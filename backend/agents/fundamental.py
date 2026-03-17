from __future__ import annotations

from typing import Any, Dict, List

from backend.services.yahoo_service import YahooService
from backend.utils.logging_utils import get_logger

logger = get_logger(__name__)


def _clamp_0_10(x: float) -> float:
    return max(0.0, min(10.0, x))


class FundamentalAgent:
    name = "fundamental"

    def __init__(self, yahoo: YahooService) -> None:
        self._yahoo = yahoo

    def run(self, ticker: str) -> Dict[str, Any]:
        logger.info("agent.fundamental.start ticker=%s", ticker)
        fundamentals = self._yahoo.get_fundamentals(ticker)
        info = fundamentals.get("info", {})

        signals: List[str] = []

        roe = info.get("returnOnEquity")
        if roe is not None:
            signals.append("roe_ok" if roe >= 0.12 else "roe_weak")

        dte = info.get("debtToEquity")
        if dte is not None:
            signals.append("leverage_ok" if dte <= 150 else "leverage_high")

        pm = info.get("profitMargins")
        if pm is not None:
            signals.append("margins_ok" if pm >= 0.10 else "margins_thin")

        # Simple heuristic score around neutral, based on available signals
        score = 5.0
        for s in signals:
            if s.endswith("_ok"):
                score += 1.0
            elif s.endswith("_weak") or s.endswith("_high") or s.endswith("_thin"):
                score -= 1.0

        score = _clamp_0_10(score)
        status = "ok" if signals else "partial"
        summary = "Fundamental analysis computed from available Yahoo Finance fundamentals."

        logger.info("agent.fundamental.done ticker=%s score=%.2f status=%s", ticker, score, status)
        return {"agent": "fundamental", "status": status, "summary": summary, "score": score, "signals": signals}

