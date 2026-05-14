from __future__ import annotations

from typing import Any

from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY


def build_autonomy_milestones() -> dict[str, Any]:
    milestones = [
        _milestone(
            1,
            "research_intake_autonomous",
            "Research intake autonomous",
            "MET",
            [],
            "sequence35_intake_run",
            "run governed local/cached intake daily",
            "Phase 35",
        ),
        _milestone(
            2,
            "evidence_acquisition_repeatable",
            "Evidence acquisition repeatable",
            "IN_PROGRESS",
            ["BLOCKED_BY_THIN_EVIDENCE", "SHADOW_EVIDENCE_TOO_THIN"],
            "sequence35_evidence_bridge",
            "add approved read-only data fixtures that feed replay windows",
            "Phase 36",
        ),
        _milestone(
            3,
            "replay_inputs_sufficient",
            "Replay inputs sufficient",
            "BLOCKED",
            ["REPLAY_INPUT_INSUFFICIENT"],
            "sequence28_replay_inputs",
            "expand timestamped replay inputs with real cached windows",
            "Phase 36",
        ),
        _milestone(
            4,
            "shadow_decisions_generated",
            "Shadow decisions generated",
            "MET",
            [],
            "sequence31_shadow_execution",
            "keep shadow policy deterministic and blocked when weak",
            "Phase 31",
        ),
        _milestone(
            5,
            "shadow_proving_threshold_met",
            "Shadow proving threshold met",
            "BLOCKED",
            ["SHADOW_PROVING_TOO_THIN"],
            "sequence32_shadow_proving",
            "accumulate enough replay windows to evaluate stability",
            "Phase 36",
        ),
        _milestone(
            6,
            "bounded_shadow_rehearsal_ready",
            "Bounded shadow rehearsal ready",
            "BLOCKED",
            ["SHADOW_EVIDENCE_TOO_THIN"],
            "sequence33_shadow_rehearsal",
            "prove blockers are understood across windows",
            "Phase 37",
        ),
        _milestone(
            7,
            "dry_run_parity_ready",
            "Dry-run parity ready",
            "BLOCKED",
            ["NO_DRY_RUN_PARITY_PROTOCOL"],
            "canary_preflight_reports",
            "define deterministic dry-run parity protocol",
            "Phase 38",
        ),
        _milestone(
            8,
            "canary_preconditions_met",
            "Canary preconditions met",
            "BLOCKED",
            ["CANARY_PRECONDITIONS_NOT_MET"],
            "sequence32_canary_preconditions",
            "satisfy fail-closed canary checklist with proof",
            "Phase 39",
        ),
        _milestone(
            9,
            "manual_arming_protocol_present",
            "Manual arming protocol present",
            "BLOCKED",
            ["NO_MANUAL_ARMING_PROTOCOL"],
            "canary_arm_token_reports",
            "write operator-supervised arming and disarming procedure",
            "Phase 39",
        ),
        _milestone(
            10,
            "first_tiny_canary_allowed",
            "First tiny canary allowed",
            "BLOCKED",
            ["LIVE_DEFAULT_OFF", "CANARY_NOT_EARNED"],
            "live_canary_reports",
            "allow only after milestones 1-9 are met",
            "Future canary phase",
        ),
        _milestone(
            11,
            "real_canary_reconciliation_passed",
            "Real canary reconciliation passed",
            "BLOCKED",
            ["NO_REAL_CANARY_RECONCILIATION"],
            "live_reconciliation_reports",
            "reconcile every real canary event deterministically",
            "Future canary phase",
        ),
        _milestone(
            12,
            "expansion_blocked_until_repeated_proof",
            "Expansion still blocked until repeated proof",
            "BLOCKED",
            ["REPEATED_PROOF_REQUIRED"],
            "capital_ladder_reports",
            "require repeated canary proof before any expansion",
            "Future expansion phase",
        ),
    ]
    next_required = next(item for item in milestones if item["status"] != "MET")
    return {
        "schema_version": "autonomy_milestones_v1",
        "sequence": "35",
        "ledger_status": "FINITE_AUTONOMY_PATH_EXPLICIT",
        "milestone_count": len(milestones),
        "milestones": milestones,
        "next_required_milestone": next_required,
        "live_orders_allowed": False,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def build_sequence36_autonomy_milestones(*, replay_dataset_readiness: dict[str, Any]) -> dict[str, Any]:
    payload = build_autonomy_milestones()
    milestones = [dict(item) for item in payload["milestones"]]
    readiness_status = replay_dataset_readiness["readiness_status"]
    dataset_has_shape = replay_dataset_readiness["row_count"] > 0
    for milestone in milestones:
        if milestone["milestone_id"] == "evidence_acquisition_repeatable":
            milestone["status"] = "PARTIAL" if dataset_has_shape else "BLOCKED"
            milestone["evidence_source"] = "sequence36_pm_crypto_updown_dataset"
            milestone["required_next_action"] = (
                "resolve dataset quality blockers before candidate replay testing"
            )
            milestone["phase_likely_responsible"] = "Phase 36"
        if milestone["milestone_id"] == "replay_inputs_sufficient":
            milestone["status"] = (
                "MET"
                if readiness_status == "REPLAY_DATASET_READY_FOR_CANDIDATE_TEST"
                else "PARTIAL"
                if dataset_has_shape
                else "BLOCKED"
            )
            milestone["current_blockers"] = replay_dataset_readiness["blockers"]
            milestone["evidence_source"] = "sequence36_replay_dataset_readiness"
            milestone["required_next_action"] = (
                "run Phase 37 candidate replay/backtest only after readiness is sufficient"
            )
            milestone["phase_likely_responsible"] = "Phase 37"
        if milestone["milestone_id"] == "shadow_proving_threshold_met":
            milestone["status"] = "BLOCKED"
            milestone["current_blockers"] = ["CANDIDATE_REPLAY_NOT_TESTED"]
            milestone["required_next_action"] = "test candidate in replay before any shadow proving claim"
            milestone["phase_likely_responsible"] = "Phase 37"
    next_required = next(item for item in milestones if item["status"] not in {"MET"})
    payload.update(
        {
            "sequence": "36",
            "ledger_status": "FINITE_AUTONOMY_PATH_UPDATED_WITH_REPLAY_DATASET",
            "milestones": milestones,
            "next_required_milestone": next_required,
            "replay_dataset_readiness_status": readiness_status,
            "live_orders_allowed": False,
            "live_promotion_status": "LIVE_BLOCKED",
        }
    )
    return payload


def build_sequence37_autonomy_milestones(
    *,
    candidate_replay_readiness: dict[str, Any],
) -> dict[str, Any]:
    payload = build_autonomy_milestones()
    milestones = [dict(item) for item in payload["milestones"]]
    readiness_status = candidate_replay_readiness["readiness_status"]
    for milestone in milestones:
        if milestone["milestone_id"] == "evidence_acquisition_repeatable":
            milestone["status"] = "PARTIAL"
            milestone["current_blockers"] = ["MORE_REPLAY_WINDOWS_REQUIRED"]
            milestone["evidence_source"] = "sequence37_candidate_replay_eval"
            milestone["required_next_action"] = (
                "expand fixture-safe replay data before any stronger autonomy claim"
            )
            milestone["phase_likely_responsible"] = "Phase 38"
        if milestone["milestone_id"] == "replay_inputs_sufficient":
            milestone["status"] = "MET"
            milestone["current_blockers"] = []
            milestone["evidence_source"] = "sequence36_replay_dataset_readiness"
            milestone["required_next_action"] = "keep replay alignment deterministic while expanding data"
            milestone["phase_likely_responsible"] = "Phase 38"
        if milestone["milestone_id"] == "shadow_proving_threshold_met":
            milestone["status"] = "BLOCKED"
            milestone["current_blockers"] = [readiness_status]
            milestone["evidence_source"] = "sequence37_candidate_replay_readiness"
            milestone["required_next_action"] = (
                "do not expand shadow proving until candidate replay readiness is earned"
            )
            milestone["phase_likely_responsible"] = "Phase 38"
        if milestone["milestone_id"] == "bounded_shadow_rehearsal_ready":
            milestone["status"] = (
                "PARTIAL"
                if readiness_status == "READY_FOR_EXPANDED_SHADOW_REPLAY"
                else "BLOCKED"
            )
            milestone["current_blockers"] = (
                []
                if readiness_status == "READY_FOR_EXPANDED_SHADOW_REPLAY"
                else ["EXPANDED_SHADOW_REPLAY_NOT_READY"]
            )
            milestone["evidence_source"] = "sequence37_shadow_bridge"
            milestone["required_next_action"] = (
                "run expanded offline shadow replay only if the candidate earns the gate"
            )
            milestone["phase_likely_responsible"] = "Phase 38"
    next_required = next(item for item in milestones if item["status"] not in {"MET"})
    payload.update(
        {
            "sequence": "37",
            "ledger_status": "FINITE_AUTONOMY_PATH_UPDATED_WITH_CANDIDATE_REPLAY_TEST",
            "milestones": milestones,
            "next_required_milestone": next_required,
            "candidate_replay_readiness_status": readiness_status,
            "phase37_movement": candidate_replay_readiness["autonomy_milestones"],
            "live_orders_allowed": False,
            "live_promotion_status": "LIVE_BLOCKED",
        }
    )
    return payload


def _milestone(
    index: int,
    milestone_id: str,
    title: str,
    status: str,
    blockers: list[str],
    evidence_source: str,
    required_next_action: str,
    phase_likely_responsible: str,
) -> dict[str, Any]:
    return {
        "milestone_index": index,
        "milestone_id": milestone_id,
        "title": title,
        "status": status,
        "current_blockers": blockers,
        "evidence_source": evidence_source,
        "required_next_action": required_next_action,
        "phase_likely_responsible": phase_likely_responsible,
        "required_for_live_orders": True,
    }
