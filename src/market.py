"""Broad-market overview: pull the major index ETFs' daily CSVs and summarize them.

Reuses the same daily-cached downloader as everything else, so the data refreshes
automatically once per day on first load.
"""
import pandas as pd

from .data import load_prices

DEFAULT_INDICES = ["SPY", "QQQ", "DIA", "IWM"]


def _change(close: pd.Series, n: int):
    """Percent change over the last n trading days (None if not enough history)."""
    if len(close) > n:
        return round((close.iloc[-1] / close.iloc[-1 - n] - 1) * 100, 2)
    return None


def _indices(cfg: dict) -> list[str]:
    return cfg.get("market", {}).get("indices", DEFAULT_INDICES)


def index_performance(ticker: str, cfg: dict) -> dict:
    c = load_prices(ticker, cfg)["Close"]
    return {
        "ticker": ticker,
        "price": round(float(c.iloc[-1]), 2),
        "day_%": _change(c, 1),
        "week_%": _change(c, 5),
        "month_%": _change(c, 21),
        "3mo_%": _change(c, 63),
    }


def market_overview(cfg: dict) -> list[dict]:
    """One row per index ETF. Rows that fail to load carry an 'error' key instead."""
    rows = []
    for t in _indices(cfg):
        try:
            rows.append(index_performance(t, cfg))
        except Exception as e:
            rows.append({"ticker": t, "error": str(e)})
    return rows


def normalized_frame(cfg: dict, days: int = 90) -> pd.DataFrame:
    """Each index rebased to 100 over the last `days` so they're directly comparable."""
    cols = {}
    for t in _indices(cfg):
        try:
            c = load_prices(t, cfg)["Close"].tail(days)
            if len(c):
                cols[t] = c / c.iloc[0] * 100
        except Exception:
            pass
    return pd.DataFrame(cols)
