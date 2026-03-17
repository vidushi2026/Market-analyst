from __future__ import annotations

from datetime import datetime
import time
from typing import Any, Dict, List

from duckduckgo_search import DDGS

from config.settings import settings
from backend.utils.cache import TTLCache
from backend.utils.logging_utils import get_logger
from backend.utils.metrics import metrics

logger = get_logger(__name__)


class SearchService:
    def __init__(self, cache: TTLCache) -> None:
        self._cache = cache

    def get_news(self, query: str, max_results: int = 8, window: str = "7d") -> Dict[str, Any]:
        cache_key = f"news:{query}:{window}:{max_results}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.info("news.cache_hit %s", cache_key)
            metrics.inc("cache_hit_news")
            return cached

        metrics.inc("cache_miss_news")
        logger.info("news.fetch query=%s max_results=%s window=%s", query, max_results, window)
        t0 = time.time()
        items: List[Dict[str, Any]] = []
        with DDGS() as ddgs:
            # DuckDuckGo API shape varies; keep minimal normalized fields
            for r in ddgs.news(query, max_results=max_results):
                items.append(
                    {
                        "title": r.get("title") or "",
                        "url": r.get("url") or "",
                        "source": r.get("source"),
                        "published_at": r.get("date"),
                        "snippet": r.get("body"),
                    }
                )

        metrics.observe_ms("upstream_ddg_news_ms", (time.time() - t0) * 1000.0)
        payload = {"query": query, "as_of": datetime.utcnow().isoformat() + "Z", "items": items}
        self._cache.set(cache_key, payload, ttl_seconds=settings.ttl_news)
        return payload

