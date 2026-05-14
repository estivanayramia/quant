from __future__ import annotations

from typing import Any

from quant_os.proving.shadow_proving_spec import SHADOW_PROVING_SAFETY


def evaluate_shadow_rehearsal_readiness(*, unblockability: dict[str, Any]) -> dict[str, Any]:
    blockers = _blockers(unblockability)
    status = _status(blockers)
    return {
        "schema_version": "shadow_rehearsal_readiness_v1",
        "sequence": "33",
        "shadow_rehearsal_status": status,
        "ready_for_bounded_shadow_rehearsal": (
            status == "READY_FOR_BOUNDED_SHADOW_REHEARSAL"
        ),
        "ready_for_live_trading": False,
        "unblockability_status": unblockability["unblockability_status"],
        "blockers": blockers,
        "observed_facts": [
            "Shadow rehearsal readiness is offline-only.",
            "Synthetic stress windows are not treated as real edge evidence.",
        ],
        "required_before_rehearsal": [
            "More real or fixture-quality replay windows.",
            "Resolved replay realism blockers.",
            "Stable non-blocked shadow decisions under conservative assumptions.",
            "No hidden live authority.",
        ],
        **SHADOW_PROVING_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _blockers(unblockability: dict[str, Any]) -> list[str]:
    blockers = []
    if unblockability["real_or_fixture_effective_window_count"] < 5:
        blockers.append("shadow_evidence_too_thin")
    if "BLOCKED_BY_REPLAY_REALISM" in unblockability["secondary_blockers"]:
        blockers.append("unresolved_replay_realism")
    if "BLOCKED_BY_SIGNAL_WEAKNESS" in unblockability["secondary_blockers"]:
        blockers.append("weak_signal_evidence")
    if "BLOCKED_BY_RISK_POLICY" in unblockability["secondary_blockers"]:
        blockers.append("risk_policy_blocks_rehearsal")
    if unblockability["hidden_live_authority_detected"]:
        blockers.append("hidden_live_authority_detected")
    return blockers


def _status(blockers: list[str]) -> str:
    if "hidden_live_authority_detected" in blockers:
        return "SHADOW_REHEARSAL_NOT_READY"
    if "shadow_evidence_too_thin" in blockers:
        return "SHADOW_EVIDENCE_TOO_THIN"
    if "unresolved_replay_realism" in blockers or "weak_signal_evidence" in blockers:
        return "SHADOW_BLOCKERS_NOT_UNDERSTOOD"
    if blockers:
        return "SHADOW_REHEARSAL_NOT_READY"
    return "READY_FOR_BOUNDED_SHADOW_REHEARSAL"
