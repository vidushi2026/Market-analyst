from backend.orchestrator.scoring import compute_final_score, decision_from_score


def test_decision_thresholds():
    assert decision_from_score(8.0) == "Strong Buy"
    assert decision_from_score(7.5) == "Buy"
    assert decision_from_score(5.5) == "Buy"
    assert decision_from_score(5.49) == "Hold"
    assert decision_from_score(4.0) == "Hold"
    assert decision_from_score(3.99) == "Avoid/Sell"


def test_compute_final_score_renormalizes_missing_agent():
    agent_results = {
        "fundamental": {"status": "ok", "score": 10},
        "technical": {"status": "ok", "score": 0},
        # sentiment missing
    }
    score, contributions = compute_final_score(agent_results)
    assert 0 <= score <= 10
    assert "fundamental" in contributions
    assert "technical" in contributions

