from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def _row(
    row_id: str,
    *,
    outcome: str = "UP",
    resolved_outcome: str = "UP",
    ask: float = 0.46,
    bid: float = 0.44,
    liquidity: float = 800.0,
    seconds_to_window_end: float = 45.0,
    spot_return_5s: float | None = 0.0002,
    flags: list[str] | None = None,
    source_quality: str = "fixture_real_shaped",
    no_fill_probability: float | None = None,
    partial_fill_ratio: float | None = None,
    latency_penalty: float | None = None,
) -> dict[str, Any]:
    mid = (bid + ask) / 2.0
    return {
        "clob_snapshot_id": row_id,
        "market_id": f"market_{row_id}",
        "condition_id": f"condition_{row_id}",
        "token_id": f"token_{row_id}",
        "outcome": outcome,
        "event_ts": "2026-05-14T12:00:30Z",
        "window_start_ts": "2026-05-14T12:00:00Z",
        "window_end_ts": "2026-05-14T12:01:00Z",
        "market_bid": bid,
        "market_ask": ask,
        "market_mid": mid,
        "market_spread": ask - bid,
        "market_liquidity": liquidity,
        "market_last_trade_price": mid,
        "seconds_to_window_end": seconds_to_window_end,
        "spot_return_5s": spot_return_5s,
        "label_status": "RESOLVED",
        "resolved_outcome": resolved_outcome,
        "data_quality_flags": flags or ["LOOKAHEAD_PREVENTED"],
        "source_quality": source_quality,
        "source_name": source_quality,
        "primary_evidence_candidate": source_quality != "synthetic_stress",
        **({} if no_fill_probability is None else {"no_fill_probability": no_fill_probability}),
        **({} if partial_fill_ratio is None else {"expected_partial_fill_ratio": partial_fill_ratio}),
        **({} if latency_penalty is None else {"latency_penalty": latency_penalty}),
    }


def _signal_report(rows: list[dict[str, Any]], *, probability: float = 0.68) -> dict[str, Any]:
    return {
        "row_decisions": [
            {
                "row_id": row["clob_snapshot_id"],
                "clob_snapshot_id": row["clob_snapshot_id"],
                "market_id": row["market_id"],
                "token_id": row["token_id"],
                "outcome": row["outcome"],
                "resolved_outcome": row["resolved_outcome"],
                "side": "BUY",
                "predicted_probability": probability,
                "signal_strength": abs(float(row.get("spot_return_5s") or 0.0)),
                "primary_evidence": row["source_quality"] != "synthetic_stress",
                "blocked": False,
                "blockers": [],
                "spot_direction": "UP" if (row.get("spot_return_5s") or 0.0) > 0 else "DOWN",
            }
            for row in rows
        ],
        "candidate_signal_count": len(rows),
    }


def _phase44_blocked_rows() -> list[dict[str, Any]]:
    return [
        _row("allow_fixture_win", resolved_outcome="UP", ask=0.46, bid=0.44),
        _row("allow_fixture_loss", resolved_outcome="DOWN", ask=0.46, bid=0.44),
        _row(
            "allow_real_cached_win",
            resolved_outcome="UP",
            ask=0.47,
            bid=0.45,
            source_quality="real_cached",
            partial_fill_ratio=0.55,
        ),
        _row(
            "allow_real_cached_loss",
            resolved_outcome="DOWN",
            ask=0.47,
            bid=0.45,
            source_quality="real_cached",
            partial_fill_ratio=0.55,
        ),
        _row("wide_blocked", ask=0.62, bid=0.48, liquidity=900.0),
        _row("low_liquidity_blocked", ask=0.46, bid=0.44, liquidity=40.0),
        _row("near_end_blocked", ask=0.46, bid=0.44, seconds_to_window_end=2.0),
        _row(
            "synthetic_allow",
            ask=0.46,
            bid=0.44,
            source_quality="synthetic_stress",
            resolved_outcome="UP",
        ),
    ]


def test_sequence45_acquisition_plan_computes_allowed_intent_gaps(
    local_project: Path,
) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_allowed_intent_acquisition import (
        write_pm_crypto_updown_allowed_intent_acquisition_plan,
    )

    diagnostics = {
        "allowed_primary_intent_count": 3,
        "allowed_real_cached_intent_count": 2,
        "allowed_synthetic_diagnostic_intent_count": 1,
    }
    payload = write_pm_crypto_updown_allowed_intent_acquisition_plan(
        diagnostics=diagnostics,
        output_root=local_project,
    )

    assert payload["current_allowed_primary_intents"] == 3
    assert payload["target_allowed_primary_intents"] == 5
    assert payload["current_allowed_real_cached_intents"] == 2
    assert payload["target_allowed_real_cached_intents"] == 3
    assert payload["required_additional_allowed_primary_intents"] == 2
    assert payload["required_additional_allowed_real_cached_intents"] == 1
    assert payload["estimated_additional_two_token_windows_required"] == 2
    assert "sufficient_spot_lag_signal" in payload["required_new_window_properties"]
    assert payload["synthetic_rows_counted_as_primary"] is False
    assert payload["capture_artifacts_are_ignored_by_default"] is True
    assert (
        local_project
        / "reports"
        / "sequence45"
        / "allowed_intent_acquisition"
        / "latest_allowed_intent_acquisition_plan.json"
    ).exists()
    assert (
        local_project
        / "reports"
        / "sequence45"
        / "allowed_intent_acquisition"
        / "latest_allowed_intent_acquisition_plan.md"
    ).exists()


def test_sequence45_progress_counts_only_policy_allowed_primary_imports(
    local_project: Path,
) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_allowed_intent_diagnostics import (
        evaluate_pm_crypto_updown_allowed_intent_diagnostics,
    )
    from quant_os.research.replay_candidates.pm_crypto_updown_allowed_intent_progress import (
        write_pm_crypto_updown_allowed_intent_progress_report,
    )

    baseline_rows = _phase44_blocked_rows()
    imported_rows = [
        _row(
            "new_real_cached_allowed",
            source_quality="real_cached",
            resolved_outcome="UP",
            ask=0.45,
            bid=0.43,
            partial_fill_ratio=0.65,
        ),
        _row(
            "new_real_cached_wide_blocked",
            source_quality="real_cached",
            resolved_outcome="UP",
            ask=0.70,
            bid=0.50,
            partial_fill_ratio=0.65,
        ),
        _row(
            "new_synthetic_allowed",
            source_quality="synthetic_stress",
            resolved_outcome="UP",
            ask=0.45,
            bid=0.43,
        ),
    ]
    previous = evaluate_pm_crypto_updown_allowed_intent_diagnostics(
        rows=baseline_rows,
        signal_report=_signal_report(baseline_rows),
    )
    payload = write_pm_crypto_updown_allowed_intent_progress_report(
        previous_diagnostics=previous,
        rows=baseline_rows + imported_rows,
        signal_report=_signal_report(baseline_rows + imported_rows),
        imported_row_ids=[row["clob_snapshot_id"] for row in imported_rows],
        output_root=local_project,
    )

    assert payload["new_primary_rows"] == 2
    assert payload["new_real_cached_rows"] == 2
    assert payload["new_allowed_primary_intents"] == 1
    assert payload["new_allowed_real_cached_intents"] == 1
    assert payload["synthetic_rows_counted_as_primary"] is False
    assert "new_real_cached_allowed" in payload["new_allowed_primary_row_ids"]
    assert "new_synthetic_allowed" not in payload["new_allowed_primary_row_ids"]
    rejected_by_id = {item["row_id"]: item for item in payload["rows_blocked_by_policy"]}
    assert rejected_by_id["new_real_cached_wide_blocked"]["blocker_reasons"]
    assert payload["source_quality_separation"]["synthetic_counted_as_primary"] is False
    assert (
        local_project
        / "reports"
        / "sequence45"
        / "allowed_intent_progress"
        / "latest_allowed_intent_progress.json"
    ).exists()


def test_sequence45_progress_handles_repeated_real_cached_roots() -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_allowed_intent_progress import (
        summarize_pm_crypto_updown_allowed_intent_import_roots,
    )

    fixture_root = Path("tests/fixtures/replay_candidates/pm_crypto_updown/real_cached_sample")
    payload = summarize_pm_crypto_updown_allowed_intent_import_roots(
        real_cached_artifact_roots=[fixture_root, fixture_root],
    )

    assert payload["import_root_count"] == 2
    assert payload["dedupe_dropped_artifact_count"] > 0
    assert payload["newly_imported_artifacts"] > 0
    assert payload["newly_imported_windows"] > 0
    assert payload["local_files_only"] is True


def test_sequence45_candidate_decision_blocks_below_thresholds() -> None:
    from quant_os.readiness.pm_crypto_updown_allowed_intent_decision import (
        evaluate_pm_crypto_updown_allowed_intent_decision,
    )

    payload = evaluate_pm_crypto_updown_allowed_intent_decision(
        diagnostics={
            "primary_evidence_row_count": 24,
            "real_cached_replay_ready_row_count": 12,
            "allowed_primary_intent_count": 4,
            "allowed_real_cached_intent_count": 3,
            "allowed_synthetic_diagnostic_intent_count": 0,
            "does_any_conservative_policy_allow_nonzero_intents": True,
            "synthetic_rows_counted_as_primary": False,
            "cost_fill_adjusted_result": 0.3,
        },
        attribution={
            "active_blocker": "NONE",
            "candidate_beats_market_baseline": True,
            "candidate_beats_no_skill_baseline": True,
            "candidate_beats_or_separates_from_placebos": True,
            "market_baseline_dominant": False,
        },
        overfit_guard={"passes": True, "blockers": []},
        retirement={"retirement_action": "CONTINUE_WITH_MORE_ALLOWED_INTENTS"},
    )

    assert payload["decision_status"] == "NEEDS_MORE_ALLOWED_INTENTS"
    assert payload["ready_for_bounded_shadow_rehearsal"] is False
    assert payload["live_readiness_claimed"] is False
    assert payload["canary_readiness_claimed"] is False


def test_sequence45_candidate_decision_blocks_baseline_and_placebo_failures() -> None:
    from quant_os.readiness.pm_crypto_updown_allowed_intent_decision import (
        evaluate_pm_crypto_updown_allowed_intent_decision,
    )

    payload = evaluate_pm_crypto_updown_allowed_intent_decision(
        diagnostics={
            "primary_evidence_row_count": 24,
            "real_cached_replay_ready_row_count": 12,
            "allowed_primary_intent_count": 5,
            "allowed_real_cached_intent_count": 3,
            "allowed_synthetic_diagnostic_intent_count": 0,
            "does_any_conservative_policy_allow_nonzero_intents": True,
            "synthetic_rows_counted_as_primary": False,
            "cost_fill_adjusted_result": 0.3,
        },
        attribution={
            "active_blocker": "BASELINE_OR_PLACEBO_BLOCKED",
            "candidate_beats_market_baseline": False,
            "candidate_beats_no_skill_baseline": True,
            "candidate_beats_or_separates_from_placebos": True,
            "market_baseline_dominant": True,
            "baselines_beating_or_tying_candidate": ["market_probability"],
            "placebos_beating_or_tying_candidate": [],
        },
        overfit_guard={"passes": True, "blockers": []},
        retirement={"retirement_action": "CONTINUE_WITH_MORE_ALLOWED_INTENTS"},
    )

    assert payload["decision_status"] == "BASELINE_OR_PLACEBO_BLOCKED"
    assert "market_probability" in payload["blockers"]


def test_sequence45_candidate_decision_blocks_one_row_dominance() -> None:
    from quant_os.readiness.pm_crypto_updown_allowed_intent_decision import (
        evaluate_pm_crypto_updown_allowed_intent_decision,
    )

    payload = evaluate_pm_crypto_updown_allowed_intent_decision(
        diagnostics={
            "primary_evidence_row_count": 24,
            "real_cached_replay_ready_row_count": 12,
            "allowed_primary_intent_count": 5,
            "allowed_real_cached_intent_count": 3,
            "allowed_synthetic_diagnostic_intent_count": 0,
            "does_any_conservative_policy_allow_nonzero_intents": True,
            "synthetic_rows_counted_as_primary": False,
            "cost_fill_adjusted_result": 0.3,
        },
        attribution={
            "active_blocker": "NONE",
            "candidate_beats_market_baseline": True,
            "candidate_beats_no_skill_baseline": True,
            "candidate_beats_or_separates_from_placebos": True,
            "market_baseline_dominant": False,
        },
        overfit_guard={
            "passes": False,
            "blockers": ["ONE_ROW_DOMINANCE_SHARE_0.750_GT_0.500"],
        },
        retirement={"retirement_action": "CONTINUE_WITH_MORE_ALLOWED_INTENTS"},
    )

    assert payload["decision_status"] == "OVERFIT_RISK_TOO_HIGH"
    assert "ONE_ROW_DOMINANCE_SHARE_0.750_GT_0.500" in payload["blockers"]


def test_sequence45_candidate_decision_can_reach_bounded_shadow_only_when_all_gates_pass() -> None:
    from quant_os.readiness.pm_crypto_updown_allowed_intent_decision import (
        evaluate_pm_crypto_updown_allowed_intent_decision,
    )

    payload = evaluate_pm_crypto_updown_allowed_intent_decision(
        diagnostics={
            "primary_evidence_row_count": 24,
            "real_cached_replay_ready_row_count": 12,
            "allowed_primary_intent_count": 5,
            "allowed_real_cached_intent_count": 3,
            "allowed_synthetic_diagnostic_intent_count": 0,
            "does_any_conservative_policy_allow_nonzero_intents": True,
            "synthetic_rows_counted_as_primary": False,
            "cost_fill_adjusted_result": 0.3,
            "blocker_causes": {"cost_fill_erosion": False},
        },
        attribution={
            "active_blocker": "NONE",
            "candidate_beats_market_baseline": True,
            "candidate_beats_no_skill_baseline": True,
            "candidate_beats_or_separates_from_placebos": True,
            "market_baseline_dominant": False,
        },
        overfit_guard={"passes": True, "blockers": []},
        retirement={"retirement_action": "CONTINUE_WITH_MORE_ALLOWED_INTENTS"},
    )

    assert payload["decision_status"] == "READY_FOR_BOUNDED_SHADOW_REHEARSAL"
    assert payload["ready_for_bounded_shadow_rehearsal"] is True
    assert payload["not_live_readiness"] is True
    assert payload["not_canary_readiness"] is True
    assert payload["order_routing_enabled"] is False


def test_sequence45_bounded_shadow_rehearsal_package_requires_ready_decision(
    local_project: Path,
) -> None:
    from quant_os.proving.pm_crypto_updown_bounded_shadow_rehearsal_spec import (
        write_pm_crypto_updown_bounded_shadow_rehearsal_report,
    )

    blocked = write_pm_crypto_updown_bounded_shadow_rehearsal_report(
        candidate_decision={
            "decision_status": "NEEDS_MORE_ALLOWED_INTENTS",
            "ready_for_bounded_shadow_rehearsal": False,
            "blockers": ["NEEDS_MORE_ALLOWED_INTENTS"],
            "allowed_primary_intent_count": 3,
            "allowed_real_cached_intent_count": 2,
        },
        output_root=local_project,
    )
    ready = write_pm_crypto_updown_bounded_shadow_rehearsal_report(
        candidate_decision={
            "decision_status": "READY_FOR_BOUNDED_SHADOW_REHEARSAL",
            "ready_for_bounded_shadow_rehearsal": True,
            "blockers": [],
            "allowed_primary_intent_count": 5,
            "allowed_real_cached_intent_count": 3,
        },
        output_root=local_project,
    )

    assert blocked["package_created"] is False
    assert blocked["status"] == "BOUNDED_SHADOW_REHEARSAL_BLOCKED"
    assert ready["package_created"] is True
    assert ready["status"] == "BOUNDED_SHADOW_REHEARSAL_SPEC_READY"
    assert ready["offline_only"] is True
    assert ready["order_routing_enabled"] is False
    assert ready["wallet_signing_enabled"] is False


def test_sequence45_notes_and_autonomy_ledger_keep_reference_material_non_executing() -> None:
    from quant_os.readiness.autonomy_milestones import build_sequence45_autonomy_milestones
    from quant_os.research.replay_candidates.pm_crypto_updown_phase45_notes import (
        build_pm_crypto_updown_phase45_reference_notes,
    )

    decision = {
        "decision_status": "NEEDS_MORE_ALLOWED_INTENTS",
        "ready_for_bounded_shadow_rehearsal": False,
        "allowed_primary_intent_count": 3,
        "allowed_real_cached_intent_count": 2,
        "blockers": ["NEEDS_MORE_ALLOWED_INTENTS"],
    }
    notes = build_pm_crypto_updown_phase45_reference_notes()
    ledger = build_sequence45_autonomy_milestones(candidate_decision=decision)
    milestones = {item["milestone_id"]: item for item in ledger["milestones"]}

    assert "pm_lp_refresh_lag_arbitrage" in notes["candidate_backlog_families"]
    assert notes["kelly_sizing_policy"]["sizing_enabled"] is False
    assert "LLM_DISCRETIONARY_TRADING_PROMPT" in notes["social_intake_warning_categories"]
    assert notes["reference_only_external_repos"]["google_skills"]["vendor_or_install"] is False
    assert notes["reference_only_external_repos"]["scenario_lab"]["vendor_or_install"] is False
    assert milestones["evidence_acquisition_repeatable"]["status"] == "MET"
    assert milestones["replay_inputs_sufficient"]["status"] == "MET"
    assert milestones["shadow_proving_threshold_met"]["status"] == "MET"
    assert milestones["allowed_intent_threshold_met"]["status"] == "BLOCKED"
    assert milestones["bounded_shadow_rehearsal_ready"]["status"] == "BLOCKED"
    assert milestones["first_tiny_canary_allowed"]["status"] == "BLOCKED"
    assert ledger["live_orders_allowed"] is False


def test_sequence45_cli_make_targets_and_forbidden_paths_are_non_executing(
    local_project: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = {
        **os.environ,
        "PYTHONPATH": str(repo_root / "src"),
    }
    commands = [
        [
            sys.executable,
            "-m",
            "quant_os.cli",
            "research",
            "pm-crypto-updown-allowed-intent-acquisition",
        ],
        [
            sys.executable,
            "-m",
            "quant_os.cli",
            "research",
            "pm-crypto-updown-allowed-intent-progress",
        ],
        [
            sys.executable,
            "-m",
            "quant_os.cli",
            "research",
            "pm-crypto-updown-baseline-placebo-update",
        ],
        [
            sys.executable,
            "-m",
            "quant_os.cli",
            "readiness",
            "pm-crypto-updown-allowed-intent-decision",
        ],
    ]

    for command in commands:
        result = subprocess.run(
            command,
            cwd=local_project,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        assert "live_trading_enabled" in result.stdout
        assert "False" in result.stdout
        assert "execution_authority" in result.stdout
        assert "NONE" in result.stdout

    make_cmd = (repo_root / "make.cmd").read_text(encoding="utf-8")
    assert 'if "%TARGET%"=="sequence45-smoke"' in make_cmd
    assert 'if "%TARGET%"=="allowed-intent-acquisition-smoke"' in make_cmd
    assert 'if "%TARGET%"=="allowed-intent-decision-smoke"' in make_cmd

    source_paths = [
        "src/quant_os/research/replay_candidates/pm_crypto_updown_allowed_intent_acquisition.py",
        "src/quant_os/research/replay_candidates/pm_crypto_updown_allowed_intent_progress.py",
        "src/quant_os/readiness/pm_crypto_updown_allowed_intent_decision.py",
        "src/quant_os/proving/pm_crypto_updown_bounded_shadow_rehearsal_spec.py",
        "src/quant_os/research/replay_candidates/pm_crypto_updown_phase45_notes.py",
    ]
    forbidden_tokens = [
        "create_order",
        "cancel_order",
        "post_order",
        "private_key",
        "wallet_signer",
        "sign_order",
        "copy_wallet_trade",
        "captcha_bypass",
        "proxy_rotation",
        "stealth_evasion",
    ]
    for source_path in source_paths:
        text = (repo_root / source_path).read_text(encoding="utf-8").lower()
        for token in forbidden_tokens:
            assert token not in text
