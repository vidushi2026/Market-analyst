from __future__ import annotations

from typing import Any, Dict, List

from backend.services.search_service import SearchService
from backend.utils.logging_utils import get_logger

logger = get_logger(__name__)


def _sentiment_from_headlines(headlines: List[str]) -> str:
    # Mockable heuristic sentiment classifier (no LLM calls).
    negative = ("lawsuit", "fraud", "probe", "crash", "decline", "miss", "downgrade", "fine")
    positive = ("beat", "record", "surge", "upgrade", "growth", "profit", "raises", "wins")

    score = 0
    for h in headlines:
        hl = h.lower()
        if any(w in hl for w in positive):
            score += 1
        if any(w in hl for w in negative):
            score -= 1

    if score >= 2:
        return "positive"
    if score <= -2:
        return "negative"
    return "neutral"


class SentimentAgent:
    name = "sentiment"

    def __init__(self, search: SearchService) -> None:
        self._search = search

    def run(self, query: str) -> Dict[str, Any]:
        logger.info("agent.sentiment.start query=%s", query)
        news = self._search.get_news(query=query, max_results=8, window="7d")
        items = news.get("items", [])

        headlines = [i.get("title", "") for i in items if i.get("title")]
        if not headlines:
            logger.info("agent.sentiment.partial query=%s reason=no_headlines", query)
            return {
                "agent": "sentiment",
                "status": "partial",
                "summary": "No recent headlines available to estimate sentiment.",
                "score": 5.0,
                "confidence": 0.3,
                "signals": ["no_headlines"],
                "sentiment": "neutral",
                "key_events": [],
            }

        sentiment = _sentiment_from_headlines(headlines)
        score = {"positive": 8.0, "neutral": 5.0, "negative": 2.0}[sentiment]
        confidence = 0.5 + min(0.4, len(headlines) * 0.03)
        key_events = headlines[:3]

        logger.info("agent.sentiment.done query=%s sentiment=%s score=%.2f", query, sentiment, score)
        return {
            "agent": "sentiment",
            "status": "ok",
            "summary": "Headline-based sentiment estimate (heuristic; no LLM).",
            "score": score,
            "confidence": confidence,
            "signals": [f"headline_sentiment_{sentiment}"],
            "sentiment": sentiment,
            "key_events": key_events,
        }

