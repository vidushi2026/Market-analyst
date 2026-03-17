from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import DefaultDict, Dict


@dataclass
class _TimerAgg:
    count: int = 0
    total_ms: float = 0.0
    max_ms: float = 0.0

    def add(self, ms: float) -> None:
        self.count += 1
        self.total_ms += ms
        self.max_ms = max(self.max_ms, ms)


class Metrics:
    """
    Minimal in-process metrics (v1).

    This intentionally avoids external dependencies (Prometheus/etc.) while providing:
    - counters
    - timing aggregations
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: DefaultDict[str, int] = defaultdict(int)
        self._timers: Dict[str, _TimerAgg] = {}

    def inc(self, name: str, value: int = 1) -> None:
        with self._lock:
            self._counters[name] += value

    def observe_ms(self, name: str, ms: float) -> None:
        with self._lock:
            agg = self._timers.get(name)
            if agg is None:
                agg = _TimerAgg()
                self._timers[name] = agg
            agg.add(ms)

    def snapshot(self) -> Dict[str, object]:
        with self._lock:
            timers = {
                k: {
                    "count": v.count,
                    "avg_ms": (v.total_ms / v.count) if v.count else 0.0,
                    "max_ms": v.max_ms,
                }
                for k, v in self._timers.items()
            }
            return {"counters": dict(self._counters), "timers": timers, "ts": time.time()}


metrics = Metrics()

