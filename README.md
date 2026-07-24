# 📈 Stock Forecaster (Paper Mode)

A personal decision-support tool that scans price data and news, scores each stock
with a transparent technical + sentiment model, and suggests trades — all on
**fake money** so you can tune the model risk-free.

> ⚠️ Not financial advice. No tool can reliably predict prices. This is for
> learning and disciplined decision-making, not guaranteed profit.
>
> Demo Video:https://youtu.be/hsJSnpSSyjA

## What it does
- **Downloads** daily price history per ticker (Yahoo Finance via `yfinance`) and caches it.
- **Reads news** headlines (free RSS now; Finnhub later) and scores sentiment offline (VADER).
- **Scores** each stock −100…+100 from trend (SMA), momentum (MACD + 10-day return),
  RSI, and news sentiment → **BUY / HOLD / SELL** with plain-English reasons.
- **Paper trades**: a $100k simulated account tracks cash, positions, and P&L.
- **Backtests** the strategy against buy-and-hold so you can see if the rules hold up.

## First-time setup (one time)
Open PowerShell in this folder, create a virtual environment, and install the libraries:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Run it
Double-click **`run.bat`**, or:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Your browser opens to the dashboard with four tabs:
1. **Suggestions** – scan your watchlist, see scores/reasons, execute paper trades.
2. **Paper Portfolio** – equity, cash, P&L, open positions, trade log, reset button.
3. **Backtest** – test the strategy on one ticker vs. buy-and-hold.
4. **Settings** – view current config.

## Tuning the model
Everything lives in **`config.yaml`**:
- `watchlist` – tickers to scan.
- `signals.weights` – how much trend/momentum/RSI/sentiment each count (sum to 1.0).
- `signals.buy_threshold` / `sell_threshold` – how decisive a signal must be.
- `news.provider` – `rss` (free) → switch to `finnhub` and add your key later.
- `sentiment.provider` – `vader` (free). `claude` is a future upgrade (needs an API key + cost).

## Bring your own CSVs
Drop a file named `TICKER.csv` (e.g. `TSLA.csv`) into `data/manual_csvs/`.
Needs columns: Date, Open, High, Low, Close, Volume. Manual files override downloads.

## Roadmap
- [ ] Finnhub news integration (toggle ready in config)
- [ ] Optional Claude-powered sentiment
- [ ] Live trading mode (intentionally disabled for now)
