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


def build_sequence38_autonomy_milestones(
    *,
    expanded_shadow_readiness: dict[str, Any],
) -> dict[str, Any]:
    payload = build_autonomy_milestones()
    milestones = [dict(item) for item in payload["milestones"]]
    ready = expanded_shadow_readiness["ready_for_expanded_shadow_replay"]
    readiness_status = expanded_shadow_readiness["readiness_status"]
    for milestone in milestones:
        if milestone["milestone_id"] == "evidence_acquisition_repeatable":
            milestone["status"] = "PARTIAL"
            milestone["current_blockers"] = expanded_shadow_readiness["blockers"]
            milestone["evidence_source"] = "sequence38_evidence_expansion"
            milestone["required_next_action"] = (
                "collect real-cached read-only UP/DOWN CLOB, spot, and resolution windows"
            )
            milestone["phase_likely_responsible"] = "Phase 39"
        if milestone["milestone_id"] == "replay_inputs_sufficient":
            milestone["status"] = "PARTIAL" if not ready else "MET"
            milestone["current_blockers"] = [] if ready else [readiness_status]
            milestone["evidence_source"] = "sequence38_expanded_dataset"
            milestone["required_next_action"] = (
                "raise primary replay-ready evidence to the configured threshold"
            )
            milestone["phase_likely_responsible"] = "Phase 39"
        if milestone["milestone_id"] == "shadow_proving_threshold_met":
            milestone["status"] = "PARTIAL" if ready else "BLOCKED"
            milestone["current_blockers"] = [] if ready else [readiness_status]
            milestone["evidence_source"] = "sequence38_expanded_shadow_replay_readiness"
            milestone["required_next_action"] = (
                "run expanded offline shadow replay only after the evidence gate passes"
            )
            milestone["phase_likely_responsible"] = "Phase 39"
        if milestone["milestone_id"] == "bounded_shadow_rehearsal_ready":
            milestone["status"] = "PARTIAL" if ready else "BLOCKED"
            milestone["current_blockers"] = [] if ready else ["EXPANDED_SHADOW_REPLAY_NOT_READY"]
            milestone["evidence_source"] = "sequence38_expanded_shadow_replay_readiness"
            milestone["required_next_action"] = (
                "keep canary and live blocked until expanded shadow replay is earned"
            )
            milestone["phase_likely_responsible"] = "Future phase"
    next_required = next(item for item in milestones if item["status"] not in {"MET"})
    payload.update(
        {
            "sequence": "38",
            "ledger_status": "FINITE_AUTONOMY_PATH_UPDATED_WITH_REPLAY_EVIDENCE_EXPANSION",
            "milestones": milestones,
            "next_required_milestone": next_required,
            "expanded_shadow_replay_readiness_status": readiness_status,
            "phase38_movement": expanded_shadow_readiness["autonomy_milestones"],
            "live_orders_allowed": False,
            "live_promotion_status": "LIVE_BLOCKED",
        }
    )
    return payload


def build_sequence39_autonomy_milestones(
    *,
    real_cached_readiness: dict[str, Any],
) -> dict[str, Any]:
    payload = build_autonomy_milestones()
    milestones = [dict(item) for item in payload["milestones"]]
    ready = real_cached_readiness["ready_for_expanded_shadow_replay"]
    readiness_status = real_cached_readiness["readiness_status"]
    for milestone in milestones:
        if milestone["milestone_id"] == "evidence_acquisition_repeatable":
            milestone["status"] = "PARTIAL" if not ready else "MET"
            milestone["current_blockers"] = real_cached_readiness["blockers"]
            milestone["evidence_source"] = "sequence39_real_cached_import"
            milestone["required_next_action"] = (
                "collect enough local/manual real-cached rows to clear the primary threshold"
            )
            milestone["phase_likely_responsible"] = "Phase 40"
        if milestone["milestone_id"] == "replay_inputs_sufficient":
            milestone["status"] = "PARTIAL" if not ready else "MET"
            milestone["current_blockers"] = [] if ready else [readiness_status]
            milestone["evidence_source"] = "sequence39_threshold_progress"
            milestone["required_next_action"] = (
                "run expanded shadow replay only after real-cached readiness passes"
            )
            milestone["phase_likely_responsible"] = "Phase 40"
        if milestone["milestone_id"] == "shadow_proving_threshold_met":
            milestone["status"] = "PARTIAL" if ready else "BLOCKED"
            milestone["current_blockers"] = [] if ready else [readiness_status]
            milestone["evidence_source"] = "sequence39_real_cached_readiness"
            milestone["required_next_action"] = (
                "keep shadow replay blocked until the real-cached gate passes"
            )
            milestone["phase_likely_responsible"] = "Phase 40"
        if milestone["milestone_id"] == "bounded_shadow_rehearsal_ready":
            milestone["status"] = "PARTIAL" if ready else "BLOCKED"
            milestone["current_blockers"] = [] if ready else ["EXPANDED_SHADOW_REPLAY_NOT_READY"]
            milestone["evidence_source"] = "sequence39_real_cached_readiness"
            milestone["required_next_action"] = (
                "keep canary and live blocked until expanded shadow replay is earned"
            )
            milestone["phase_likely_responsible"] = "Future phase"
    next_required = next(item for item in milestones if item["status"] not in {"MET"})
    payload.update(
        {
            "sequence": "39",
            "ledger_status": "FINITE_AUTONOMY_PATH_UPDATED_WITH_REAL_CACHED_EVIDENCE",
            "milestones": milestones,
            "next_required_milestone": next_required,
            "real_cached_replay_readiness_status": readiness_status,
            "phase39_movement": real_cached_readiness["autonomy_milestones"],
            "live_orders_allowed": False,
            "live_promotion_status": "LIVE_BLOCKED",
        }
    )
    return payload


def build_sequence41_autonomy_milestones(
    *,
    expanded_shadow_readiness: dict[str, Any],
) -> dict[str, Any]:
    payload = build_autonomy_milestones()
    milestones = [dict(item) for item in payload["milestones"]]
    ready = expanded_shadow_readiness["ready_for_expanded_shadow_replay"]
    readiness_status = expanded_shadow_readiness["readiness_status"]
    for milestone in milestones:
        if milestone["milestone_id"] == "evidence_acquisition_repeatable":
            milestone["status"] = "MET" if ready else "PARTIAL"
            milestone["current_blockers"] = expanded_shadow_readiness["blockers"]
            milestone["evidence_source"] = "sequence41_window_acquisition"
            milestone["required_next_action"] = (
                "import enough valid local real-cached windows to clear source coverage"
            )
            milestone["phase_likely_responsible"] = "Phase 41"
        if milestone["milestone_id"] == "replay_inputs_sufficient":
            milestone["status"] = "MET" if ready else "PARTIAL"
            milestone["current_blockers"] = [] if ready else [readiness_status]
            milestone["evidence_source"] = "sequence41_threshold_progress"
            milestone["required_next_action"] = (
                "keep collecting replay-ready rows until the primary threshold is met"
            )
            milestone["phase_likely_responsible"] = "Phase 41"
        if milestone["milestone_id"] == "shadow_proving_threshold_met":
            milestone["status"] = "PARTIAL" if ready else "BLOCKED"
            milestone["current_blockers"] = [] if ready else [readiness_status]
            milestone["evidence_source"] = "sequence41_expanded_shadow_replay_readiness"
            milestone["required_next_action"] = (
                "run expanded offline shadow replay only after the hard gate passes"
            )
            milestone["phase_likely_responsible"] = "Phase 41"
        if milestone["milestone_id"] == "bounded_shadow_rehearsal_ready":
            milestone["status"] = "PARTIAL" if ready else "BLOCKED"
            milestone["current_blockers"] = [] if ready else ["EXPANDED_SHADOW_REPLAY_NOT_READY"]
            milestone["evidence_source"] = "sequence41_expanded_shadow_replay_readiness"
            milestone["required_next_action"] = (
                "keep canary and live blocked after expanded shadow replay readiness"
            )
            milestone["phase_likely_responsible"] = "Future phase"
    next_required = next(item for item in milestones if item["status"] not in {"MET"})
    payload.update(
        {
            "sequence": "41",
            "ledger_status": "FINITE_AUTONOMY_PATH_UPDATED_WITH_REAL_CACHED_WINDOW_ACQUISITION",
            "milestones": milestones,
            "next_required_milestone": next_required,
            "expanded_shadow_replay_readiness_status": readiness_status,
            "phase41_movement": expanded_shadow_readiness["autonomy_milestones"],
            "live_orders_allowed": False,
            "live_promotion_status": "LIVE_BLOCKED",
        }
    )
    return payload


def build_sequence43_autonomy_milestones(
    *,
    bounded_shadow_readiness: dict[str, Any],
) -> dict[str, Any]:
    payload = build_autonomy_milestones()
    milestones = [dict(item) for item in payload["milestones"]]
    ready = bounded_shadow_readiness["ready_for_bounded_shadow_rehearsal"]
    readiness_status = bounded_shadow_readiness["readiness_status"]
    for milestone in milestones:
        if milestone["milestone_id"] == "evidence_acquisition_repeatable":
            milestone["status"] = "MET"
            milestone["current_blockers"] = []
            milestone["evidence_source"] = "sequence42_real_cached_window_import"
            milestone["required_next_action"] = (
                "preserve real-cached evidence and continue with offline-only gates"
            )
            milestone["phase_likely_responsible"] = "Phase 42"
        if milestone["milestone_id"] == "replay_inputs_sufficient":
            milestone["status"] = "MET"
            milestone["current_blockers"] = []
            milestone["evidence_source"] = "sequence43_policy_replay_eval"
            milestone["required_next_action"] = (
                "use conservative policy replay output for bounded shadow readiness only"
            )
            milestone["phase_likely_responsible"] = "Phase 43"
        if milestone["milestone_id"] == "shadow_proving_threshold_met":
            milestone["status"] = "PARTIAL"
            milestone["current_blockers"] = [] if ready else [readiness_status]
            milestone["evidence_source"] = "sequence43_fill_realism_shadow_policy"
            milestone["required_next_action"] = (
                "continue offline shadow proof only if fill realism survives"
            )
            milestone["phase_likely_responsible"] = "Phase 43"
        if milestone["milestone_id"] == "bounded_shadow_rehearsal_ready":
            milestone["status"] = "MET" if ready else "BLOCKED"
            milestone["current_blockers"] = [] if ready else bounded_shadow_readiness["blockers"]
            milestone["evidence_source"] = "sequence43_bounded_shadow_rehearsal_readiness"
            milestone["required_next_action"] = (
                "rehearse bounded shadow only if ready; otherwise do nothing"
            )
            milestone["phase_likely_responsible"] = "Phase 43"
        if milestone["milestone_id"] in {
            "canary_preconditions_met",
            "manual_arming_protocol_present",
            "first_tiny_canary_allowed",
            "real_canary_reconciliation_passed",
            "expansion_blocked_until_repeated_proof",
        }:
            milestone["status"] = "BLOCKED"
            milestone["current_blockers"] = ["LIVE_AND_CANARY_STILL_DISABLED"]
            milestone["required_next_action"] = "do not enable live or canary in Phase 43"
            milestone["phase_likely_responsible"] = "Future phase"
    next_required = next(item for item in milestones if item["status"] not in {"MET"})
    payload.update(
        {
            "sequence": "43",
            "ledger_status": "FINITE_AUTONOMY_PATH_UPDATED_WITH_FILL_REALISM_SHADOW_POLICY",
            "milestones": milestones,
            "next_required_milestone": next_required,
            "bounded_shadow_rehearsal_readiness_status": readiness_status,
            "phase43_movement": bounded_shadow_readiness["autonomy_milestones"],
            "live_orders_allowed": False,
            "live_promotion_status": "LIVE_BLOCKED",
        }
    )
    return payload


def build_sequence44_autonomy_milestones(
    *,
    candidate_decision: dict[str, Any],
) -> dict[str, Any]:
    payload = build_autonomy_milestones()
    milestones = [dict(item) for item in payload["milestones"]]
    ready = candidate_decision["ready_for_bounded_shadow_rehearsal"]
    decision_status = candidate_decision["decision_status"]
    for milestone in milestones:
        if milestone["milestone_id"] == "evidence_acquisition_repeatable":
            milestone["status"] = "MET"
            milestone["current_blockers"] = []
            milestone["evidence_source"] = "sequence42_real_cached_window_import"
            milestone["required_next_action"] = (
                "preserve complete real-cached evidence acquisition record"
            )
            milestone["phase_likely_responsible"] = "Phase 42"
        if milestone["milestone_id"] == "replay_inputs_sufficient":
            milestone["status"] = "MET"
            milestone["current_blockers"] = []
            milestone["evidence_source"] = "sequence43_policy_replay_eval"
            milestone["required_next_action"] = (
                "use allowed-intent diagnostics without adding new evidence"
            )
            milestone["phase_likely_responsible"] = "Phase 44"
        if milestone["milestone_id"] == "shadow_proving_threshold_met":
            milestone["status"] = "MET"
            milestone["current_blockers"] = []
            milestone["evidence_source"] = "sequence43_bounded_shadow_rehearsal_readiness"
            milestone["required_next_action"] = (
                "make candidate decision before bounded shadow rehearsal"
            )
            milestone["phase_likely_responsible"] = "Phase 44"
        if milestone["milestone_id"] == "bounded_shadow_rehearsal_ready":
            milestone["status"] = "MET" if ready else "BLOCKED"
            milestone["current_blockers"] = [] if ready else candidate_decision["blockers"]
            milestone["evidence_source"] = "sequence44_candidate_decision"
            milestone["required_next_action"] = (
                "start bounded shadow rehearsal"
                if ready
                else "do not rehearse until the candidate decision gate passes"
            )
            milestone["phase_likely_responsible"] = "Phase 44"
        if milestone["milestone_id"] in {
            "canary_preconditions_met",
            "manual_arming_protocol_present",
            "first_tiny_canary_allowed",
            "real_canary_reconciliation_passed",
            "expansion_blocked_until_repeated_proof",
        }:
            milestone["status"] = "BLOCKED"
            milestone["current_blockers"] = ["LIVE_AND_CANARY_STILL_DISABLED"]
            milestone["required_next_action"] = "do not enable live or canary in Phase 44"
            milestone["phase_likely_responsible"] = "Future phase"
    next_required = next(item for item in milestones if item["status"] not in {"MET"})
    payload.update(
        {
            "sequence": "44",
            "ledger_status": "FINITE_AUTONOMY_PATH_UPDATED_WITH_ALLOWED_INTENT_DECISION",
            "milestones": milestones,
            "next_required_milestone": next_required,
            "candidate_decision_status": decision_status,
            "phase44_movement": candidate_decision["autonomy_milestones"],
            "live_orders_allowed": False,
            "live_promotion_status": "LIVE_BLOCKED",
        }
    )
    return payload


def build_sequence45_autonomy_milestones(
    *,
    candidate_decision: dict[str, Any],
) -> dict[str, Any]:
    payload = build_autonomy_milestones()
    milestones = [dict(item) for item in payload["milestones"]]
    allowed_threshold_met = (
        int(candidate_decision["allowed_primary_intent_count"]) >= 5
        and int(candidate_decision["allowed_real_cached_intent_count"]) >= 3
    )
    ready = candidate_decision["ready_for_bounded_shadow_rehearsal"]
    decision_status = candidate_decision["decision_status"]
    allowed_milestone = _milestone(
        6,
        "allowed_intent_threshold_met",
        "Allowed-intent threshold met",
        "MET" if allowed_threshold_met else "BLOCKED",
        [] if allowed_threshold_met else candidate_decision["blockers"],
        "sequence45_allowed_intent_decision",
        (
            "continue bounded offline shadow rehearsal checks"
            if allowed_threshold_met
            else "collect enough allowed primary and real-cached intents before rehearsal"
        ),
        "Phase 45",
    )
    milestones.insert(6, allowed_milestone)
    for index, milestone in enumerate(milestones, start=1):
        milestone["milestone_index"] = index
        if milestone["milestone_id"] == "evidence_acquisition_repeatable":
            milestone["status"] = "MET"
            milestone["current_blockers"] = []
            milestone["evidence_source"] = "sequence42_real_cached_window_import"
            milestone["required_next_action"] = (
                "preserve real-cached evidence acquisition and collect allowed-intent-targeted windows"
            )
            milestone["phase_likely_responsible"] = "Phase 45"
        if milestone["milestone_id"] == "replay_inputs_sufficient":
            milestone["status"] = "MET"
            milestone["current_blockers"] = []
            milestone["evidence_source"] = "sequence43_policy_replay_eval"
            milestone["required_next_action"] = (
                "rerun allowed-intent policy gates after each import"
            )
            milestone["phase_likely_responsible"] = "Phase 45"
        if milestone["milestone_id"] == "shadow_proving_threshold_met":
            milestone["status"] = "MET"
            milestone["current_blockers"] = []
            milestone["evidence_source"] = "sequence44_candidate_decision"
            milestone["required_next_action"] = (
                "keep anti-overfit and baseline/placebo gates active"
            )
            milestone["phase_likely_responsible"] = "Phase 45"
        if milestone["milestone_id"] == "bounded_shadow_rehearsal_ready":
            milestone["status"] = "MET" if ready else "BLOCKED"
            milestone["current_blockers"] = [] if ready else candidate_decision["blockers"]
            milestone["evidence_source"] = "sequence45_candidate_decision"
            milestone["required_next_action"] = (
                "start bounded offline shadow rehearsal"
                if ready
                else "do not rehearse until the Phase 45 candidate decision gate passes"
            )
            milestone["phase_likely_responsible"] = "Phase 45"
        if milestone["milestone_id"] in {
            "canary_preconditions_met",
            "manual_arming_protocol_present",
            "first_tiny_canary_allowed",
            "real_canary_reconciliation_passed",
            "expansion_blocked_until_repeated_proof",
        }:
            milestone["status"] = "BLOCKED"
            milestone["current_blockers"] = ["LIVE_AND_CANARY_STILL_DISABLED"]
            milestone["required_next_action"] = "do not enable live or canary in Phase 45"
            milestone["phase_likely_responsible"] = "Future phase"
    next_required = next(item for item in milestones if item["status"] not in {"MET"})
    payload.update(
        {
            "sequence": "45",
            "ledger_status": "FINITE_AUTONOMY_PATH_UPDATED_WITH_ALLOWED_INTENT_EXPANSION",
            "milestone_count": len(milestones),
            "milestones": milestones,
            "next_required_milestone": next_required,
            "candidate_decision_status": decision_status,
            "phase45_movement": candidate_decision.get(
                "autonomy_milestones",
                {
                    "allowed_intent_threshold": "met"
                    if allowed_threshold_met
                    else "blocked",
                    "bounded_shadow_rehearsal": "ready" if ready else "blocked",
                    "canary": "blocked",
                    "live": "blocked",
                },
            ),
            "allowed_intent_threshold_met": allowed_threshold_met,
            "bounded_shadow_rehearsal_ready": ready,
            "canary_ready": False,
            "live_orders_allowed": False,
            "live_promotion_status": "LIVE_BLOCKED",
        }
    )
    return payload


def build_sequence47_autonomy_milestones(
    *,
    candidate_readiness: dict[str, Any],
) -> dict[str, Any]:
    payload = build_autonomy_milestones()
    milestones = [dict(item) for item in payload["milestones"]]
    ready_for_data = (
        candidate_readiness["candidate_readiness_status"]
        == "CANDIDATE_PACK_READY_FOR_DATA_ACQUISITION"
    )
    candidate_pack_milestone = _milestone(
        7,
        "refresh_lag_candidate_pack_ready",
        "Refresh-lag candidate pack ready",
        "MET" if ready_for_data else "BLOCKED",
        [] if ready_for_data else candidate_readiness["blockers"],
        "sequence47_pm_lp_refresh_lag_candidate_pack",
        (
            "acquire public read-only CLOB, trade, quote-refresh, spot-trigger, and resolution data"
            if ready_for_data
            else "repair the candidate pack before any data acquisition"
        ),
        "Phase 47",
    )
    milestones.insert(6, candidate_pack_milestone)
    for index, milestone in enumerate(milestones, start=1):
        milestone["milestone_index"] = index
        if milestone["milestone_id"] == "evidence_acquisition_repeatable":
            milestone["status"] = "PARTIAL"
            milestone["current_blockers"] = candidate_readiness["blockers"]
            milestone["evidence_source"] = "sequence47_source_policy"
            milestone["required_next_action"] = (
                "collect only public read-only refresh-lag source artifacts"
            )
            milestone["phase_likely_responsible"] = "Phase 48"
        if milestone["milestone_id"] == "replay_inputs_sufficient":
            milestone["status"] = "PARTIAL" if ready_for_data else "BLOCKED"
            milestone["current_blockers"] = ["PUBLIC_SOURCES_REQUIRED_NOT_ACQUIRED"]
            milestone["evidence_source"] = "sequence47_replay_schema"
            milestone["required_next_action"] = (
                "validate real cached refresh-lag windows before replay evaluation"
            )
            milestone["phase_likely_responsible"] = "Phase 48"
        if milestone["milestone_id"] == "shadow_proving_threshold_met":
            milestone["status"] = "BLOCKED"
            milestone["current_blockers"] = ["NO_REFRESH_LAG_REPLAY_EVIDENCE"]
            milestone["evidence_source"] = "sequence47_candidate_readiness"
            milestone["required_next_action"] = "do not run shadow proving in Phase 47"
            milestone["phase_likely_responsible"] = "Future phase"
        if milestone["milestone_id"] == "bounded_shadow_rehearsal_ready":
            milestone["status"] = "BLOCKED"
            milestone["current_blockers"] = ["CANDIDATE_PACK_ONLY"]
            milestone["evidence_source"] = "sequence47_candidate_pack"
            milestone["required_next_action"] = (
                "block rehearsal until public data, baselines, placebos, and fill realism pass"
            )
            milestone["phase_likely_responsible"] = "Future phase"
        if milestone["milestone_id"] in {
            "canary_preconditions_met",
            "manual_arming_protocol_present",
            "first_tiny_canary_allowed",
            "real_canary_reconciliation_passed",
            "expansion_blocked_until_repeated_proof",
        }:
            milestone["status"] = "BLOCKED"
            milestone["current_blockers"] = ["LIVE_AND_CANARY_STILL_DISABLED"]
            milestone["required_next_action"] = "do not enable live or canary in Phase 47"
            milestone["phase_likely_responsible"] = "Future phase"
    next_required = next(item for item in milestones if item["status"] not in {"MET"})
    payload.update(
        {
            "sequence": "47",
            "ledger_status": "FINITE_AUTONOMY_PATH_UPDATED_WITH_REFRESH_LAG_CANDIDATE_PACK",
            "milestone_count": len(milestones),
            "milestones": milestones,
            "next_required_milestone": next_required,
            "prior_candidate_status": "DEPRIORITIZE_CANDIDATE",
            "selected_candidate_id": "pm_lp_refresh_lag_arbitrage",
            "candidate_readiness_status": candidate_readiness["candidate_readiness_status"],
            "phase47_movement": candidate_readiness.get(
                "autonomy_milestones",
                {
                    "candidate_pack": "ready_for_data_acquisition"
                    if ready_for_data
                    else "blocked",
                    "public_source_acquisition": "blocked",
                    "bounded_shadow_rehearsal": "blocked",
                    "canary": "blocked",
                    "live": "blocked",
                },
            ),
            "live_orders_allowed": False,
            "live_promotion_status": "LIVE_BLOCKED",
        }
    )
    return payload


def build_sequence50_autonomy_milestones(
    *,
    weather_readiness: dict[str, Any],
) -> dict[str, Any]:
    payload = build_autonomy_milestones()
    milestones = [dict(item) for item in payload["milestones"]]
    weather_milestone = _milestone(
        7,
        "weather_market_data_acquisition",
        "Weather market data acquisition",
        "PARTIAL"
        if weather_readiness["readiness_status"] == "PAPER_PROFIT_DIAGNOSTIC_ONLY"
        else "BLOCKED",
        weather_readiness["blockers"],
        "sequence50_weather_data_readiness",
        "capture real public weather, market, orderbook, and resolution rows",
        "Phase 50",
    )
    milestones.insert(6, weather_milestone)
    for index, milestone in enumerate(milestones, start=1):
        milestone["milestone_index"] = index
        if milestone["milestone_id"] == "evidence_acquisition_repeatable":
            milestone["status"] = "PARTIAL"
            milestone["current_blockers"] = weather_readiness["blockers"]
            milestone["evidence_source"] = "sequence50_weather_capture_plan"
            milestone["required_next_action"] = (
                "collect source-policy-approved public weather and market snapshots"
            )
            milestone["phase_likely_responsible"] = "Phase 50+"
        if milestone["milestone_id"] == "replay_inputs_sufficient":
            milestone["status"] = "PARTIAL"
            milestone["current_blockers"] = ["FIXTURE_ONLY_NOT_PROOF", "REAL_LABELS_REQUIRED"]
            milestone["evidence_source"] = "sequence50_weather_replay_schema"
            milestone["required_next_action"] = "replace fixture rows with real public proof rows"
            milestone["phase_likely_responsible"] = "Phase 50+"
        if milestone["milestone_id"] == "shadow_proving_threshold_met":
            milestone["status"] = "BLOCKED"
            milestone["current_blockers"] = ["NO_PAPER_PROFIT_CANDIDATE"]
            milestone["evidence_source"] = "sequence50_profit_claim_guard"
            milestone["required_next_action"] = "do not run bounded shadow until proof qualifies"
            milestone["phase_likely_responsible"] = "Future phase"
        if milestone["milestone_id"] == "bounded_shadow_rehearsal_ready":
            milestone["status"] = "BLOCKED"
            milestone["current_blockers"] = ["PAPER_PROFIT_DIAGNOSTIC_ONLY"]
            milestone["evidence_source"] = "sequence50_weather_data_readiness"
            milestone["required_next_action"] = "keep rehearsal blocked until real evidence passes"
            milestone["phase_likely_responsible"] = "Future phase"
        if milestone["milestone_id"] in {
            "canary_preconditions_met",
            "manual_arming_protocol_present",
            "first_tiny_canary_allowed",
            "real_canary_reconciliation_passed",
            "expansion_blocked_until_repeated_proof",
        }:
            milestone["status"] = "BLOCKED"
            milestone["current_blockers"] = ["LIVE_AND_CANARY_STILL_DISABLED"]
            milestone["required_next_action"] = "do not enable live or canary in Phase 50"
            milestone["phase_likely_responsible"] = "Future phase"
    next_required = next(item for item in milestones if item["status"] != "MET")
    payload.update(
        {
            "sequence": "50",
            "ledger_status": "FINITE_AUTONOMY_PATH_UPDATED_WITH_WEATHER_DATA_PROVING",
            "milestone_count": len(milestones),
            "milestones": milestones,
            "next_required_milestone": next_required,
            "selected_candidate_id": "pm_weather_forecast_market_mismatch",
            "weather_data_readiness_status": weather_readiness["readiness_status"],
            "phase50_movement": weather_readiness["autonomy_milestones"],
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
