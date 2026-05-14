from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "replay_candidates" / "pm_crypto_updown"
REAL_CACHED_SAMPLE_ROOT = FIXTURE_ROOT / "real_cached_sample"


def _write_manifest_only_run(root: Path) -> Path:
    from quant_os.data.prediction_markets.pm_updown_real_cached_capture import (
        write_pm_crypto_updown_real_cached_capture_plan,
    )

    payload = write_pm_crypto_updown_real_cached_capture_plan(
        output_root=root,
        manual_network_ok=True,
        run_id="pm_crypto_updown_manual_041",
    )
    return root / payload["run_root"]


def _write_duplicate_root(root: Path) -> Path:
    duplicate_root = root / "duplicate_real_cached"
    duplicate_root.mkdir()
    duplicate_root.joinpath("artifacts.jsonl").write_text(
        (REAL_CACHED_SAMPLE_ROOT / "artifacts.jsonl").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return duplicate_root


def _write_malformed_root(root: Path) -> Path:
    malformed_root = root / "malformed_real_cached"
    malformed_root.mkdir()
    malformed_root.joinpath("artifacts.jsonl").write_text(
        json.dumps(
            {
                "artifact_type": "pm_clob_snapshot",
                "source_id": "sequence41_missing_timestamp",
                "capture_mode": "local_import",
                "captured_at": "2026-05-13T12:00:00Z",
                "raw_hash": "raw_sequence41_bad",
                "normalized_hash": "norm_sequence41_bad",
                "source_note": "malformed sequence41 test artifact",
                "provenance": {"test": True},
                "quality_flags": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return malformed_root


def test_sequence41_window_acquisition_plan_computes_gap_and_required_windows(
    local_project: Path,
    tmp_path: Path,
) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_window_acquisition_report import (
        write_pm_crypto_updown_window_acquisition_plan,
    )

    manual_root = _write_manifest_only_run(tmp_path)
    payload = write_pm_crypto_updown_window_acquisition_plan(
        fixture_root=FIXTURE_ROOT,
        real_cached_artifact_roots=[REAL_CACHED_SAMPLE_ROOT, manual_root],
        output_root=local_project,
    )

    assert payload["schema_version"] == "pm_crypto_updown_window_acquisition_plan_v1"
    assert payload["sequence"] == "41"
    assert payload["previous_primary_row_count"] == 10
    assert payload["current_primary_row_count"] == 10
    assert payload["current_real_cached_row_count"] == 4
    assert payload["target_primary_row_count"] == 20
    assert payload["row_gap"] == 10
    assert payload["required_remaining_two_token_windows"] == 5
    assert len(payload["needed_two_token_windows"]) == 5
    assert payload["needed_two_token_windows"][0]["required_artifacts"] == [
        "market_metadata",
        "condition_id",
        "token_ids_and_outcomes",
        "window_start_ts_and_window_end_ts",
        "clob_orderbook_snapshots",
        "spot_snapshots_or_candles",
        "label_or_resolution_data",
        "liquidity_and_spread",
    ]
    assert payload["operator_action_required"] is True
    assert payload["code_missing"] is False
    assert payload["capture_or_import_status"] == "OPERATOR_ACTION_REQUIRED"
    assert "SOURCE_COVERAGE_REAL_CACHED_ROWS_4_LT_REQUIRED_14" in payload["blockers"]
    assert "python -m quant_os.cli data pm-crypto-updown-real-cached-import" in " ".join(
        payload["operator_commands"]
    )
    assert (
        local_project
        / "reports"
        / "sequence41"
        / "window_acquisition"
        / "latest_window_acquisition_plan.json"
    ).exists()


def test_sequence41_repeated_real_cached_root_import_aggregates_and_dedupes(
    tmp_path: Path,
) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_real_cached_import import (
        import_pm_crypto_updown_real_cached_artifact_roots,
    )

    duplicate_root = _write_duplicate_root(tmp_path)
    manifest_root = _write_manifest_only_run(tmp_path)
    malformed_root = _write_malformed_root(tmp_path)

    payload = import_pm_crypto_updown_real_cached_artifact_roots(
        import_roots=[REAL_CACHED_SAMPLE_ROOT, duplicate_root, manifest_root, malformed_root],
        output_root=tmp_path,
    )

    assert payload["schema_version"] == "pm_crypto_updown_real_cached_import_v2"
    assert payload["sequence"] == "41"
    assert payload["accepted_artifact_count"] == 12
    assert payload["dedupe_dropped_artifact_count"] == 12
    assert payload["rejected_artifact_count"] == 1
    assert payload["rejected_by_reason"] == {"MISSING_TIMESTAMP": 1}
    assert payload["manifest_only_root_count"] == 1
    assert payload["real_cached_rows_imported"] == 4
    assert payload["source_mode_counts"] == {"local_import": 12}
    assert payload["source_quality_counts"] == {"real_cached": 12}
    assert payload["normalized_source"]["source_quality"] == "real_cached"
    assert payload["root_summaries"][2]["coverage_status"] == "MANIFEST_ONLY_NO_ARTIFACTS"


def test_sequence41_threshold_replay_readiness_and_milestones_remain_blocked_below_20(
    local_project: Path,
    tmp_path: Path,
) -> None:
    from quant_os.readiness.expanded_shadow_replay_readiness_report import (
        write_sequence41_expanded_shadow_replay_readiness_report,
    )
    from quant_os.research.replay_candidates.pm_crypto_updown_real_cached_replay_eval import (
        write_pm_crypto_updown_sequence41_replay_eval_report,
    )
    from quant_os.research.replay_candidates.pm_crypto_updown_threshold_progress import (
        write_pm_crypto_updown_sequence41_threshold_progress_report,
    )

    manual_root = _write_manifest_only_run(tmp_path)
    roots = [REAL_CACHED_SAMPLE_ROOT, manual_root]
    progress = write_pm_crypto_updown_sequence41_threshold_progress_report(
        fixture_root=FIXTURE_ROOT,
        real_cached_artifact_roots=roots,
        output_root=local_project,
    )
    evaluation = write_pm_crypto_updown_sequence41_replay_eval_report(
        fixture_root=FIXTURE_ROOT,
        real_cached_artifact_roots=roots,
        output_root=local_project,
    )
    readiness = write_sequence41_expanded_shadow_replay_readiness_report(
        real_cached_replay_eval=evaluation,
        output_root=local_project,
    )

    assert progress["sequence"] == "41"
    assert progress["previous_primary_row_count"] == 10
    assert progress["current_primary_row_count"] == 10
    assert progress["previous_real_cached_row_count"] == 4
    assert progress["current_real_cached_row_count"] == 4
    assert progress["row_gap"] == 10
    assert progress["rows_added_by_source_quality"] == {}
    assert progress["source_coverage"]["additional_two_token_windows_needed_estimate"] == 5
    assert "SOURCE_COVERAGE_REAL_CACHED_ROWS_4_LT_REQUIRED_14" in progress["blockers"]
    assert evaluation["sequence"] == "41"
    assert evaluation["primary_result"]["row_count"] == 10
    assert evaluation["real_cached_result"]["row_count"] == 4
    assert evaluation["synthetic_rows_counted_as_primary"] is False
    assert readiness["sequence"] == "41"
    assert readiness["readiness_status"] == "PRIMARY_EVIDENCE_STILL_TOO_THIN"
    assert readiness["overall_status"] == "CANDIDATE_REMAINS_BLOCKED"
    assert readiness["ready_for_expanded_shadow_replay"] is False
    assert readiness["not_live_readiness"] is True
    assert readiness["not_canary_readiness"] is True
    assert readiness["live_readiness_claimed"] is False
    assert readiness["canary_readiness_claimed"] is False
    assert readiness["autonomy_milestones"]["real_cached_evidence_acquisition"] == "partial"
    assert readiness["autonomy_milestones"]["replay_evidence_threshold"] == "partial"
    assert readiness["autonomy_milestones"]["expanded_shadow_replay"] == "blocked"
    assert readiness["autonomy_milestones"]["canary"] == "blocked"
    assert readiness["autonomy_milestones"]["live"] == "blocked"
    assert (
        local_project
        / "reports"
        / "sequence41"
        / "threshold_progress"
        / "latest_threshold_progress.json"
    ).exists()
    assert (
        local_project
        / "reports"
        / "sequence41"
        / "replay_eval"
        / "latest_pm_crypto_updown_replay_eval.json"
    ).exists()
    assert (
        local_project
        / "reports"
        / "sequence41"
        / "expanded_shadow_replay_readiness"
        / "latest_expanded_shadow_replay_readiness.json"
    ).exists()


def test_sequence41_cli_and_make_targets_are_non_executing(local_project: Path) -> None:
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
            "pm-crypto-updown-window-acquisition",
            "--real-cached-root",
            str(REAL_CACHED_SAMPLE_ROOT),
        ],
        [
            sys.executable,
            "-m",
            "quant_os.cli",
            "data",
            "pm-crypto-updown-real-cached-import",
            "--real-cached-root",
            str(REAL_CACHED_SAMPLE_ROOT),
            "--real-cached-root",
            str(REAL_CACHED_SAMPLE_ROOT),
        ],
        [
            sys.executable,
            "-m",
            "quant_os.cli",
            "readiness",
            "expanded-shadow-replay-readiness",
            "--real-cached-root",
            str(REAL_CACHED_SAMPLE_ROOT),
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
    assert 'if "%TARGET%"=="sequence41-smoke"' in make_cmd
    assert 'if "%TARGET%"=="pm-crypto-updown-window-acquisition-smoke"' in make_cmd
    assert 'if "%TARGET%"=="expanded-shadow-replay-readiness-smoke"' in make_cmd


def test_sequence41_modules_do_not_add_auth_signing_order_cancel_wallet_or_evasion_paths() -> None:
    source_paths = [
        Path("src/quant_os/research/replay_candidates/pm_crypto_updown_window_acquisition.py"),
        Path("src/quant_os/research/replay_candidates/pm_crypto_updown_window_acquisition_report.py"),
        Path("src/quant_os/research/replay_candidates/pm_crypto_updown_real_cached_import.py"),
        Path("src/quant_os/research/replay_candidates/pm_crypto_updown_threshold_progress.py"),
        Path("src/quant_os/research/replay_candidates/pm_crypto_updown_real_cached_replay_eval.py"),
        Path("src/quant_os/readiness/expanded_shadow_replay_readiness.py"),
        Path("src/quant_os/readiness/expanded_shadow_replay_readiness_report.py"),
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

    for path in source_paths:
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        for token in forbidden_tokens:
            assert token not in lowered
