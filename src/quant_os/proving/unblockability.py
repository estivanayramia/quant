from __future__ import annotations

from typing import Any

from quant_os.proving.shadow_proving_spec import SHADOW_PROVING_SAFETY


def evaluate_unblockability(
    *,
    shadow_windows: dict[str, Any],
    blocker_attribution: dict[str, Any],
    sensitivity: dict[str, Any],
) -> dict[str, Any]:
    secondary = _secondary_blockers(
        blocker_attribution=blocker_attribution,
        sensitivity=sensitivity,
    )
    status = _status(shadow_windows=shadow_windows, secondary_blockers=secondary)
    hidden_authority = _hidden_authority_detected(shadow_windows, blocker_attribution, sensitivity)
    return {
        "schema_version": "shadow_unblockability_v1",
        "sequence": "33",
        "unblockability_status": status,
        "allowed_statuses": [
            "UNBLOCKABILITY_NOT_TESTABLE",
            "BLOCKED_BY_THIN_EVIDENCE",
            "BLOCKED_BY_SIGNAL_WEAKNESS",
            "BLOCKED_BY_REPLAY_REALISM",
            "BLOCKED_BY_RISK_POLICY",
            "UNBLOCKABLE_ONLY_UNDER_TOO_LENIENT_ASSUMPTIONS",
            "POTENTIALLY_UNBLOCKABLE_WITH_BETTER_DATA",
            "READY_FOR_BOUNDED_SHADOW_REHEARSAL",
        ],
        "ready_for_bounded_shadow_rehearsal": (
            status == "READY_FOR_BOUNDED_SHADOW_REHEARSAL" and not hidden_authority
        ),
        "real_or_fixture_effective_window_count": shadow_windows[
            "proving_effective_window_count"
        ],
        "total_window_count": shadow_windows["total_window_count"],
        "synthetic_stress_not_profitability_evidence": True,
        "secondary_blockers": secondary,
        "hidden_live_authority_detected": hidden_authority,
        "plausible_conservative_path": (
            "Potentially unblockable only with more real or fixture-quality replay windows, "
            "resolved realism blockers, and stable non-blocked decisions. Current evidence "
            "does not justify rehearsal."
        ),
        "diagnosis": (
            "Current blocked state is testable as a diagnostic, but not as proof of "
            "bounded shadow autonomy."
        ),
        **SHADOW_PROVING_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _status(
    *,
    shadow_windows: dict[str, Any],
    secondary_blockers: list[str],
) -> str:
    if shadow_windows["proving_effective_window_count"] < 5:
        return "BLOCKED_BY_THIN_EVIDENCE"
    if "BLOCKED_BY_REPLAY_REALISM" in secondary_blockers:
        return "BLOCKED_BY_REPLAY_REALISM"
    if "BLOCKED_BY_RISK_POLICY" in secondary_blockers:
        return "BLOCKED_BY_RISK_POLICY"
    if "BLOCKED_BY_SIGNAL_WEAKNESS" in secondary_blockers:
        return "BLOCKED_BY_SIGNAL_WEAKNESS"
    if "UNBLOCKABLE_ONLY_UNDER_TOO_LENIENT_ASSUMPTIONS" in secondary_blockers:
        return "UNBLOCKABLE_ONLY_UNDER_TOO_LENIENT_ASSUMPTIONS"
    return "READY_FOR_BOUNDED_SHADOW_REHEARSAL"


def _secondary_blockers(
    *,
    blocker_attribution: dict[str, Any],
    sensitivity: dict[str, Any],
) -> list[str]:
    blockers = []
    groups = blocker_attribution["blocker_groups"]
    if groups["signal_edge_blockers"]:
        blockers.append("BLOCKED_BY_SIGNAL_WEAKNESS")
    if groups["data_replay_blockers"]:
        blockers.append("BLOCKED_BY_REPLAY_REALISM")
    if groups["risk_policy_blockers"]:
        blockers.append("BLOCKED_BY_RISK_POLICY")
    if any(variant["too_lenient_flag"] for variant in sensitivity["variants"]):
        blockers.append("UNBLOCKABLE_ONLY_UNDER_TOO_LENIENT_ASSUMPTIONS")
    return blockers


def _hidden_authority_detected(*payloads: dict[str, Any]) -> bool:
    for payload in payloads:
        if payload.get("live_trading_enabled") is True:
            return True
        if payload.get("execution_authority") != "NONE":
            return True
        if payload.get("prediction_market_execution_authority_added") is True:
            return True
    return False
