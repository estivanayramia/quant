from __future__ import annotations

from typing import Any

from quant_os.execution.pm_crypto_updown_shadow_intents import (
    build_pm_crypto_updown_shadow_intents,
)
from quant_os.research.replay_candidates.pm_crypto_updown_schema import CANDIDATE_ID
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

CONSERVATIVE_VARIANTS = (
    "STRICT_LIMIT_ONLY",
    "PASSIVE_LIMIT_WITH_NO_FILL",
    "SMALL_SIZE_SPREAD_CAPPED",
    "CROSS_ONLY_IF_EDGE_SURVIVES_WORST_CASE",
)
TOO_LENIENT_CONTROL = "TOO_LENIENT_REJECTED_CONTROL"


def evaluate_pm_crypto_updown_fill_variants(
    *,
    rows: list[dict[str, Any]],
    signal_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    intents = build_pm_crypto_updown_shadow_intents(rows=rows, signal_report=signal_report)
    variants = [
        _variant("STRICT_LIMIT_ONLY", intents),
        _variant("PASSIVE_LIMIT_WITH_NO_FILL", intents),
        _variant("SMALL_SIZE_SPREAD_CAPPED", intents),
        _variant("CROSS_ONLY_IF_EDGE_SURVIVES_WORST_CASE", intents),
        _too_lenient_control(intents),
    ]
    return {
        "schema_version": "pm_crypto_updown_fill_variants_v1",
        "sequence": "43",
        "candidate_id": CANDIDATE_ID,
        "variants": variants,
        "too_lenient_control_promotes_readiness": False,
        "conservative_variant_ids": list(CONSERVATIVE_VARIANTS),
        "network_fetch_attempted": False,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _variant(variant_id: str, intents: list[dict[str, Any]]) -> dict[str, Any]:
    allowed = _allowed_for_variant(variant_id, intents)
    blocked_count = len(intents) - len(allowed)
    filled_count, no_fill_count, partial_fill_count = _fill_counts(variant_id, allowed)
    cost_adjusted = _cost_adjusted_result(variant_id, allowed)
    return {
        "variant_id": variant_id,
        "assumption_classification": "CONSERVATIVE",
        "allowed_intent_count": len(allowed),
        "blocked_intent_count": blocked_count,
        "filled_count": filled_count,
        "no_fill_count": no_fill_count,
        "partial_fill_count": partial_fill_count,
        "cost_adjusted_result": round(cost_adjusted, 6),
        "baseline_comparison": _comparison(cost_adjusted),
        "placebo_comparison": _comparison(cost_adjusted),
        "can_promote_readiness": cost_adjusted > 0.0 and len(allowed) > 0,
    }


def _allowed_for_variant(variant_id: str, intents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    allowed = [item for item in intents if item["decision"] == "ALLOW_SHADOW_INTENT"]
    if variant_id == "SMALL_SIZE_SPREAD_CAPPED":
        return [item for item in allowed if item["conservative_cost"] <= 0.06]
    if variant_id == "CROSS_ONLY_IF_EDGE_SURVIVES_WORST_CASE":
        return [item for item in allowed if item["expected_edge_after_cost"] >= 0.05]
    return allowed


def _fill_counts(variant_id: str, allowed: list[dict[str, Any]]) -> tuple[int, int, int]:
    partial = sum(1 for item in allowed if item["fill_assumption"] == "PARTIAL_FILL_ALLOWED")
    if variant_id == "PASSIVE_LIMIT_WITH_NO_FILL":
        no_fill = sum(1 for index, _item in enumerate(allowed) if index % 3 == 0)
        return len(allowed) - no_fill, no_fill, partial
    if variant_id == "STRICT_LIMIT_ONLY":
        return len(allowed), 0, partial
    if variant_id == "SMALL_SIZE_SPREAD_CAPPED":
        no_fill = sum(1 for index, _item in enumerate(allowed) if index % 4 == 0)
        return len(allowed) - no_fill, no_fill, partial
    no_fill = sum(1 for index, _item in enumerate(allowed) if index % 2 == 1)
    return len(allowed) - no_fill, no_fill, partial


def _cost_adjusted_result(variant_id: str, allowed: list[dict[str, Any]]) -> float:
    result = 0.0
    for index, intent in enumerate(allowed):
        edge = float(intent["expected_edge_after_cost"])
        partial_factor = float(intent["partial_fill_ratio"])
        if variant_id == "PASSIVE_LIMIT_WITH_NO_FILL" and index % 3 == 0:
            continue
        if variant_id == "CROSS_ONLY_IF_EDGE_SURVIVES_WORST_CASE":
            edge -= 0.02
        result += edge * partial_factor
    return result


def _comparison(cost_adjusted_result: float) -> dict[str, Any]:
    return {
        "comparison_basis": "cost_adjusted_shadow_policy_result",
        "candidate_positive_after_cost": cost_adjusted_result > 0.0,
        "promotion_claimed": False,
    }


def _too_lenient_control(intents: list[dict[str, Any]]) -> dict[str, Any]:
    buy_intents = [item for item in intents if item["side"] == "BUY"]
    return {
        "variant_id": TOO_LENIENT_CONTROL,
        "assumption_classification": "TOO_LENIENT",
        "allowed_intent_count": len(buy_intents),
        "blocked_intent_count": len(intents) - len(buy_intents),
        "filled_count": len(buy_intents),
        "no_fill_count": 0,
        "partial_fill_count": 0,
        "cost_adjusted_result": round(
            sum(max(float(item["expected_edge_before_cost"]), 0.0) for item in buy_intents),
            6,
        ),
        "baseline_comparison": {
            "comparison_basis": "rejected_control",
            "promotion_claimed": False,
        },
        "placebo_comparison": {
            "comparison_basis": "rejected_control",
            "promotion_claimed": False,
        },
        "can_promote_readiness": False,
        "rejection_reason": "Control ignores conservative no-fill, partial-fill, and price-discipline blockers.",
    }
