"""Technical indicators and the scoring model that turns them into a trade suggestion.

The final score is in [-100, 100]:
  >= buy_threshold  -> BUY
  <= sell_threshold -> SELL
  otherwise         -> HOLD
"""
import numpy as np
import pandas as pd


def _clip(x, lo=-100.0, hi=100.0):
    return max(lo, min(hi, float(x)))


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def macd(close: pd.Series, fast=12, slow=26, signal=9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    line = ema_fast - ema_slow
    sig = line.ewm(span=signal, adjust=False).mean()
    return line, sig


def compute_indicators(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    s = cfg["signals"]
    out = df.copy()
    out["SMA_fast"] = out["Close"].rolling(s["sma_fast"]).mean()
    out["SMA_slow"] = out["Close"].rolling(s["sma_slow"]).mean()
    out["RSI"] = rsi(out["Close"], s["rsi_period"])
    out["MACD"], out["MACD_signal"] = macd(out["Close"])
    out["MOM"] = out["Close"].pct_change(10)  # 10-day momentum
    return out


def evaluate(df_ind: pd.DataFrame, sentiment_mean: float, cfg: dict) -> dict:
    """Score the most recent bar. df_ind must come from compute_indicators()."""
    s = cfg["signals"]
    w = s["weights"]
    last = df_ind.iloc[-1]
    reasons = []
    sub = {}

    # --- Trend: fast SMA vs slow SMA ---
    if pd.notna(last["SMA_fast"]) and pd.notna(last["SMA_slow"]) and last["SMA_slow"]:
        trend_pct = (last["SMA_fast"] - last["SMA_slow"]) / last["SMA_slow"]
        sub["trend"] = _clip(trend_pct * 1000)
        direction = "above" if last["SMA_fast"] >= last["SMA_slow"] else "below"
        reasons.append(f"SMA{s['sma_fast']} is {direction} SMA{s['sma_slow']} ({trend_pct * 100:+.1f}%)")
    else:
        sub["trend"] = 0.0
        reasons.append("Not enough history to judge trend")

    # --- Momentum: 10-day return + MACD confirmation ---
    mom = 0.0 if pd.isna(last.get("MOM")) else float(last["MOM"])
    mscore = _clip(mom * 1000)
    if pd.notna(last["MACD"]) and pd.notna(last["MACD_signal"]):
        if last["MACD"] >= last["MACD_signal"]:
            mscore = _clip(mscore + 15)
            reasons.append("MACD above its signal line (bullish)")
        else:
            mscore = _clip(mscore - 15)
            reasons.append("MACD below its signal line (bearish)")
    sub["momentum"] = mscore
    reasons.append(f"10-day return {mom * 100:+.1f}%")

    # --- RSI: low = oversold (bullish), high = overbought (bearish) ---
    rsi_val = last["RSI"]
    if pd.notna(rsi_val):
        sub["rsi"] = _clip((50 - rsi_val) * 2)
        if rsi_val < 30:
            reasons.append(f"RSI {rsi_val:.0f} — oversold (possible bounce)")
        elif rsi_val > 70:
            reasons.append(f"RSI {rsi_val:.0f} — overbought (caution)")
        else:
            reasons.append(f"RSI {rsi_val:.0f} — neutral")
    else:
        sub["rsi"] = 0.0

    # --- News sentiment ---
    sub["sentiment"] = _clip(sentiment_mean * 100)
    reasons.append(f"News sentiment {sentiment_mean:+.2f}")

    score = _clip(
        w["trend"] * sub["trend"]
        + w["momentum"] * sub["momentum"]
        + w["rsi"] * sub["rsi"]
        + w["sentiment"] * sub["sentiment"]
    )

    if score >= s["buy_threshold"]:
        action = "BUY"
    elif score <= s["sell_threshold"]:
        action = "SELL"
    else:
        action = "HOLD"

    return {
        "score": round(score, 1),
        "action": action,
        "sub_scores": {k: round(v, 1) for k, v in sub.items()},
        "reasons": reasons,
        "price": float(last["Close"]),
        "rsi": None if pd.isna(rsi_val) else float(rsi_val),
    }
