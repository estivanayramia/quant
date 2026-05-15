from __future__ import annotations

import json
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
    partial_fill_ratio: float | None = None,
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
        **({} if partial_fill_ratio is None else {"expected_partial_fill_ratio": partial_fill_ratio}),
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


def _previous_diagnostics() -> dict[str, Any]:
    return {
        "allowed_primary_intent_count": 3,
        "allowed_real_cached_intent_count": 2,
        "allowed_synthetic_diagnostic_intent_count": 1,
    }


def _manifest_only_root(root: Path) -> Path:
    run_root = root / "data" / "external" / "manual_captures" / "pm_crypto_updown" / "run_046"
    run_root.mkdir(parents=True)
    (run_root / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": "pm_crypto_updown_real_cached_capture_plan_v1",
                "run_id": "run_046",
                "network_fetch_attempted": False,
                "auth_required": False,
                "wallet_required": False,
                "order_placement_allowed": False,
                "order_cancellation_allowed": False,
            }
        ),
        encoding="utf-8",
    )
    return run_root


def test_sequence46_capture_pass_report_is_deterministic_and_counts_before_after(
    local_project: Path,
) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_allowed_intent_capture_pass import (
        write_pm_crypto_updown_allowed_intent_capture_pass_report,
    )

    run_root = _manifest_only_root(local_project)
    progress = {
        "previous_allowed_primary_intents": 3,
        "previous_allowed_real_cached_intents": 2,
        "current_allowed_primary_intents": 3,
        "current_allowed_real_cached_intents": 2,
        "allowed_primary_intent_delta": 0,
        "allowed_real_cached_intent_delta": 0,
        "new_allowed_primary_intents": 0,
        "new_allowed_real_cached_intents": 0,
        "new_allowed_primary_row_ids": [],
        "new_allowed_real_cached_row_ids": [],
        "diagnostics": {
            "allowed_primary_intent_count": 3,
            "allowed_real_cached_intent_count": 2,
            "active_blocker": "NEEDS_MORE_ALLOWED_INTENTS",
        },
        "real_cached_import_summary": {
            "newly_imported_artifacts": 0,
            "rejected_artifact_count": 0,
            "newly_imported_windows": 0,
            "newly_imported_rows": 0,
            "root_summaries": [
                {
                    "import_root": str(run_root).replace("\\", "/"),
                    "coverage_status": "MANIFEST_ONLY_NO_ARTIFACTS",
                    "accepted_artifact_count": 0,
                    "rejected_artifact_count": 0,
                    "dedupe_dropped_artifact_count": 0,
                    "raw_artifact_count": 0,
                }
            ],
        },
        "source_quality_separation": {
            "synthetic_counted_as_primary": False,
            "source_quality_counts": {},
        },
        "synthetic_rows_counted_as_primary": False,
    }

    first = write_pm_crypto_updown_allowed_intent_capture_pass_report(
        run_id="run_046",
        capture_run_root=run_root,
        progress_payload=progress,
        output_root=local_project,
    )
    second = write_pm_crypto_updown_allowed_intent_capture_pass_report(
        run_id="run_046",
        capture_run_root=run_root,
        progress_payload=progress,
        output_root=local_project,
    )

    assert first == second
    assert first["run_id"] == "run_046"
    assert first["capture_attempted"] is True
    assert first["network_attempted"] is False
    assert first["auth_used"] is False
    assert first["wallet_used"] is False
    assert first["order_endpoints_used"] is False
    assert first["artifacts_accepted"] == 0
    assert first["artifacts_rejected"] == 0
    assert first["windows_captured_or_imported"] == 0
    assert first["rows_imported"] == 0
    assert first["allowed_primary_intents_before"] == 3
    assert first["allowed_primary_intents_after"] == 3
    assert first["allowed_real_cached_intents_before"] == 2
    assert first["allowed_real_cached_intents_after"] == 2
    assert first["allowed_intent_threshold_passed"] is False
    assert first["source_coverage_still_missing"] is True
    assert first["blocker_after"] == "NEEDS_MORE_ALLOWED_INTENTS"
    assert "pm-crypto-updown-real-cached-import" in first["exact_next_command_if_still_blocked"]
    assert (
        local_project
        / "reports"
        / "sequence46"
        / "allowed_intent_capture"
        / "latest_allowed_intent_capture_pass.json"
    ).exists()
    assert (
        local_project
        / "reports"
        / "sequence46"
        / "allowed_intent_capture"
        / "latest_allowed_intent_capture_pass.md"
    ).exists()


def test_sequence46_imported_evidence_increases_counts_only_when_policy_filters_pass(
    local_project: Path,
) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_allowed_intent_capture_pass import (
        write_pm_crypto_updown_allowed_intent_capture_pass_report,
    )

    baseline_rows = [
        _row("old_fixture_win", resolved_outcome="UP"),
        _row("old_fixture_loss", resolved_outcome="DOWN"),
        _row(
            "old_real_cached_win",
            resolved_outcome="UP",
            source_quality="real_cached",
            partial_fill_ratio=0.6,
        ),
        _row(
            "old_real_cached_loss",
            resolved_outcome="DOWN",
            source_quality="real_cached",
            partial_fill_ratio=0.6,
        ),
        _row("old_wide_blocked", ask=0.70, bid=0.50),
        _row("old_synthetic", source_quality="synthetic_stress", resolved_outcome="UP"),
    ]
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
            ask=0.72,
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
    rows = baseline_rows + imported_rows
    payload = write_pm_crypto_updown_allowed_intent_capture_pass_report(
        run_id="run_policy_filters",
        previous_diagnostics=_previous_diagnostics(),
        rows=rows,
        signal_report=_signal_report(rows),
        imported_row_ids=[row["clob_snapshot_id"] for row in imported_rows],
        output_root=local_project,
    )

    assert payload["new_allowed_primary_intents"] == 1
    assert payload["new_allowed_real_cached_intents"] == 1
    assert payload["allowed_primary_intents_after"] == 4
    assert payload["allowed_real_cached_intents_after"] == 3
    assert payload["synthetic_rows_counted_as_primary"] is False
    assert "new_real_cached_allowed" in payload["new_allowed_primary_row_ids"]
    assert "new_synthetic_allowed" not in payload["new_allowed_primary_row_ids"]


def test_sequence46_candidate_path_final_statuses_and_promotion_require_all_gates(
    local_project: Path,
) -> None:
    from quant_os.readiness.pm_crypto_updown_phase46_candidate_path import (
        PHASE46_FINAL_STATUSES,
        evaluate_pm_crypto_updown_phase46_candidate_path,
    )
    from quant_os.readiness.pm_crypto_updown_phase46_candidate_path_report import (
        write_pm_crypto_updown_phase46_candidate_path_report,
    )

    assert PHASE46_FINAL_STATUSES == [
        "READY_FOR_BOUNDED_SHADOW_REHEARSAL",
        "NEEDS_MORE_ALLOWED_INTENTS",
        "DEPRIORITIZE_CANDIDATE",
        "RETIRE_CANDIDATE",
    ]

    ready = evaluate_pm_crypto_updown_phase46_candidate_path(
        capture_pass={
            "capture_attempted": True,
            "allowed_primary_intents_before": 3,
            "allowed_primary_intents_after": 5,
            "allowed_real_cached_intents_before": 2,
            "allowed_real_cached_intents_after": 3,
            "allowed_intent_threshold_passed": True,
            "source_coverage_still_missing": False,
            "exact_next_command_if_still_blocked": "",
        },
        candidate_decision={
            "decision_status": "READY_FOR_BOUNDED_SHADOW_REHEARSAL",
            "ready_for_bounded_shadow_rehearsal": True,
            "candidate_beats_market_baseline": True,
            "candidate_beats_no_skill_baseline": True,
            "candidate_beats_or_separates_from_placebos": True,
            "anti_overfit_guard_passes": True,
            "blockers": [],
        },
    )
    blocked = evaluate_pm_crypto_updown_phase46_candidate_path(
        capture_pass={
            "capture_attempted": True,
            "allowed_primary_intents_before": 3,
            "allowed_primary_intents_after": 5,
            "allowed_real_cached_intents_before": 2,
            "allowed_real_cached_intents_after": 3,
            "allowed_intent_threshold_passed": True,
            "source_coverage_still_missing": False,
            "exact_next_command_if_still_blocked": "",
        },
        candidate_decision={
            "decision_status": "BASELINE_OR_PLACEBO_BLOCKED",
            "ready_for_bounded_shadow_rehearsal": False,
            "candidate_beats_market_baseline": True,
            "candidate_beats_no_skill_baseline": True,
            "candidate_beats_or_separates_from_placebos": False,
            "anti_overfit_guard_passes": True,
            "blockers": ["BASELINE_OR_PLACEBO_BLOCKED"],
        },
    )
    ready_report = write_pm_crypto_updown_phase46_candidate_path_report(
        capture_pass=ready["capture_pass"],
        candidate_decision=ready["candidate_decision"],
        output_root=local_project,
    )

    assert ready["final_status"] == "READY_FOR_BOUNDED_SHADOW_REHEARSAL"
    assert ready_report["bounded_shadow_rehearsal_package_created"] is True
    assert blocked["final_status"] == "DEPRIORITIZE_CANDIDATE"
    assert blocked["bounded_shadow_rehearsal_package_created"] is False
    assert blocked["live_readiness_claimed"] is False
    assert blocked["canary_readiness_claimed"] is False


def test_sequence46_candidate_path_deprioritizes_manifest_only_no_improvement_and_writes_handoff(
    local_project: Path,
) -> None:
    from quant_os.readiness.pm_crypto_updown_phase46_candidate_path_report import (
        write_pm_crypto_updown_phase46_candidate_path_report,
    )

    payload = write_pm_crypto_updown_phase46_candidate_path_report(
        capture_pass={
            "run_id": "pm_crypto_updown_manual_046",
            "capture_attempted": True,
            "network_attempted": False,
            "artifacts_accepted": 0,
            "rows_imported": 0,
            "allowed_primary_intents_before": 3,
            "allowed_primary_intents_after": 3,
            "allowed_real_cached_intents_before": 2,
            "allowed_real_cached_intents_after": 2,
            "allowed_intent_threshold_passed": False,
            "source_coverage_still_missing": True,
            "exact_next_command_if_still_blocked": (
                "python -m quant_os.cli data pm-crypto-updown-real-cached-import "
                "--real-cached-root tests\\fixtures\\replay_candidates\\pm_crypto_updown\\real_cached_sample "
                "--real-cached-root data\\external\\manual_captures\\pm_crypto_updown\\pm_crypto_updown_manual_046"
            ),
            "blocker_after": "NEEDS_MORE_ALLOWED_INTENTS",
        },
        candidate_decision={
            "decision_status": "NEEDS_MORE_ALLOWED_INTENTS",
            "ready_for_bounded_shadow_rehearsal": False,
            "candidate_beats_market_baseline": True,
            "candidate_beats_no_skill_baseline": True,
            "candidate_beats_or_separates_from_placebos": False,
            "anti_overfit_guard_passes": False,
            "blockers": [
                "NEEDS_MORE_ALLOWED_INTENTS",
                "ALLOWED_PRIMARY_INTENTS_3_LT_5",
                "ALLOWED_REAL_CACHED_INTENTS_2_LT_3",
            ],
        },
        output_root=local_project,
    )

    handoff = (
        local_project
        / "reports"
        / "sequence46"
        / "next_candidate_handoff"
        / "latest_next_candidate_handoff.md"
    )
    bounded = (
        local_project
        / "reports"
        / "sequence46"
        / "bounded_shadow_rehearsal"
        / "latest_bounded_shadow_rehearsal.json"
    )

    assert payload["final_status"] == "DEPRIORITIZE_CANDIDATE"
    assert payload["next_candidate_handoff_created"] is True
    assert payload["bounded_shadow_rehearsal_package_created"] is False
    assert handoff.exists()
    assert "pm_lp_refresh_lag_arbitrage" in handoff.read_text(encoding="utf-8")
    assert not bounded.exists()


def test_sequence46_cli_make_targets_and_forbidden_paths_are_non_executing(
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
            "pm-crypto-updown-phase46-capture-pass",
            "--run-id",
            "pm_crypto_updown_manual_046",
            "--real-cached-root",
            str(
                repo_root
                / "tests"
                / "fixtures"
                / "replay_candidates"
                / "pm_crypto_updown"
                / "real_cached_sample"
            ),
        ],
        [
            sys.executable,
            "-m",
            "quant_os.cli",
            "readiness",
            "pm-crypto-updown-phase46-candidate-path",
            "--run-id",
            "pm_crypto_updown_manual_046",
            "--real-cached-root",
            str(
                repo_root
                / "tests"
                / "fixtures"
                / "replay_candidates"
                / "pm_crypto_updown"
                / "real_cached_sample"
            ),
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
    assert 'if "%TARGET%"=="sequence46-smoke"' in make_cmd

    source_paths = [
        "src/quant_os/research/replay_candidates/pm_crypto_updown_allowed_intent_capture_pass.py",
        "src/quant_os/readiness/pm_crypto_updown_phase46_candidate_path.py",
        "src/quant_os/readiness/pm_crypto_updown_phase46_candidate_path_report.py",
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
