from backend.utils.metrics import Metrics


def test_metrics_snapshot_contains_counters_and_timers():
    m = Metrics()
    m.inc("x")
    m.observe_ms("t", 12.0)
    snap = m.snapshot()
    assert "counters" in snap
    assert snap["counters"]["x"] == 1
    assert "timers" in snap
    assert snap["timers"]["t"]["count"] == 1

