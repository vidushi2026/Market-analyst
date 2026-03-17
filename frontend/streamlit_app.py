import requests
import streamlit as st
import os
from typing import Optional
import pandas as pd


st.set_page_config(page_title="Market Analyst", layout="wide")

st.title("Market Analyst")
backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")

mode = st.sidebar.selectbox("Mode", ["Stock", "Compare", "Portfolio"])

SIGNAL_EXPLANATIONS = {
    # Fundamental
    "roe_ok": "Return on equity looks healthy (>= 12%).",
    "roe_weak": "Return on equity looks weak (< 12%).",
    "leverage_ok": "Debt-to-equity looks manageable (<= 150).",
    "leverage_high": "Debt-to-equity looks high (> 150).",
    "margins_ok": "Profit margins look healthy (>= 10%).",
    "margins_thin": "Profit margins look thin (< 10%).",
    # Technical
    "ma_bullish": "Short-term average is meaningfully above long-term average (bullish bias).",
    "ma_bearish": "Short-term average is meaningfully below long-term average (bearish bias).",
    "ma_flat": "Short and long averages are close (sideways / no clear trend).",
    "insufficient_price_history": "Not enough price data to compute indicators reliably.",
    # Sentiment
    "headline_sentiment_positive": "Recent headlines skew positive.",
    "headline_sentiment_neutral": "Recent headlines look neutral/mixed.",
    "headline_sentiment_negative": "Recent headlines skew negative.",
    "no_headlines": "No recent headlines found for sentiment estimation.",
}


def _format_status(status: str) -> str:
    if status == "ok":
        return "OK"
    if status == "partial":
        return "Partial"
    if status == "error":
        return "Error"
    return status


def _render_signals(signals: list) -> None:
    if not signals:
        st.caption("No signals produced.")
        return
    lines = []
    for s in signals:
        explanation = SIGNAL_EXPLANATIONS.get(s)
        if explanation:
            lines.append(f"- **{s}**: {explanation}")
        else:
            lines.append(f"- **{s}**")
    st.markdown("\n".join(lines))


def _render_key_events(key_events: list) -> None:
    if not key_events:
        return
    st.markdown("**Recent headlines/events:**")
    st.markdown("\n".join([f"- {e}" for e in key_events]))


def _decision_from_score(score: float) -> str:
    if score > 7.5:
        return "Strong Buy"
    if score >= 5.5:
        return "Buy"
    if score >= 4.0:
        return "Hold"
    return "Avoid/Sell"


def _render_stock_like_result(data: dict, title: Optional[str] = None) -> None:
    if title:
        st.subheader(title)

    cols = st.columns(3)
    final_score = float(data.get("final_score", 0) or 0)
    recommendation = data.get("final_recommendation") or _decision_from_score(final_score)
    cols[0].metric("Recommendation", str(recommendation))
    cols[1].metric("Final score", f"{final_score:.2f}")
    conf = data.get("confidence")
    cols[2].metric("Confidence", f"{float(conf):.2f}" if conf is not None else "-")

    breakdown = data.get("agent_breakdown") or {}
    for agent_name, agent_out in breakdown.items():
        base = agent_name.capitalize()
        if isinstance(agent_out, dict) and agent_out.get("status"):
            base = f"{base} — {_format_status(agent_out.get('status'))}"

        with st.expander(base, expanded=False):
            if isinstance(agent_out, dict):
                summary = agent_out.get("summary", "")
                if summary:
                    st.write(summary)
                if "trend" in agent_out:
                    st.markdown(f"**Trend:** `{agent_out.get('trend')}`")
                if "sentiment" in agent_out:
                    st.markdown(f"**Sentiment:** `{agent_out.get('sentiment')}`")

                st.markdown("**Signals:**")
                _render_signals(agent_out.get("signals") or [])
                _render_key_events(agent_out.get("key_events") or [])

                if agent_out.get("status") == "partial":
                    st.info("This agent returned partial data (some upstream fields were missing or insufficient).")
                if agent_out.get("status") == "error":
                    st.error("This agent failed to run.")
            else:
                st.write(agent_out)


def render_response(resp_json: dict) -> None:
    if resp_json.get("status") != "ok":
        st.error(resp_json.get("error", {}).get("message", "Request failed"))
        with st.expander("Error details"):
            st.json(resp_json)
        return

    data = resp_json.get("data") or {}

    # Stock analysis shape
    if "final_recommendation" in data:
        _render_stock_like_result(data, title=None)
        return

    # Compare / portfolio: show a readable summary
    if "winner" in data:
        st.metric("Winner", str(data.get("winner")))
        st.write(data.get("reason", ""))

        side = data.get("side_by_side") or {}
        left = side.get("left") or {}
        right = side.get("right") or {}
        if left and right:
            st.subheader("Side-by-side comparison")
            c1, c2 = st.columns(2)
            with c1:
                _render_stock_like_result(left, title=str(left.get("ticker", "Left")))
            with c2:
                _render_stock_like_result(right, title=str(right.get("ticker", "Right")))

    if "per_stock" in data:
        st.subheader("Portfolio summary")
        cols = st.columns(3)
        cols[0].metric("Risk level", str(data.get("risk_level", "-")))
        cols[1].metric("Diversification score", str(data.get("diversification_score", "-")))
        cols[2].metric("Portfolio health", str(data.get("portfolio_health", "-")))

        if data.get("summary"):
            st.write(data["summary"])

        per_stock = data.get("per_stock") or []
        rows = []
        for item in per_stock:
            score = float(item.get("final_score", 0) or 0)
            rows.append(
                {
                    "Ticker": item.get("ticker", ""),
                    "Final score": round(score, 2),
                    "Recommendation": _decision_from_score(score),
                }
            )
        if rows:
            st.subheader("Per-stock results")
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            for item in per_stock:
                t = item.get("ticker", "Stock")
                with st.expander(f"{t} details", expanded=False):
                    _render_stock_like_result(
                        {
                            "final_score": item.get("final_score"),
                            "agent_breakdown": item.get("agent_breakdown"),
                        },
                        title=None,
                    )

        weakest = data.get("weakest")
        strongest = data.get("strongest")
        if isinstance(weakest, dict) and isinstance(strongest, dict):
            st.subheader("Strongest / Weakest")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**Strongest:** `{strongest.get('ticker')}`")
                if strongest.get("reason"):
                    st.write(strongest["reason"])
            with c2:
                st.markdown(f"**Weakest:** `{weakest.get('ticker')}`")
                if weakest.get("reason"):
                    st.write(weakest["reason"])


if mode == "Stock":
    ticker = st.text_input("Ticker", value="AAPL")
    period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y"], index=2)
    interval = st.selectbox("Interval", ["1d", "1h"], index=0)
    if st.button("Analyze"):
        resp = requests.post(
            f"{backend_url}/analyze/stock",
            json={"ticker": ticker, "options": {"period": period, "interval": interval}},
            timeout=60,
        )
        render_response(resp.json())

elif mode == "Compare":
    left = st.text_input("Left ticker", value="AAPL")
    right = st.text_input("Right ticker", value="MSFT")
    period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y"], index=2)
    interval = st.selectbox("Interval", ["1d", "1h"], index=0)
    if st.button("Compare"):
        resp = requests.post(
            f"{backend_url}/compare",
            json={"stocks": [left, right], "options": {"period": period, "interval": interval}},
            timeout=60,
        )
        render_response(resp.json())

else:
    st.write("Enter portfolio items as ticker + weight. Weights must sum to 1 (or close).")
    tickers = st.text_area("Portfolio (one per line: TICKER,WEIGHT)", value="AAPL,0.5\nMSFT,0.5")
    period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y"], index=3)
    interval = st.selectbox("Interval", ["1d", "1h"], index=0)
    if st.button("Analyze portfolio"):
        portfolio = []
        for line in tickers.splitlines():
            line = line.strip()
            if not line:
                continue
            t, w = [x.strip() for x in line.split(",", 1)]
            portfolio.append({"ticker": t, "weight": float(w)})
        resp = requests.post(
            f"{backend_url}/analyze/portfolio",
            json={"portfolio": portfolio, "options": {"period": period, "interval": interval}},
            timeout=60,
        )
        render_response(resp.json())

