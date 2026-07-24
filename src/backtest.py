"""Walk the strategy through history to sanity-check it vs. buy-and-hold.

NOTE: backtest uses TECHNICAL signals only (sentiment = 0), because historical
headlines aren't available offline. It's a reality check, not a profit promise.
"""
import pandas as pd

from .signals import compute_indicators, evaluate


def backtest(df: pd.DataFrame, cfg: dict, start_cash: float = 10000.0) -> dict:
    ind = compute_indicators(df, cfg).dropna(subset=["SMA_slow"])
    if ind.empty:
        raise ValueError("Not enough history to backtest (need more than sma_slow days).")

    cash, shares = start_cash, 0.0
    curve = []
    for i in range(len(ind)):
        window = ind.iloc[: i + 1]
        price = float(window["Close"].iloc[-1])
        res = evaluate(window, 0.0, cfg)  # no news in backtest
        if res["action"] == "BUY" and cash > 0:
            shares, cash = cash / price, 0.0
        elif res["action"] == "SELL" and shares > 0:
            cash, shares = shares * price, 0.0
        curve.append({"Date": window.index[-1], "equity": cash + shares * price})

    eq = pd.DataFrame(curve).set_index("Date")
    strat = (eq["equity"].iloc[-1] / start_cash - 1) * 100
    bh = (ind["Close"].iloc[-1] / ind["Close"].iloc[0] - 1) * 100
    return {
        "equity_curve": eq,
        "strategy_return_pct": round(strat, 2),
        "buy_hold_return_pct": round(bh, 2),
    }
