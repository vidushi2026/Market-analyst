from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_health_envelope():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "request_id" in body


def test_metrics_shape():
    r = client.get("/metrics")
    assert r.status_code == 200
    body = r.json()
    assert "counters" in body
    assert "timers" in body


def test_analyze_stock_contract(monkeypatch):
    # Avoid any upstream calls by monkeypatching the module-level orchestrator.
    import backend.routes.analyze as analyze_mod

    def fake_analyze_stock(ticker: str, period: str, interval: str):
        return {
            "request_id": "internal",
            "final_recommendation": "Hold",
            "confidence": 0.5,
            "final_score": 5.0,
            "agent_breakdown": {"fundamental": {}, "technical": {}, "sentiment": {}},
            "explanation": "fake",
        }

    monkeypatch.setattr(analyze_mod, "_orchestrator", type("O", (), {"analyze_stock": staticmethod(fake_analyze_stock)})())

    r = client.post("/analyze/stock", json={"ticker": "AAPL", "options": {"period": "6mo", "interval": "1d"}})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "request_id" in body
    assert "data" in body
    assert body["data"]["final_recommendation"] in ["Strong Buy", "Buy", "Hold", "Avoid/Sell", "Sell"]


def test_compare_validation_requires_two_stocks():
    r = client.post("/compare", json={"stocks": ["AAPL"], "options": {"period": "6mo", "interval": "1d"}})
    # pydantic validation error surfaces as 422 from FastAPI
    assert r.status_code == 422

