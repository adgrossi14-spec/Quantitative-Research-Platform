"""Paper-trading account: fake money, real bookkeeping. Persists to a JSON file.

This is the ONLY place trades happen, and they are always simulated.
There is no broker connection — live trading is intentionally not implemented.
"""
import json
from datetime import datetime

from .config import project_path


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class PaperAccount:
    def __init__(self, cfg: dict):
        pcfg = cfg["paper"]
        self.path = project_path(pcfg["state_file"])
        self.starting_cash = float(pcfg["starting_cash"])
        self.max_position_pct = float(pcfg.get("max_position_pct", 0.15))
        self._load()

    def _load(self):
        if self.path.exists():
            with open(self.path, "r", encoding="utf-8") as f:
                st = json.load(f)
        else:
            st = {"cash": self.starting_cash, "positions": {}, "trades": []}
        self.cash = float(st["cash"])
        self.positions = st["positions"]   # {ticker: {"shares": int, "avg_price": float}}
        self.trades = st["trades"]

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(
                {"cash": self.cash, "positions": self.positions, "trades": self.trades},
                f,
                indent=2,
            )

    # ---- trading ----
    def buy(self, ticker: str, price: float, shares=None, note="") -> dict:
        ticker = ticker.upper()
        if shares is None:  # size by max_position_pct of current equity
            budget = self.equity({ticker: price}) * self.max_position_pct
            shares = int(budget // price)
        shares = int(shares)
        if shares <= 0:
            return {"ok": False, "msg": "Position size rounds to 0 shares."}
        cost = shares * price
        if cost > self.cash:
            return {"ok": False, "msg": f"Need ${cost:,.0f} but only ${self.cash:,.0f} cash."}

        pos = self.positions.get(ticker, {"shares": 0, "avg_price": 0.0})
        if pos["shares"] == 0:  # opening a fresh position — stamp the entry date
            pos["opened"] = _now()
        new_shares = pos["shares"] + shares
        pos["avg_price"] = (pos["avg_price"] * pos["shares"] + cost) / new_shares
        pos["shares"] = new_shares
        self.positions[ticker] = pos
        self.cash -= cost
        self.trades.append(
            {"time": _now(), "side": "BUY", "ticker": ticker, "shares": shares,
             "price": round(price, 2), "note": note}
        )
        self.save()
        return {"ok": True, "msg": f"Bought {shares} {ticker} @ ${price:,.2f}"}

    def sell(self, ticker: str, price: float, shares=None, note="") -> dict:
        ticker = ticker.upper()
        pos = self.positions.get(ticker)
        if not pos or pos["shares"] <= 0:
            return {"ok": False, "msg": f"No open position in {ticker}."}
        if shares is None or int(shares) > pos["shares"]:
            shares = pos["shares"]
        shares = int(shares)
        proceeds = shares * price
        realized = (price - pos["avg_price"]) * shares
        pos["shares"] -= shares
        if pos["shares"] == 0:
            del self.positions[ticker]
        else:
            self.positions[ticker] = pos
        self.cash += proceeds
        self.trades.append(
            {"time": _now(), "side": "SELL", "ticker": ticker, "shares": shares,
             "price": round(price, 2), "realized": round(realized, 2), "note": note}
        )
        self.save()
        return {"ok": True, "msg": f"Sold {shares} {ticker} @ ${price:,.2f}  (P&L ${realized:+,.2f})"}

    # ---- valuation ----
    def equity(self, prices: dict) -> float:
        val = self.cash
        for t, pos in self.positions.items():
            px = prices.get(t, pos["avg_price"])
            val += pos["shares"] * px
        return val

    def positions_table(self, prices: dict) -> list[dict]:
        rows = []
        for t, pos in self.positions.items():
            px = prices.get(t, pos["avg_price"])
            mv = pos["shares"] * px
            cost = pos["shares"] * pos["avg_price"]
            rows.append(
                {
                    "ticker": t,
                    "shares": pos["shares"],
                    "days_held": self._days_held(pos),
                    "avg_price": round(pos["avg_price"], 2),
                    "price": round(px, 2),
                    "market_value": round(mv, 2),
                    "unrealized": round(mv - cost, 2),
                    "unrealized_%": round((px / pos["avg_price"] - 1) * 100, 2) if pos["avg_price"] else 0.0,
                }
            )
        return rows

    @staticmethod
    def _days_held(pos: dict):
        """Calendar days since the position was opened (None if unknown, e.g. legacy state)."""
        opened = pos.get("opened")
        if not opened:
            return None
        try:
            return (datetime.now() - datetime.strptime(opened, "%Y-%m-%d %H:%M:%S")).days
        except (ValueError, TypeError):
            return None

    def reset(self):
        self.cash = self.starting_cash
        self.positions = {}
        self.trades = []
        self.save()
