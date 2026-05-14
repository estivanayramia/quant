from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from quant_os.proving.shadow_proving_spec import build_shadow_proving_spec


def evaluate_shadow_proving(*, shadow_execution_reports: list[dict[str, Any]]) -> dict[str, Any]:
    spec = build_shadow_proving_spec()
    aggregate = _aggregate(shadow_execution_reports)
    blockers = _blockers(spec=spec, aggregate=aggregate, reports=shadow_execution_reports)
    status = _status_from_blockers(blockers)
    return {
        "shadow_proving_status": status,
        "ready_for_tiny_canary_consideration": (
            status == "READY_FOR_TINY_CANARY_CONSIDERATION"
        ),
        "aggregate_metrics": aggregate,
        "blockers": blockers,
        "window_results": [
            _window_summary(index, report)
            for index, report in enumerate(shadow_execution_reports)
        ],
        "thresholds": spec["thresholds"],
        "observed_facts": [
            "Shadow proving aggregates offline shadow execution evidence only.",
            "Current sample has one replay window and one blocked shadow intent.",
        ],
        "inferred_patterns": [
            "The current shadow substrate is too thin and too risk-blocked for canary consideration.",
        ],
        "unknowns": [
            "Whether additional replay windows would produce consistent non-blocked decisions.",
            "Whether conservative fill assumptions can ever support positive expectancy.",
        ],
    }


def _aggregate(reports: list[dict[str, Any]]) -> dict[str, Any]:
    total_intents = sum(int(report["metrics"]["intent_count"]) for report in reports)
    total_blocked = sum(int(report["metrics"]["blocked_trade_count"]) for report in reports)
    total_filled = sum(int(report["metrics"]["filled_count"]) for report in reports)
    total_no_fill = sum(int(report["metrics"]["no_fill_count"]) for report in reports)
    window_count = len(reports)
    risk_blocked_windows = sum(
        1 for report in reports if "RISK_BLOCKS_SHADOW_AUTONOMY" in report["blockers"]
    )
    return {
        "window_count": window_count,
        "total_intent_count": total_intents,
        "blocked_trade_count": total_blocked,
        "blocked_trade_ratio": _ratio(total_blocked, total_intents),
        "filled_count": total_filled,
        "no_fill_count": total_no_fill,
        "fill_rate": _ratio(total_filled, total_intents),
        "no_fill_rate": _ratio(total_no_fill, total_intents),
        "risk_blocked_window_count": risk_blocked_windows,
        "intent_consistency": "too_thin_to_measure",
        "blocked_decision_stability": "stable_but_blocked",
        "fill_sensitivity": "too_thin_no_fills",
        "expectancy_fragility": "unearned_no_edge",
        "risk_envelope_adherence": "blocked_by_fail_closed_risk",
        "lane_specific_concentration_risk": "single_lane_single_window",
        "degradation_under_harsher_fill_assumptions": "not_estimated_no_fills",
    }


def _blockers(
    *,
    spec: dict[str, Any],
    aggregate: dict[str, Any],
    reports: list[dict[str, Any]],
) -> list[str]:
    thresholds = spec["thresholds"]
    blockers = []
    if aggregate["window_count"] < thresholds["minimum_shadow_windows"]:
        blockers.append("SHADOW_WINDOW_SAMPLE_TOO_THIN")
    if aggregate["total_intent_count"] < thresholds["minimum_total_intents"]:
        blockers.append("SHADOW_SAMPLE_TOO_THIN")
    if aggregate["blocked_trade_ratio"] == "1":
        blockers.append("ALL_INTENTS_BLOCKED")
    if _decimal(aggregate["fill_rate"]) < _decimal(thresholds["minimum_fill_rate"]):
        blockers.append("FILL_RATE_TOO_LOW")
    if aggregate["risk_blocked_window_count"] > 0:
        blockers.append("RISK_BLOCKS_CANARY_CONSIDERATION")
    if any("WEAK_SIGNAL_BLOCKS_SHADOW_AUTONOMY" in report["blockers"] for report in reports):
        blockers.append("WEAK_EVIDENCE_BLOCKS_PROMOTION")
    if any("REPLAY_DESIGN_PARTIAL" in report["blockers"] for report in reports):
        blockers.append("UNRESOLVED_REALISM_DISQUALIFIER")
    if blockers:
        blockers.append("CANARY_PRECONDITIONS_NOT_MET")
    return _dedupe(blockers)


def _status_from_blockers(blockers: list[str]) -> str:
    if "SHADOW_SAMPLE_TOO_THIN" in blockers or "SHADOW_WINDOW_SAMPLE_TOO_THIN" in blockers:
        return "SHADOW_PROVING_TOO_THIN"
    if "RISK_BLOCKS_CANARY_CONSIDERATION" in blockers:
        return "RISK_BLOCKS_CANARY_CONSIDERATION"
    if "WEAK_EVIDENCE_BLOCKS_PROMOTION" in blockers:
        return "CANARY_PRECONDITIONS_NOT_MET"
    if blockers:
        return "SHADOW_PROVING_UNSTABLE"
    return "READY_FOR_TINY_CANARY_CONSIDERATION"


def _window_summary(index: int, report: dict[str, Any]) -> dict[str, Any]:
    return {
        "window_index": index,
        "shadow_execution_status": report["shadow_execution_status"],
        "intent_count": report["metrics"]["intent_count"],
        "blocked_trade_count": report["metrics"]["blocked_trade_count"],
        "fill_rate": report["metrics"]["fill_rate"],
        "no_fill_rate": report["metrics"]["no_fill_rate"],
        "blockers": report["blockers"],
    }


def _ratio(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "0"
    value = Decimal(numerator) / Decimal(denominator)
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered or "0"


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


def _dedupe(items: list[str]) -> list[str]:
    seen = set()
    deduped = []
    for item in items:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped
