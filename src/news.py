"""Fetch recent headlines for a ticker. Free RSS by default; Finnhub when configured."""
import urllib.parse
from datetime import datetime, timedelta

import feedparser


def fetch_news(ticker: str, cfg: dict) -> list[dict]:
    ticker = ticker.upper()
    ncfg = cfg.get("news", {})
    maxn = int(ncfg.get("max_articles", 15))
    if ncfg.get("provider") == "finnhub" and ncfg.get("finnhub_api_key"):
        try:
            return _fetch_finnhub(ticker, ncfg["finnhub_api_key"], maxn)
        except Exception:
            pass  # fall back to free RSS if Finnhub fails
    return _fetch_rss(ticker, maxn)


def _fetch_rss(ticker: str, maxn: int) -> list[dict]:
    feeds = [
        f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US",
        "https://news.google.com/rss/search?q="
        + urllib.parse.quote(f"{ticker} stock")
        + "&hl=en-US&gl=US&ceid=US:en",
    ]
    items, seen = [], set()
    for url in feeds:
        try:
            parsed = feedparser.parse(url)
        except Exception:
            continue
        for e in parsed.entries:
            title = (e.get("title") or "").strip()
            key = title.lower()
            if title and key not in seen:
                seen.add(key)
                items.append(
                    {"title": title, "link": e.get("link", ""), "published": e.get("published", "")}
                )
    return items[:maxn]


def _fetch_finnhub(ticker: str, api_key: str, maxn: int) -> list[dict]:
    import requests

    today = datetime.now().date()
    frm = today - timedelta(days=14)
    url = (
        f"https://finnhub.io/api/v1/company-news?symbol={ticker}"
        f"&from={frm}&to={today}&token={api_key}"
    )
    data = requests.get(url, timeout=10).json()
    return [
        {
            "title": a.get("headline", ""),
            "link": a.get("url", ""),
            "published": str(a.get("datetime", "")),
        }
        for a in data[:maxn]
        if a.get("headline")
    ]
