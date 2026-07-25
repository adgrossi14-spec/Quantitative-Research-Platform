# 📈 Stock Forecaster (Paper Mode)

A personal decision-support tool that scans price data and news, scores each stock
with a transparent technical + sentiment model, and suggests trades — all on
**fake money** so you can tune the model risk-free.

> ⚠️ Not financial advice. No tool can reliably predict prices. This is for
> learning and disciplined decision-making, not guaranteed profit.

## 🎥 Demo

[![Watch the demo](https://img.youtube.com/vi/hsJSnpSSyjA/maxresdefault.jpg)](https://youtu.be/hsJSnpSSyjA)

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

Your browser opens to the dashboard with six tabs:
1. **Market** – broad-market backdrop from the major index ETFs.
2. **Suggestions** – scan your watchlist, see scores/reasons, execute paper trades.
3. **Screener** – fast technical scan across the broad US stock universe.
4. **Paper Portfolio** – equity, cash, P&L, positions, trade log, manual buy/sell.
5. **Backtest** – test the strategy on one ticker vs. buy-and-hold.
6. **Settings** – adjust the watchlist, weights, and thresholds live.

## Tuning the model
Everything lives in **`config.yaml`** (or the editable Settings tab):
- `watchlist` – tickers to scan.
- `signals.weights` – how much trend/momentum/RSI/sentiment each count (sum to 1.0).
- `signals.buy_threshold` / `sell_threshold` – how decisive a signal must be.
- `news.provider` – `rss` (free) → switch to `finnhub` and add your key later.
- `sentiment.provider` – `vader` (free). `claude` is a future upgrade (needs an API key + cost).

## Bring your own CSVs
Drop a file named `TICKER.csv` (e.g. `TSLA.csv`) into `data/manual_csvs/`.
Needs columns: Date, Open, High, Low, Close, Volume. Manual files override downloads.

## 🛠️ Tech Stack

**Language & Environment**

| Technology | Role |
| --- | --- |
| **Python 3.12** | The language the entire application is written in |
| **venv** | Isolated, self-contained dependency environment |
| **pip** | Package installer for the libraries below |

**Web Interface**

| Technology | Role |
| --- | --- |
| **Streamlit** | Turns Python into the interactive browser dashboard — all six tabs, buttons, charts, and tables. Runs the local web server. No hand-written HTML/CSS/JavaScript. |

**Data Processing & Math**

| Technology | Role |
| --- | --- |
| **pandas** | Core data engine — loads price history, computes indicators, powers the screener tables |
| **NumPy** | Numerical library underneath pandas; used in the indicator math (e.g. Relative Strength Index) |

**Data Sources & Fetching** (all free)

| Technology | Role |
| --- | --- |
| **yfinance** | Downloads daily stock & index prices from Yahoo Finance (no key needed) |
| **feedparser** | Reads free news headline feeds (RSS) from Yahoo Finance & Google News |
| **requests** | Fetches the screener's stock universe (Nasdaq Trader directory) and sector/market-cap data |

**Analysis / "Intelligence"**

| Technology | Role |
| --- | --- |
| **vaderSentiment (VADER)** | Free, offline tool that scores news headlines as positive/negative — no paid AI, no per-use cost |
| **Custom scoring model** | Hand-written Python (`src/signals.py`) blending trend, momentum, relative strength & sentiment — a transparent formula, not machine learning |

**Configuration**

| Technology | Role |
| --- | --- |
| **PyYAML** | Reads the `config.yaml` settings |
| **ruamel.yaml** | Writes settings back from the Settings tab while preserving comments |

**Storage** (deliberately no database)

| Technology | Role |
| --- | --- |
| **JSON files** | Paper-trading account state (`state/paper_account.json`) |
| **CSV files** | Cached prices, screener results, and ticker universe (in `data/`) |

**Tooling & Distribution**

| Technology | Role |
| --- | --- |
| **Git & GitHub** | Version control and hosting |
| **run.bat** | One-click launcher for Windows |
| **Claude Code** | AI pair-programmer used to build it |

## Roadmap
- [ ] Finnhub news integration (toggle ready in config)
- [ ] Optional Claude-powered sentiment
- [ ] Live trading mode (intentionally disabled for now)
