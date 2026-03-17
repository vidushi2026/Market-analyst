from __future__ import annotations

import uuid
from typing import Any, Dict, List

from backend.agents.fundamental import FundamentalAgent
from backend.agents.sentiment import SentimentAgent
from backend.agents.technical import TechnicalAgent
from backend.orchestrator.scoring import (
    compute_final_score,
    confidence_from_agents,
    decision_from_score,
)
from backend.utils.logging_utils import get_logger

logger = get_logger(__name__)


class Orchestrator:
    def __init__(
        self,
        fundamental: FundamentalAgent,
        technical: TechnicalAgent,
        sentiment: SentimentAgent,
    ) -> None:
        self._fundamental = fundamental
        self._technical = technical
        self._sentiment = sentiment

    def analyze_stock(self, ticker: str, period: str, interval: str) -> Dict[str, Any]:
        request_id = str(uuid.uuid4())
        logger.info("orchestrator.analyze_stock.start request_id=%s ticker=%s", request_id, ticker)

        agent_results: Dict[str, Dict[str, Any]] = {}
        # v1: sequential execution (safe + simple); can be parallelized later.
        try:
            agent_results["fundamental"] = self._fundamental.run(ticker)
        except Exception as e:  # noqa: BLE001
            logger.info("orchestrator.agent_error request_id=%s agent=fundamental err=%s", request_id, str(e))
            agent_results["fundamental"] = {"agent": "fundamental", "status": "error", "summary": "failed", "error": {"code": "INTERNAL_ERROR", "message": str(e), "details": {}}}

        try:
            agent_results["technical"] = self._technical.run(ticker, period=period, interval=interval)
        except Exception as e:  # noqa: BLE001
            logger.info("orchestrator.agent_error request_id=%s agent=technical err=%s", request_id, str(e))
            agent_results["technical"] = {"agent": "technical", "status": "error", "summary": "failed", "error": {"code": "INTERNAL_ERROR", "message": str(e), "details": {}}}

        try:
            agent_results["sentiment"] = self._sentiment.run(query=ticker)
        except Exception as e:  # noqa: BLE001
            logger.info("orchestrator.agent_error request_id=%s agent=sentiment err=%s", request_id, str(e))
            agent_results["sentiment"] = {"agent": "sentiment", "status": "error", "summary": "failed", "error": {"code": "INTERNAL_ERROR", "message": str(e), "details": {}}}

        final_score, contributions = compute_final_score(agent_results)
        recommendation = decision_from_score(final_score)
        confidence = confidence_from_agents(agent_results, contributions)

        response = {
            "request_id": request_id,
            "final_recommendation": recommendation,
            "confidence": confidence,
            "final_score": final_score,
            "agent_breakdown": {
                "fundamental": agent_results.get("fundamental"),
                "technical": agent_results.get("technical"),
                "sentiment": agent_results.get("sentiment"),
            },
            "explanation": "Combined fundamental, technical, and sentiment signals using Phase 6 weights and thresholds.",
        }

        logger.info(
            "orchestrator.analyze_stock.done request_id=%s ticker=%s final_score=%.2f rec=%s",
            request_id,
            ticker,
            final_score,
            recommendation,
        )
        return response

    def compare(self, left: str, right: str, period: str, interval: str) -> Dict[str, Any]:
        request_id = str(uuid.uuid4())
        logger.info("orchestrator.compare.start request_id=%s left=%s right=%s", request_id, left, right)
        left_r = self.analyze_stock(left, period=period, interval=interval)
        right_r = self.analyze_stock(right, period=period, interval=interval)

        # Tie-break rules (Phase 6): score, then confidence
        winner = left if (left_r["final_score"], left_r["confidence"]) >= (right_r["final_score"], right_r["confidence"]) else right
        reason = "Selected by higher final_score; ties broken by higher confidence."

        logger.info("orchestrator.compare.done request_id=%s winner=%s", request_id, winner)
        return {
            "request_id": request_id,
            "winner": winner,
            "reason": reason,
            "side_by_side": {"left": {"ticker": left, **left_r}, "right": {"ticker": right, **right_r}},
        }

    def analyze_portfolio(self, items: List[Dict[str, Any]], period: str, interval: str) -> Dict[str, Any]:
        request_id = str(uuid.uuid4())
        logger.info("orchestrator.analyze_portfolio.start request_id=%s n=%s", request_id, len(items))

        per_stock = []
        for it in items:
            t = it["ticker"]
            per_stock.append({"ticker": t, "weight": it.get("weight"), **self.analyze_stock(t, period=period, interval=interval)})

        # v1 roll-up: average final_score weighted by provided weights (or equal-weight)
        weights = [p.get("weight") for p in per_stock]
        if any(w is None for w in weights):
            weights = [1.0 / len(per_stock)] * len(per_stock)
        s = sum(float(w) for w in weights) or 1.0
        weights = [float(w) / s for w in weights]

        portfolio_score = sum(w * float(p["final_score"]) for w, p in zip(weights, per_stock))
        strongest = max(per_stock, key=lambda x: x["final_score"])
        weakest = min(per_stock, key=lambda x: x["final_score"])

        result = {
            "request_id": request_id,
            "portfolio_health": "Computed from constituent scores (v1).",
            "summary": "Portfolio roll-up is a weighted average of constituent final scores (v1).",
            "risk_level": "medium",
            "diversification_score": 5.0,
            "weakest": {"ticker": weakest["ticker"], "reason": "Lowest final_score among constituents."},
            "strongest": {"ticker": strongest["ticker"], "reason": "Highest final_score among constituents."},
            "suggested_rebalance": [],
            "per_stock": [{"ticker": p["ticker"], "final_score": p["final_score"], "agent_breakdown": p["agent_breakdown"]} for p in per_stock],
        }

        logger.info("orchestrator.analyze_portfolio.done request_id=%s portfolio_score=%.2f", request_id, portfolio_score)
        return result

