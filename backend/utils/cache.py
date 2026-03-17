import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class CacheEntry:
    value: Any
    expires_at: float


class TTLCache:
    def __init__(self) -> None:
        self._data: Dict[str, CacheEntry] = {}
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        entry = self._data.get(key)
        if entry is None:
            self._misses += 1
            return None
        if time.time() >= entry.expires_at:
            self._data.pop(key, None)
            self._misses += 1
            return None
        self._hits += 1
        return entry.value

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        self._data[key] = CacheEntry(value=value, expires_at=time.time() + ttl_seconds)

    def stats(self) -> Tuple[int, int]:
        # (items, expired_removed)
        expired = 0
        now = time.time()
        for k, v in list(self._data.items()):
            if now >= v.expires_at:
                self._data.pop(k, None)
                expired += 1
        return (len(self._data), expired)

    def hit_miss(self) -> Tuple[int, int]:
        return (self._hits, self._misses)

