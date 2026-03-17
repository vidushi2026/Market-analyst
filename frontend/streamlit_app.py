import requests
import streamlit as st
import os


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


def render_response(resp_json: dict) -> None:
    if resp_json.get("status") != "ok":
        st.error(resp_json.get("error", {}).get("message", "Request failed"))
        with st.expander("Error details"):
            st.json(resp_json)
        return

    data = resp_json.get("data") or {}

    # Stock analysis shape
    if "final_recommendation" in data:
        cols = st.columns(3)
        cols[0].metric("Recommendation", str(data.get("final_recommendation")))
        cols[1].metric("Final score", f"{float(data.get('final_score', 0)):.2f}")
        cols[2].metric("Confidence", f"{float(data.get('confidence', 0)):.2f}")

        st.subheader("Agent breakdown")
        breakdown = data.get("agent_breakdown") or {}
        for agent_name, agent_out in breakdown.items():
            title = agent_name.capitalize()
            if isinstance(agent_out, dict) and agent_out.get("status"):
                title = f"{title} — {_format_status(agent_out.get('status'))}"

            with st.expander(title, expanded=False):
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

        return

    # Compare / portfolio: show a readable summary, keep JSON in expander
    if "winner" in data:
        st.metric("Winner", str(data.get("winner")))
        st.write(data.get("reason", ""))

    if "per_stock" in data:
        st.subheader("Per-stock results")
        st.write(data.get("per_stock"))

    with st.expander("Raw response JSON"):
        st.json(resp_json)


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

