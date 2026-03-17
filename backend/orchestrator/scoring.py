from __future__ import annotations

from typing import Any, Dict, Tuple

from config.settings import settings


def clamp_0_10(x: float) -> float:
    return max(0.0, min(10.0, x))


def pull_to_neutral_if_partial(score: float, status: str) -> float:
    if status != "partial":
        return score
    # score' = 5 + 0.7 * (score - 5)
    return clamp_0_10(5.0 + 0.7 * (score - 5.0))


def normalize_agent_score(agent_result: Dict[str, Any]) -> float:
    score = float(agent_result.get("score", 5.0))
    status = agent_result.get("status", "partial")
    return pull_to_neutral_if_partial(clamp_0_10(score), status)


def renormalize_weights(available: Dict[str, float]) -> Dict[str, float]:
    s = sum(available.values())
    if s <= 0:
        return {k: 0.0 for k in available}
    return {k: v / s for k, v in available.items()}


def compute_final_score(agent_results: Dict[str, Dict[str, Any]]) -> Tuple[float, Dict[str, float]]:
    weights = {
        "fundamental": settings.weight_fundamental,
        "technical": settings.weight_technical,
        "sentiment": settings.weight_sentiment,
    }

    available = {}
    for k, w in weights.items():
        r = agent_results.get(k)
        if r is None:
            continue
        if r.get("status") == "error":
            continue
        available[k] = w

    norm_w = renormalize_weights(available)
    total = 0.0
    contributions: Dict[str, float] = {}
    for k, w in norm_w.items():
        s = normalize_agent_score(agent_results[k])
        contrib = w * s
        contributions[k] = contrib
        total += contrib

    return (clamp_0_10(total), contributions)


def decision_from_score(final_score: float) -> str:
    if final_score > 7.5:
        return "Strong Buy"
    if final_score >= 5.5:
        return "Buy"
    if final_score >= 4.0:
        return "Hold"
    return "Avoid/Sell"


def confidence_from_agents(agent_results: Dict[str, Dict[str, Any]], contributions: Dict[str, float]) -> float:
    # Weighted average of agent confidences, fallback to heuristic.
    weights = {k: v for k, v in contributions.items() if v is not None}
    if not weights:
        return 0.2

    # Convert contributions back into weights
    s = sum(weights.values())
    if s <= 0:
        return 0.2
    norm = {k: v / s for k, v in weights.items()}

    confs = []
    for k, w in norm.items():
        c = agent_results.get(k, {}).get("confidence")
        if c is None:
            continue
        confs.append(w * float(c))
    if confs:
        return max(0.0, min(1.0, sum(confs)))

    # Heuristic: more ok agents => higher; partial lowers.
    ok = sum(1 for r in agent_results.values() if r and r.get("status") == "ok")
    partial = sum(1 for r in agent_results.values() if r and r.get("status") == "partial")
    return max(0.0, min(1.0, 0.35 + 0.15 * ok - 0.10 * partial))

