"""News sentiment scoring. VADER = free, offline, instant.

Returns a 'mean' compound score in [-1, 1] (negative = bearish, positive = bullish).
A finance word-boost nudges a few market-specific terms VADER doesn't know well.
"""
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Small finance lexicon boost layered on top of VADER's general lexicon.
_FINANCE_BOOST = {
    "beats": 2.0, "beat": 1.5, "surge": 2.5, "soars": 3.0, "rally": 2.0,
    "upgrade": 2.0, "upgraded": 2.0, "outperform": 2.0, "bullish": 2.5, "record": 1.5,
    "miss": -2.0, "misses": -2.0, "plunge": -3.0, "plunges": -3.0, "slump": -2.5,
    "downgrade": -2.0, "downgraded": -2.0, "lawsuit": -2.0, "probe": -1.5,
    "bearish": -2.5, "recall": -2.0, "cut": -1.5, "warns": -2.0, "bankruptcy": -3.5,
}

_analyzer = None


def _get_analyzer() -> SentimentIntensityAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = SentimentIntensityAnalyzer()
        _analyzer.lexicon.update(_FINANCE_BOOST)
    return _analyzer


def score_headlines(headlines: list[str]) -> dict:
    """Return {'mean': float, 'n': int, 'per': [float, ...]} for a list of headlines."""
    a = _get_analyzer()
    per = [a.polarity_scores(h)["compound"] for h in headlines if h]
    mean = sum(per) / len(per) if per else 0.0
    return {"mean": mean, "n": len(per), "per": per}
