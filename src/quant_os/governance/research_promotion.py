from __future__ import annotations

from typing import Any


def evaluate_research_promotion(evidence: dict[str, Any]) -> dict[str, Any]:
    warnings = list(evidence.get("warnings", []))
    blockers = list(evidence.get("blockers", []))
    status = "SHADOW_CANDIDATE" if not blockers else "RESEARCH_ONLY"
    if warnings:
        status = "RESEARCH_ONLY"
    return {
        "strategy_id": evidence.get("strategy_id"),
        "status": status,
        "dry_run_candidate_allowed": status == "SHADOW_CANDIDATE",
        "live_promotion_status": "TINY_LIVE_BLOCKED",
        "live_ready": False,
        "warnings": warnings,
        "blockers": blockers + ["LIVE_PROMOTION_DISABLED_IN_PHASE_7"],
    }
