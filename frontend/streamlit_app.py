import requests
import streamlit as st


st.set_page_config(page_title="Market Analyst", layout="wide")

st.title("Market Analyst")
backend_url = st.sidebar.text_input("Backend URL", value="http://localhost:8000")

mode = st.sidebar.selectbox("Mode", ["Stock", "Compare", "Portfolio"])


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
            with st.expander(agent_name.capitalize(), expanded=False):
                if isinstance(agent_out, dict):
                    st.write(agent_out.get("summary", ""))
                    if "trend" in agent_out:
                        st.write(f"Trend: `{agent_out.get('trend')}`")
                    if "sentiment" in agent_out:
                        st.write(f"Sentiment: `{agent_out.get('sentiment')}`")
                    if agent_out.get("signals"):
                        st.write("Signals:")
                        st.write(agent_out.get("signals"))
                    if agent_out.get("key_events"):
                        st.write("Key events:")
                        st.write(agent_out.get("key_events"))
                else:
                    st.write(agent_out)

        if data.get("explanation"):
            st.subheader("Explanation")
            st.write(data["explanation"])
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

