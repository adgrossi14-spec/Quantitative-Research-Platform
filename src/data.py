"""Price data loading: manual CSVs first, otherwise download + cache via yfinance."""
from datetime import datetime, timedelta
import pandas as pd

from .config import project_path

REQUIRED_COLS = ["Open", "High", "Low", "Close", "Volume"]


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize any reasonable OHLCV CSV into a Date-indexed frame."""
    df = df.copy()

    # Map common column-name variants to our canonical names.
    rename = {}
    for c in df.columns:
        cl = str(c).strip().lower()
        if cl in ("date", "datetime", "timestamp"):
            rename[c] = "Date"
        elif cl in ("adj close", "adj_close", "adjclose"):
            rename[c] = "Adj Close"
        elif cl in ("open", "high", "low", "close", "volume"):
            rename[c] = cl.capitalize()
    df = df.rename(columns=rename)

    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date"]).set_index("Date")
    df = df.sort_index()

    for c in REQUIRED_COLS:
        if c not in df.columns:
            raise ValueError(f"CSV is missing required column '{c}'. Found: {list(df.columns)}")
        df[c] = pd.to_numeric(df[c], errors="coerce")

    return df.dropna(subset=["Close"])


def _download(ticker: str, lookback_days: int) -> pd.DataFrame:
    import yfinance as yf

    start = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    df = yf.download(ticker, start=start, progress=False, auto_adjust=False)
    if df is None or df.empty:
        raise ValueError(f"No data returned for '{ticker}' (check the symbol / internet).")
    # yfinance sometimes returns MultiIndex columns; flatten to the first level.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df.reset_index()


def load_prices(ticker: str, cfg: dict) -> pd.DataFrame:
    """Return a normalized OHLCV DataFrame for one ticker."""
    ticker = ticker.upper()
    dcfg = cfg["data"]

    # 1) Manual CSV always wins (data/manual_csvs/TICKER.csv).
    manual_file = project_path(dcfg["manual_csv_dir"]) / f"{ticker}.csv"
    if manual_file.exists():
        return _normalize(pd.read_csv(manual_file))

    # 2) Use today's cache if we already downloaded it.
    cache_file = project_path(dcfg["cache_dir"]) / f"{ticker}.csv"
    if cache_file.exists():
        mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
        if mtime.date() == datetime.now().date():
            return _normalize(pd.read_csv(cache_file))

    # 3) Download fresh (or fall back to a stale cache if downloads are off).
    if not dcfg.get("auto_download", True):
        if cache_file.exists():
            return _normalize(pd.read_csv(cache_file))
        raise FileNotFoundError(
            f"No CSV for {ticker} and auto_download is off. "
            f"Drop a file at {manual_file} or enable auto_download."
        )

    df = _download(ticker, int(dcfg.get("lookback_days", 365)))
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(cache_file, index=False)
    return _normalize(df)
