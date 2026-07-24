"""Stock Forecaster — Streamlit dashboard (PAPER MODE).

Run with:  .venv\\Scripts\\python.exe -m streamlit run app.py
or just double-click run.bat
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import streamlit as st

from src.config import load_config
from src.data import load_prices
from src.news import fetch_news
from src.sentiment import score_headlines
from src.signals import compute_indicators, evaluate
from src.paper import PaperAccount
from src.backtest import backtest
from src.market import market_overview, normalized_frame
from src.company import get_profile, market_cap_str
from src.screener import (
    get_universe,
    run_screen,
    screen_is_fresh,
    enrich_results,
    cap_bucket,
    CAP_BUCKETS,
)

st.set_page_config(page_title="Stock Forecaster — Paper Mode", layout="wide")

cfg = load_config()
acct = PaperAccount(cfg)

st.title("📈 Stock Forecaster — Paper Mode")
st.caption(
    "Decision-support tool, **not** financial advice. Signals are probabilistic. "
    "Paper money only — no real trades are placed."
)

ACTION_ICON = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}


@st.cache_data(ttl=900, show_spinner=False)
def analyze(ticker: str) -> dict:
    """Download/load prices, fetch news, score it. Cached 15 min per ticker."""
    df = load_prices(ticker, cfg)
    ind = compute_indicators(df, cfg)
    news = fetch_news(ticker, cfg)
    sent = score_headlines([n["title"] for n in news])
    res = evaluate(ind, sent["mean"], cfg)
    profile = get_profile(ticker, cfg)
    return {"ind": ind, "news": news, "sent": sent, "res": res, "profile": profile}


def latest_price(ticker: str) -> float | None:
    try:
        return float(load_prices(ticker, cfg)["Close"].iloc[-1])
    except Exception:
        return None


@st.cache_data(ttl=900, show_spinner=False)
def get_market() -> tuple:
    """Market overview + normalized comparison frame. Cached 15 min."""
    return market_overview(cfg), normalized_frame(cfg)


# --- Always-visible market snapshot banner (today's move per index) ---
try:
    _mkt, _ = get_market()
    cols = st.columns(len(_mkt))
    for col, m in zip(cols, _mkt):
        if "error" in m:
            col.metric(m["ticker"], "n/a")
        else:
            day = m["day_%"]
            col.metric(
                m["ticker"],
                f"${m['price']:,.2f}",
                f"{day:+.2f}% today" if day is not None else "—",
            )
except Exception:
    pass

tab_mkt, tab_scan, tab_screen, tab_port, tab_bt, tab_set = st.tabs(
    ["🌎 Market", "🔎 Suggestions", "🔭 Screener", "💼 Paper Portfolio", "🧪 Backtest", "⚙️ Settings"]
)

# ----------------------------------------------------------------- Market
with tab_mkt:
    st.subheader("Market overview")
    if st.button("🔄 Refresh market data"):
        st.cache_data.clear()
        st.rerun()
    mkt, norm = get_market()
    good = [m for m in mkt if "error" not in m]
    if good:
        st.dataframe(pd.DataFrame(good), use_container_width=True, hide_index=True)
    for m in mkt:
        if "error" in m:
            st.warning(f"{m['ticker']}: {m['error']}")
    st.markdown("**Relative performance — last ~90 days, each index starts at 100:**")
    if not norm.empty:
        st.line_chart(norm)
    st.caption(
        "Daily CSVs auto-download once per day on first load (cached). "
        "Use Refresh to force a re-pull. When indices are broadly red, treat BUY signals with extra caution."
    )

# ----------------------------------------------------------------- Suggestions
with tab_scan:
    watch = st.text_input(
        "Watchlist (comma-separated tickers)", ", ".join(cfg["watchlist"])
    ).upper()
    tickers = [t.strip() for t in watch.split(",") if t.strip()]

    if st.button("🔄 Re-scan (clear cache)"):
        st.cache_data.clear()

    prices_now = {t: latest_price(t) for t in tickers}
    prices_now = {t: p for t, p in prices_now.items() if p is not None}

    for t in tickers:
        try:
            a = analyze(t)
        except Exception as e:
            st.error(f"{t}: {e}")
            continue

        res = a["res"]
        icon = ACTION_ICON[res["action"]]
        header = f"{icon} {t} — {res['action']}   ·   score {res['score']}   ·   ${res['price']:,.2f}"
        with st.expander(header, expanded=True):
            prof = a["profile"]
            meta = " · ".join(
                x for x in (prof.get("sector"), prof.get("industry"), market_cap_str(prof.get("market_cap"))) if x
            )
            st.markdown(f"### {prof.get('name', t)}")
            if meta:
                st.caption(meta)
            summary = prof.get("summary") or ""
            if summary:
                # No nested expander allowed inside a card; show a trimmed summary.
                trimmed = summary if len(summary) <= 600 else summary[:600].rsplit(" ", 1)[0] + " …"
                st.write(trimmed)
                if prof.get("website"):
                    st.caption(f"🔗 {prof['website']}")
            st.divider()

            c1, c2 = st.columns([2, 1])
            with c1:
                st.markdown("**Why:**")
                for r in res["reasons"]:
                    st.markdown(f"- {r}")

                if res["action"] == "BUY":
                    budget = acct.equity(prices_now) * acct.max_position_pct
                    sh = int(budget // res["price"])
                    st.info(
                        f"Suggested: **BUY ~{sh} shares** "
                        f"(≈${sh * res['price']:,.0f}, {acct.max_position_pct * 100:.0f}% of equity)"
                    )
                    if st.button(f"Execute paper BUY {t}", key=f"buy_{t}"):
                        out = acct.buy(t, res["price"], sh, note=f"score {res['score']}")
                        (st.success if out["ok"] else st.warning)(out["msg"])
                elif res["action"] == "SELL" and t in acct.positions:
                    st.info("Suggested: **SELL** your position")
                    if st.button(f"Execute paper SELL {t}", key=f"sell_{t}"):
                        out = acct.sell(t, res["price"], note=f"score {res['score']}")
                        (st.success if out["ok"] else st.warning)(out["msg"])
            with c2:
                st.metric("Score (-100..100)", res["score"])
                st.bar_chart(pd.Series(res["sub_scores"], name="sub-scores"))

            st.markdown("**Price & moving averages (last 180 days):**")
            st.line_chart(a["ind"].tail(180)[["Close", "SMA_fast", "SMA_slow"]])

            st.markdown(f"**Recent headlines** (sentiment {a['sent']['mean']:+.2f}, n={a['sent']['n']}):")
            for n in a["news"][:8]:
                st.markdown(f"- [{n['title']}]({n['link']})")

# ----------------------------------------------------------------- Screener
with tab_screen:
    st.subheader("🔭 Market screener — broad US universe (technical-only)")
    st.caption(
        "Fast scan with no news/profiles. Found something interesting? Paste its ticker "
        "into the Suggestions watchlist box above for the full news + company analysis."
    )

    uni = get_universe(cfg)
    cap = int((cfg.get("screener", {}) or {}).get("max_tickers", 0) or 0)
    scanned_n = min(cap, len(uni)) if cap else len(uni)
    st.write(f"Universe: **{len(uni):,}** US common stocks · this run scans **{scanned_n:,}** (cached daily).")

    run = st.button("▶️ Run / refresh full screen", type="primary")

    if run or screen_is_fresh(cfg):
        if run:
            bar = st.progress(0.0, text="Scanning the market…")
            df = run_screen(
                cfg, force=True,
                progress=lambda d, t: bar.progress(d / t, text=f"Scanning {d:,}/{t:,} tickers…"),
            )
            bar.empty()
        else:
            df = run_screen(cfg)  # today's cached results — instant

        if df.empty:
            st.warning("No results — the data source may be rate-limiting. Try again shortly.")
        else:
            df = enrich_results(df, cfg)  # add sector / market cap / size bucket

            st.markdown("**Filters** — narrow the universe (e.g. only large-cap tech):")
            f1, f2, f3 = st.columns(3)
            sectors = sorted(s for s in df["sector"].dropna().unique() if s)
            sel_sec = f1.multiselect("Sector", sectors)
            present_buckets = [b for b in CAP_BUCKETS if b in set(df["cap_bucket"])]
            sel_cap = f2.multiselect("Market cap", present_buckets)
            sel_act = f3.multiselect("Action", ["BUY", "HOLD", "SELL"])

            fdf = df
            if sel_sec:
                fdf = fdf[fdf["sector"].isin(sel_sec)]
            if sel_cap:
                fdf = fdf[fdf["cap_bucket"].isin(sel_cap)]
            if sel_act:
                fdf = fdf[fdf["action"].isin(sel_act)]

            # Friendly market-cap column for display.
            disp = fdf.copy()
            disp["mkt_cap"] = disp["marketCap"].apply(market_cap_str)
            cols = ["ticker", "sector", "mkt_cap", "action", "score", "price", "rsi"]

            st.success(f"Showing {len(fdf):,} of {len(df):,} scored stocks.")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**🟢 Top BUY candidates**")
                buys = disp[disp["action"] == "BUY"].sort_values("score", ascending=False).head(20)
                st.dataframe(buys[cols], use_container_width=True, hide_index=True)
            with c2:
                st.markdown("**🔴 Top SELL candidates**")
                sells = disp[disp["action"] == "SELL"].sort_values("score").head(20)
                st.dataframe(sells[cols], use_container_width=True, hide_index=True)

            st.markdown("**All matching results** (click a column header to sort):")
            st.dataframe(disp[cols], use_container_width=True, hide_index=True, height=480)
    else:
        st.info(
            "Click **▶️ Run** to scan the universe. The first run of the day takes a few "
            "minutes (downloading thousands of tickers); after that it's cached and instant."
        )

# ----------------------------------------------------------------- Portfolio
with tab_port:
    prices = {t: latest_price(t) for t in acct.positions}
    prices = {t: p for t, p in prices.items() if p is not None}
    eq = acct.equity(prices)

    c1, c2, c3 = st.columns(3)
    c1.metric("Equity", f"${eq:,.2f}")
    c2.metric("Cash", f"${acct.cash:,.2f}")
    c3.metric(
        "Total P&L",
        f"${eq - acct.starting_cash:,.2f}",
        f"{(eq / acct.starting_cash - 1) * 100:+.2f}%",
    )

    st.subheader("Open positions")
    rows = acct.positions_table(prices)
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No open positions yet — execute a suggestion on the first tab.")

    st.subheader("Trade log")
    if acct.trades:
        st.dataframe(pd.DataFrame(acct.trades[::-1]), use_container_width=True, hide_index=True)
    else:
        st.write("No trades yet.")

    st.divider()
    if st.button("⚠️ Reset paper account to starting cash"):
        acct.reset()
        st.success("Paper account reset.")
        st.rerun()

# ----------------------------------------------------------------- Backtest
with tab_bt:
    pool = tickers if tickers else cfg["watchlist"]
    bt_ticker = st.selectbox("Ticker to backtest", pool)
    if st.button("Run backtest"):
        try:
            df = load_prices(bt_ticker, cfg)
            bt = backtest(df, cfg)
            c1, c2 = st.columns(2)
            c1.metric("Strategy return", f"{bt['strategy_return_pct']}%")
            c2.metric("Buy & hold", f"{bt['buy_hold_return_pct']}%")
            st.line_chart(bt["equity_curve"][["equity"]])
            st.caption(
                "Technical signals only (no historical news). "
                "Past performance does not predict future results."
            )
        except Exception as e:
            st.error(str(e))

# ----------------------------------------------------------------- Settings
with tab_set:
    st.markdown(f"**Mode:** `{cfg.get('mode', 'paper')}`")
    if cfg.get("mode") == "live":
        st.error("Live mode is not implemented. Running safely in paper mode.")
    st.markdown(
        "Edit **`config.yaml`** to change your watchlist, the signal weights, "
        "buy/sell thresholds, and the news/sentiment providers, then re-run the app."
    )
    st.json(cfg)
