from __future__ import annotations

from typing import Any, Dict, List

import numpy as np

from backend.services.yahoo_service import YahooService
from backend.utils.logging_utils import get_logger

logger = get_logger(__name__)


def _clamp_0_10(x: float) -> float:
    return max(0.0, min(10.0, x))


class TechnicalAgent:
    name = "technical"

    def __init__(self, yahoo: YahooService) -> None:
        self._yahoo = yahoo

    def run(self, ticker: str, period: str, interval: str) -> Dict[str, Any]:
        logger.info("agent.technical.start ticker=%s period=%s interval=%s", ticker, period, interval)
        prices = self._yahoo.get_price_history(ticker, period=period, interval=interval)
        rows = prices.get("rows", [])
        closes = [r.get("close", 0.0) for r in rows if r.get("close") is not None]

        signals: List[str] = []
        if len(closes) < 10:
            logger.info("agent.technical.partial ticker=%s reason=insufficient_data", ticker)
            return {
                "agent": "technical",
                "status": "partial",
                "summary": "Not enough price data to compute indicators.",
                "score": 5.0,
                "signals": ["insufficient_price_history"],
                "trend": "sideways",
            }

        closes_np = np.array(closes, dtype=float)
        short = float(np.mean(closes_np[-20:])) if len(closes_np) >= 20 else float(np.mean(closes_np))
        long = float(np.mean(closes_np[-50:])) if len(closes_np) >= 50 else float(np.mean(closes_np))

        trend = "sideways"
        score = 5.0
        if short > long * 1.01:
            trend = "bullish"
            signals.append("ma_bullish")
            score = 8.0
        elif short < long * 0.99:
            trend = "bearish"
            signals.append("ma_bearish")
            score = 2.0
        else:
            signals.append("ma_flat")

        score = _clamp_0_10(score)
        logger.info("agent.technical.done ticker=%s trend=%s score=%.2f", ticker, trend, score)
        return {
            "agent": "technical",
            "status": "ok",
            "summary": "Technical analysis based on moving-average trend proxy.",
            "score": score,
            "signals": signals,
            "trend": trend,
        }

