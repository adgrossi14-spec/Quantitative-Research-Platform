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


Tech Stack:
 Language & Environment

  ┌────────────────────────────┬───────────────────────────────────────────────────┐
  │         Technology         │                       Role                        │
  ├────────────────────────────┼───────────────────────────────────────────────────┤
  │ Python 3.12                │ The language the entire application is written in │
  ├────────────────────────────┼───────────────────────────────────────────────────┤
  │ venv (virtual environment) │ Isolated, self-contained dependency environment   │
  ├────────────────────────────┼───────────────────────────────────────────────────┤
  │ pip                        │ Package installer (pulls the libraries below)     │
  └────────────────────────────┴───────────────────────────────────────────────────┘

  Web Interface / Frontend

  ┌────────────┬─────────────────────────────────────────────────────────────────────────────────────────────────────┐
  │ Technology │                                                Role                                                 │
  ├────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Streamlit  │ Turns Python into the interactive browser dashboard — all six tabs, buttons, charts, tables. No     │
  │            │ HTML/CSS/JavaScript written by hand. Also runs the local web server.                                │
  └────────────┴─────────────────────────────────────────────────────────────────────────────────────────────────────┘

  Data Processing & Math

  ┌────────────┬────────────────────────────────────────────────────────────────────────────────────────────────┐
  │ Technology │                                              Role                                              │
  ├────────────┼────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ pandas     │ Core data engine — loads price history, computes indicators, powers the screener tables        │
  ├────────────┼────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ NumPy      │ Numerical library underneath pandas; used in the indicator math (e.g. Relative Strength Index) │
  └────────────┴────────────────────────────────────────────────────────────────────────────────────────────────┘

  Data Sources & Fetching (all free)

  ┌────────────┬─────────────────────────────────────────────────────────────────────────────────────────────────────┐
  │ Technology │                                                Role                                                 │
  ├────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ yfinance   │ Downloads daily stock & index prices from Yahoo Finance (no key needed)                             │
  ├────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ feedparser │ Reads free news headline feeds (RSS) from Yahoo Finance & Google News                               │
  ├────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ requests   │ Direct web calls for the screener's stock universe (Nasdaq Trader directory) and sector/market-cap  │
  │            │ data (NASDAQ screener API)                                                                          │
  └────────────┴─────────────────────────────────────────────────────────────────────────────────────────────────────┘

  Analysis / "Intelligence"

  ┌────────────────────┬────────────────────────────────────────────────────────────────────────────────────────────┐
  │     Technology     │                                            Role                                            │
  ├────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────┤
  │ vaderSentiment     │ Free, offline tool that scores news headlines as positive/negative — no paid AI, no        │
  │ (VADER)            │ per-use cost                                                                               │
  ├────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Custom scoring     │ Hand-written Python (src/signals.py) blending trend, momentum, relative strength &         │
  │ model              │ sentiment — a transparent formula, not machine learning                                    │
  └────────────────────┴────────────────────────────────────────────────────────────────────────────────────────────┘

  Configuration

  ┌─────────────┬───────────────────────────────────────────────────────────────────────────┐
  │ Technology  │                                   Role                                    │
  ├─────────────┼───────────────────────────────────────────────────────────────────────────┤
  │ PyYAML      │ Reads your config.yaml settings                                           │
  ├─────────────┼───────────────────────────────────────────────────────────────────────────┤
  │ ruamel.yaml │ Writes settings back from the Settings tab while preserving your comments │
  └─────────────┴───────────────────────────────────────────────────────────────────────────┘

  Storage (deliberately no database)

  ┌────────────┬─────────────────────────────────────────────────────────────┐
  │ Technology │                            Role                             │
  ├────────────┼─────────────────────────────────────────────────────────────┤
  │ JSON files │ Your paper-trading account state (state/paper_account.json) │
  ├────────────┼─────────────────────────────────────────────────────────────┤
  │ CSV files  │ Cached prices, screener results, ticker universe (in data/) │
  └────────────┴─────────────────────────────────────────────────────────────┘

  Tooling & Distribution

  ┌────────────────────────┬───────────────────────────────────────────────────────────────────────────┐
  │       Technology       │                                   Role                                    │
  ├────────────────────────┼───────────────────────────────────────────────────────────────────────────┤
  │ Git & GitHub           │ Version control; hosted at adgrossi14-spec/Quantitative-Research-Platform │
  ├────────────────────────┼───────────────────────────────────────────────────────────────────────────┤
  │ Git LFS                │ Available for large files (installed on your machine)                     │
  ├────────────────────────┼───────────────────────────────────────────────────────────────────────────┤
  │ Batch script (run.bat) │ One-click launcher for Windows                                            │
  ├────────────────────────┼───────────────────────────────────────────────────────────────────────────┤
  │ Claude Code            │ AI pair-programmer used to build it                                       │
  └────────────────────────┴───────────────────────────────────────────────────────────────────────────┘
