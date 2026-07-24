"""Fast, technical-only screener over the broad US stock universe.

The universe comes from the official Nasdaq Trader symbol directory (all US-listed
securities). We bulk-download recent prices in chunks (much faster than one-by-one),
compute the same signals as the watchlist, and rank everything by score.

No news / sentiment / company profiles here — those are reserved for the small
watchlist, because fetching them per-ticker across thousands of names is far too slow.
Results are cached to data/_screen_results.csv and refreshed once per day.
"""
from datetime import datetime

import pandas as pd

from .config import project_path
from .signals import compute_indicators, evaluate

NASDAQ_LISTED = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
OTHER_LISTED = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"

# One request returns sector + market cap for the whole US market.
NASDAQ_SCREENER_API = (
    "https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=10000&download=true"
)
_BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

CAP_BUCKETS = [
    "Mega (>$200B)",
    "Large ($10-200B)",
    "Mid ($2-10B)",
    "Small ($300M-2B)",
    "Micro (<$300M)",
    "Unknown",
]


def _universe_cache(cfg):
    return project_path(cfg["data"]["cache_dir"]) / "_universe.txt"


def _results_cache(cfg):
    return project_path(cfg["data"]["cache_dir"]) / "_screen_results.csv"


def _scfg(cfg) -> dict:
    return cfg.get("screener", {}) or {}


def get_universe(cfg: dict, refresh: bool = False) -> list[str]:
    """List of US common-stock tickers from the Nasdaq Trader directory (cached to disk)."""
    cache = _universe_cache(cfg)
    if cache.exists() and not refresh:
        return [s.strip() for s in cache.read_text(encoding="utf-8").splitlines() if s.strip()]

    import requests

    exclude_etfs = _scfg(cfg).get("exclude_etfs", True)
    syms = set()

    # nasdaqlisted.txt cols: Symbol|Name|Market Category|Test Issue|Financial Status|Round Lot|ETF|NextShares
    try:
        for line in requests.get(NASDAQ_LISTED, timeout=30).text.splitlines()[1:]:
            p = line.split("|")
            if len(p) < 8:
                continue
            sym, test, etf = p[0], p[3], p[6]
            if test == "Y" or (exclude_etfs and etf == "Y"):
                continue
            syms.add(sym)
    except Exception:
        pass

    # otherlisted.txt cols: ACT Symbol|Name|Exchange|CQS Symbol|ETF|Round Lot|Test Issue|NASDAQ Symbol
    try:
        for line in requests.get(OTHER_LISTED, timeout=30).text.splitlines()[1:]:
            p = line.split("|")
            if len(p) < 8:
                continue
            sym, etf, test = p[0], p[4], p[6]
            if test == "Y" or (exclude_etfs and etf == "Y"):
                continue
            syms.add(sym)
    except Exception:
        pass

    clean = sorted(s for s in syms if _is_common_stock(s))
    if clean:
        cache.write_text("\n".join(clean), encoding="utf-8")
    return clean


def _is_common_stock(sym: str) -> bool:
    """Heuristic: keep ordinary common shares; drop warrants/units/rights.

    NASDAQ uses a 5th-letter suffix for non-common securities — e.g. trailing
    W (warrant), U (unit), R (right). Those clutter the screen and aren't tradable
    the way a stock is, so 5-letter symbols ending in W/U/R are excluded.
    """
    if not sym or not sym.isalpha() or len(sym) > 5:
        return False
    if len(sym) == 5 and sym[-1] in ("W", "U", "R"):
        return False
    return True


def _score_frame(df: pd.DataFrame, cfg: dict, ticker: str):
    df = df.dropna()
    if df.empty or len(df) < cfg["signals"]["sma_slow"] + 5:
        return None
    res = evaluate(compute_indicators(df, cfg), 0.0, cfg)
    return {
        "ticker": ticker,
        "action": res["action"],
        "score": res["score"],
        "price": res["price"],
        "rsi": round(res["rsi"], 1) if res["rsi"] is not None else None,
    }


def run_screen(cfg, tickers=None, progress=None, force=False, write_cache=True) -> pd.DataFrame:
    """Scan the universe (or a custom ticker list) and return a score-ranked DataFrame.

    progress: optional callback(done:int, total:int) for a UI progress bar.
    """
    custom = tickers is not None
    cache = _results_cache(cfg)

    # For the official (full-universe) screen, serve today's cache unless forced.
    if not custom and not force and cache.exists():
        if datetime.fromtimestamp(cache.stat().st_mtime).date() == datetime.now().date():
            return pd.read_csv(cache)

    import yfinance as yf

    if tickers is None:
        tickers = get_universe(cfg)
    max_t = int(_scfg(cfg).get("max_tickers", 0) or 0)
    if max_t and len(tickers) > max_t:
        tickers = tickers[:max_t]

    period = _scfg(cfg).get("history_period", "6mo")
    chunk = int(_scfg(cfg).get("chunk_size", 120))
    rows, total = [], len(tickers)

    for i in range(0, total, chunk):
        batch = tickers[i : i + chunk]
        try:
            data = yf.download(
                batch, period=period, progress=False, auto_adjust=False,
                group_by="ticker", threads=True,
            )
        except Exception:
            data = None
        if data is not None and not data.empty:
            for t in batch:
                try:
                    df = data if len(batch) == 1 else data[t]
                    row = _score_frame(df, cfg, t)
                    if row:
                        rows.append(row)
                except Exception:
                    continue
        if progress:
            progress(min(i + chunk, total), total)

    out = (
        pd.DataFrame(rows)
        .sort_values("score", ascending=False)
        .reset_index(drop=True)
        if rows
        else pd.DataFrame(columns=["ticker", "action", "score", "price", "rsi"])
    )
    if write_cache and not custom and not out.empty:
        out.to_csv(cache, index=False)
    return out


def _reference_cache(cfg):
    return project_path(cfg["data"]["cache_dir"]) / "_reference.csv"


def get_reference(cfg: dict, refresh: bool = False) -> pd.DataFrame:
    """Sector + market cap for the whole US market (NASDAQ screener API), cached ~weekly."""
    cache = _reference_cache(cfg)
    if cache.exists() and not refresh:
        age = datetime.now() - datetime.fromtimestamp(cache.stat().st_mtime)
        if age.days < 7:
            try:
                return pd.read_csv(cache)
            except Exception:
                pass

    import requests

    try:
        r = requests.get(NASDAQ_SCREENER_API, headers=_BROWSER_HEADERS, timeout=30)
        rows = r.json()["data"]["rows"]
        df = pd.DataFrame(rows)
        keep = [c for c in ("symbol", "name", "sector", "industry", "marketCap", "country") if c in df.columns]
        df = df[keep].copy()
        if "marketCap" in df.columns:
            df["marketCap"] = pd.to_numeric(df["marketCap"], errors="coerce")
        df.to_csv(cache, index=False)
        return df
    except Exception:
        if cache.exists():  # fall back to stale cache rather than nothing
            try:
                return pd.read_csv(cache)
            except Exception:
                pass
        return pd.DataFrame(columns=["symbol", "name", "sector", "industry", "marketCap", "country"])


def cap_bucket(cap) -> str:
    """Bucket a market-cap value into a size category."""
    try:
        cap = float(cap)
    except (TypeError, ValueError):
        return "Unknown"
    if pd.isna(cap) or cap <= 0:
        return "Unknown"
    if cap >= 200e9:
        return "Mega (>$200B)"
    if cap >= 10e9:
        return "Large ($10-200B)"
    if cap >= 2e9:
        return "Mid ($2-10B)"
    if cap >= 300e6:
        return "Small ($300M-2B)"
    return "Micro (<$300M)"


def enrich_results(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Add sector / marketCap / cap_bucket columns to a screen-result DataFrame."""
    out = df.copy()
    if out.empty:
        for c in ("sector", "marketCap", "cap_bucket"):
            out[c] = pd.Series(dtype="object")
        return out
    ref = get_reference(cfg)
    if ref is None or ref.empty or "symbol" not in ref.columns:
        out["sector"] = None
        out["marketCap"] = None
    else:
        ref = ref.rename(columns={"symbol": "ticker"})
        cols = [c for c in ("ticker", "sector", "marketCap") if c in ref.columns]
        out = out.merge(ref[cols], on="ticker", how="left")
    out["cap_bucket"] = out["marketCap"].apply(cap_bucket)
    return out


def screen_is_fresh(cfg) -> bool:
    """True if a full-universe screen was already run today."""
    cache = _results_cache(cfg)
    if not cache.exists():
        return False
    return datetime.fromtimestamp(cache.stat().st_mtime).date() == datetime.now().date()
