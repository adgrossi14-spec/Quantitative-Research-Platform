"""Company profile lookup (name, sector, industry, business summary).

Pulled from yfinance and cached to disk, since descriptions rarely change and
the .info call is slow/flaky. Cache lives at data/_profiles.json.
"""
import json

from .config import project_path


def _cache_path(cfg: dict):
    return project_path(cfg["data"]["cache_dir"]) / "_profiles.json"


def _load_cache(cfg: dict) -> dict:
    p = _cache_path(cfg)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_cache(cfg: dict, cache: dict):
    p = _cache_path(cfg)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cache, indent=2), encoding="utf-8")


def _fetch(ticker: str) -> dict:
    import yfinance as yf

    try:
        info = yf.Ticker(ticker).info or {}
    except Exception:
        info = {}
    return {
        "name": info.get("longName") or info.get("shortName") or ticker,
        "sector": info.get("sector") or "",
        "industry": info.get("industry") or "",
        "summary": info.get("longBusinessSummary") or "",
        "website": info.get("website") or "",
        "market_cap": info.get("marketCap"),
    }


def get_profile(ticker: str, cfg: dict, refresh: bool = False) -> dict:
    """Return a cached company profile dict, fetching once if not seen before."""
    ticker = ticker.upper()
    cache = _load_cache(cfg)
    if not refresh and ticker in cache:
        return cache[ticker]
    prof = _fetch(ticker)
    cache[ticker] = prof
    _save_cache(cfg, cache)
    return prof


def market_cap_str(cap) -> str:
    """Human-friendly market cap, e.g. 2.9T / 340.1B / 12.0M."""
    if not cap:
        return ""
    for unit, size in (("T", 1e12), ("B", 1e9), ("M", 1e6)):
        if cap >= size:
            return f"${cap / size:.1f}{unit}"
    return f"${cap:,.0f}"
