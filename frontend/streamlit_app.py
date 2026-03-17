import requests
import streamlit as st


st.set_page_config(page_title="Market Analyst", layout="wide")

st.title("Market Analyst")
backend_url = st.sidebar.text_input("Backend URL", value="http://localhost:8000")

mode = st.sidebar.selectbox("Mode", ["Stock", "Compare", "Portfolio"])

if mode == "Stock":
    ticker = st.text_input("Ticker", value="AAPL")
    period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y"], index=2)
    interval = st.selectbox("Interval", ["1d", "1h"], index=0)
    if st.button("Analyze"):
        resp = requests.post(f"{backend_url}/analyze/stock", json={"ticker": ticker, "options": {"period": period, "interval": interval}})
        st.json(resp.json())

elif mode == "Compare":
    left = st.text_input("Left ticker", value="AAPL")
    right = st.text_input("Right ticker", value="MSFT")
    period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y"], index=2)
    interval = st.selectbox("Interval", ["1d", "1h"], index=0)
    if st.button("Compare"):
        resp = requests.post(f"{backend_url}/compare", json={"stocks": [left, right], "options": {"period": period, "interval": interval}})
        st.json(resp.json())

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
        )
        st.json(resp.json())

