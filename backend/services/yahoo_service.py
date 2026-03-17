from __future__ import annotations

from datetime import datetime
import time
from typing import Any, Dict

import yfinance as yf

from config.settings import settings
from backend.utils.cache import TTLCache
from backend.utils.logging_utils import get_logger
from backend.utils.metrics import metrics

logger = get_logger(__name__)


class YahooService:
    def __init__(self, cache: TTLCache) -> None:
        self._cache = cache

    def get_price_history(self, ticker: str, period: str, interval: str) -> Dict[str, Any]:
        cache_key = f"prices:{ticker}:{period}:{interval}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.info("yahoo.cache_hit prices %s", cache_key)
            metrics.inc("cache_hit_prices")
            return cached

        metrics.inc("cache_miss_prices")
        logger.info("yahoo.fetch prices ticker=%s period=%s interval=%s", ticker, period, interval)
        t0 = time.time()
        df = yf.Ticker(ticker).history(period=period, interval=interval)
        metrics.observe_ms("upstream_yahoo_prices_ms", (time.time() - t0) * 1000.0)
        rows = []
        for idx, row in df.iterrows():
            ts = idx.to_pydatetime().isoformat()
            rows.append(
                {
                    "ts": ts,
                    "open": float(row.get("Open", 0.0)),
                    "high": float(row.get("High", 0.0)),
                    "low": float(row.get("Low", 0.0)),
                    "close": float(row.get("Close", 0.0)),
                    "volume": float(row.get("Volume", 0.0)),
                }
            )

        payload = {
            "ticker": ticker,
            "as_of": datetime.utcnow().isoformat() + "Z",
            "interval": interval,
            "period": period,
            "rows": rows,
        }

        ttl = settings.ttl_prices_intraday if interval not in ("1d", "1wk", "1mo") else settings.ttl_prices_daily
        self._cache.set(cache_key, payload, ttl_seconds=ttl)
        return payload

    def get_fundamentals(self, ticker: str) -> Dict[str, Any]:
        cache_key = f"fundamentals:{ticker}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.info("yahoo.cache_hit fundamentals %s", cache_key)
            metrics.inc("cache_hit_fundamentals")
            return cached

        metrics.inc("cache_miss_fundamentals")
        logger.info("yahoo.fetch fundamentals ticker=%s", ticker)
        t = yf.Ticker(ticker)
        t0 = time.time()
        info = t.info or {}
        metrics.observe_ms("upstream_yahoo_fundamentals_ms", (time.time() - t0) * 1000.0)

        payload = {
            "ticker": ticker,
            "as_of": datetime.utcnow().isoformat() + "Z",
            "info": {
                "trailingPE": info.get("trailingPE"),
                "forwardPE": info.get("forwardPE"),
                "epsTrailingTwelveMonths": info.get("epsTrailingTwelveMonths"),
                "returnOnEquity": info.get("returnOnEquity"),
                "debtToEquity": info.get("debtToEquity"),
                "profitMargins": info.get("profitMargins"),
                "revenueGrowth": info.get("revenueGrowth"),
                "earningsGrowth": info.get("earningsGrowth"),
                "marketCap": info.get("marketCap"),
                "sector": info.get("sector"),
            },
        }

        self._cache.set(cache_key, payload, ttl_seconds=settings.ttl_fundamentals)
        return payload

