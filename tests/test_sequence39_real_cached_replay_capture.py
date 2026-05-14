from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "replay_candidates" / "pm_crypto_updown"
REAL_CACHED_SAMPLE_ROOT = FIXTURE_ROOT / "real_cached_sample"


def test_sequence39_real_cached_artifact_schema_validates_required_metadata() -> None:
    from quant_os.research.replay_candidates.real_cached_artifact_models import (
        RealCachedArtifact,
        real_cached_primary_capture_mode,
    )

    artifact = RealCachedArtifact.model_validate(
        {
            "artifact_type": "pm_clob_snapshot",
            "source_id": "unit_source",
            "capture_mode": "real_cached_manual",
            "captured_at": "2026-05-13T12:00:46Z",
            "event_ts": "2026-05-13T12:00:45Z",
            "market_id": "pm_unit",
            "condition_id": "cond_unit",
            "slug": "unit-up-down",
            "token_id": "token_up",
            "outcome": "UP",
            "raw_hash": "raw",
            "normalized_hash": "norm",
            "source_url": "https://example.invalid/public-read-only",
            "provenance": {"test": True},
            "quality_flags": ["READ_ONLY"],
            "clob_snapshot_id": "clob_unit",
            "bid": 0.51,
            "ask": 0.53,
            "last_trade_price": 0.52,
            "volume": 1000.0,
            "liquidity": 750.0,
        }
    )

    assert artifact.artifact_type == "pm_clob_snapshot"
    assert real_cached_primary_capture_mode(artifact.capture_mode) is True
    assert real_cached_primary_capture_mode("fixture_real_shaped") is False
    assert real_cached_primary_capture_mode("synthetic_stress") is False
    with pytest.raises(ValidationError):
        RealCachedArtifact.model_validate(
            {
                "artifact_type": "spot_snapshot",
                "source_id": "unit_source",
                "capture_mode": "local_import",
                "captured_at": "2026-05-13T12:00:46Z",
                "spot_symbol": "BTC-USD",
                "raw_hash": "raw",
                "normalized_hash": "norm",
                "provenance": {"test": True},
                "quality_flags": [],
                "price": 100000.0,
            }
        )


def test_sequence39_manual_capture_plan_is_disabled_by_default_and_requires_network_flag(
    local_project: Path,
) -> None:
    from quant_os.data.prediction_markets.pm_updown_real_cached_capture import (
        write_pm_crypto_updown_real_cached_capture_plan,
    )

    default_payload = write_pm_crypto_updown_real_cached_capture_plan(output_root=local_project)
    network_payload = write_pm_crypto_updown_real_cached_capture_plan(
        output_root=local_project,
        manual_network_ok=True,
        run_id="unit_run",
    )

    assert default_payload["schema_version"] == "pm_crypto_updown_real_cached_capture_plan_v1"
    assert default_payload["status"] == "REAL_CACHED_CAPTURE_READY"
    assert default_payload["manual_only"] is True
    assert default_payload["read_only"] is True
    assert default_payload["network_enabled"] is False
    assert default_payload["network_fetch_attempted"] is False
    assert default_payload["auth_required"] is False
    assert default_payload["wallet_required"] is False
    assert default_payload["signing_allowed"] is False
    assert default_payload["order_placement_allowed"] is False
    assert default_payload["order_cancellation_allowed"] is False
    assert default_payload["ci_network_dependency"] is False
    assert "data/external/manual_captures/pm_crypto_updown/" in default_payload["run_root"]
    assert network_payload["network_enabled"] is True
    assert network_payload["network_fetch_attempted"] is False
    assert network_payload["status"] == "REAL_CACHED_CAPTURE_READY"
    assert (local_project / "reports" / "sequence39" / "manual_capture" / "latest_real_cached_capture_plan.json").exists()


def test_sequence39_real_cached_import_rejects_malformed_artifacts_and_dedupes(
    tmp_path: Path,
) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_real_cached_import import (
        import_pm_crypto_updown_real_cached_artifacts,
    )

    root = tmp_path / "import_root"
    root.mkdir()
    original_lines = (REAL_CACHED_SAMPLE_ROOT / "artifacts.jsonl").read_text(encoding="utf-8").splitlines()
    duplicate = json.loads(original_lines[1])
    duplicate["source_id"] = "duplicate_source_id"
    malformed = {
        "artifact_type": "pm_clob_snapshot",
        "source_id": "missing_event_ts",
        "capture_mode": "local_import",
        "captured_at": "2026-05-13T12:00:00Z",
        "raw_hash": "raw_bad",
        "normalized_hash": "norm_bad",
        "provenance": {},
        "quality_flags": [],
    }
    unsupported = json.loads(original_lines[2])
    unsupported["capture_mode"] = "wallet_signed"
    unsupported["normalized_hash"] = "unsupported_mode"
    lines = original_lines + [json.dumps(duplicate), json.dumps(malformed), json.dumps(unsupported)]
    (root / "artifacts.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")

    payload = import_pm_crypto_updown_real_cached_artifacts(import_root=root, output_root=tmp_path)

    assert payload["schema_version"] == "pm_crypto_updown_real_cached_import_v1"
    assert payload["accepted_artifact_count"] == len(original_lines)
    assert payload["dedupe_dropped_artifact_count"] == 1
    assert payload["rejected_artifact_count"] == 2
    assert payload["rejected_by_reason"]["MISSING_TIMESTAMP"] == 1
    assert payload["rejected_by_reason"]["UNSUPPORTED_CAPTURE_MODE"] == 1
    assert payload["imported_replay_ready_row_count"] == 4
    assert payload["real_cached_replay_ready_row_count"] == 4
    assert payload["source_mode_counts"]["local_import"] == len(original_lines)
    assert payload["normalized_source"]["source_quality"] == "real_cached"
    assert (tmp_path / "reports" / "sequence39" / "real_cached_import" / "latest_real_cached_import.json").exists()


def test_sequence39_dataset_rebuild_adds_real_cached_rows_without_synthetic_inflation() -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_dataset_builder import (
        build_pm_crypto_updown_expanded_dataset,
    )

    payload = build_pm_crypto_updown_expanded_dataset(
        fixture_root=FIXTURE_ROOT,
        real_cached_artifact_roots=[REAL_CACHED_SAMPLE_ROOT],
    )

    assert payload["schema_version"] == "pm_crypto_updown_expanded_dataset_v1"
    assert payload["phase38_primary_evidence_row_count"] == 6
    assert payload["primary_evidence_row_count"] == 10
    assert payload["real_cached_row_count"] == 4
    assert payload["real_cached_replay_ready_row_count"] == 4
    assert payload["rows_needed_for_threshold"] == 10
    assert payload["source_quality_counts"]["real_cached"] == 4
    assert payload["source_quality_counts"]["synthetic_stress"] == 2
    assert all(row["source_quality"] != "synthetic_stress" for row in payload["primary_rows"])
    assert all("REAL_CACHED_SAMPLE_FIXTURE" in row["data_quality_flags"] for row in payload["real_cached_rows"])


def test_sequence39_threshold_progress_reports_gap_and_bottleneck(local_project: Path) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_threshold_progress import (
        write_pm_crypto_updown_threshold_progress_report,
    )

    payload = write_pm_crypto_updown_threshold_progress_report(
        fixture_root=FIXTURE_ROOT,
        real_cached_artifact_roots=[REAL_CACHED_SAMPLE_ROOT],
        output_root=local_project,
    )

    assert payload["schema_version"] == "pm_crypto_updown_threshold_progress_v1"
    assert payload["previous_primary_row_count"] == 6
    assert payload["current_primary_row_count"] == 10
    assert payload["current_real_cached_row_count"] == 4
    assert payload["target_primary_row_count"] == 20
    assert payload["row_gap"] == 10
    assert payload["primary_rows_moved_toward_20"] is True
    assert payload["threshold_status"] == "PRIMARY_EVIDENCE_EXPANDED"
    assert payload["readiness_status"] == "PRIMARY_EVIDENCE_STILL_TOO_THIN"
    assert payload["source_bottleneck"] == "real_cached_rows"
    assert "PRIMARY_ROWS_10_LT_20" in payload["blockers"]
    assert "pm-crypto-updown-capture-plan" in payload["next_operator_action"]
    assert (local_project / "reports" / "sequence39" / "threshold_progress" / "latest_threshold_progress.json").exists()


def test_sequence39_replay_eval_and_readiness_remain_blocked_below_threshold(
    local_project: Path,
) -> None:
    from quant_os.readiness.real_cached_replay_readiness_report import (
        write_real_cached_replay_readiness_report,
    )
    from quant_os.research.replay_candidates.pm_crypto_updown_real_cached_replay_eval import (
        write_pm_crypto_updown_real_cached_replay_eval_report,
    )

    evaluation = write_pm_crypto_updown_real_cached_replay_eval_report(
        fixture_root=FIXTURE_ROOT,
        real_cached_artifact_roots=[REAL_CACHED_SAMPLE_ROOT],
        output_root=local_project,
    )
    readiness = write_real_cached_replay_readiness_report(
        real_cached_replay_eval=evaluation,
        output_root=local_project,
    )

    assert evaluation["schema_version"] == "pm_crypto_updown_real_cached_replay_eval_v1"
    assert evaluation["primary_result"]["row_count"] == 10
    assert evaluation["real_cached_result"]["row_count"] == 4
    assert evaluation["fixture_diagnostic_result"]["row_count"] == 8
    assert evaluation["synthetic_stress_result"]["row_count"] == 2
    assert evaluation["synthetic_rows_counted_as_primary"] is False
    assert "PRIMARY_ROWS_10_LT_20" in evaluation["readiness_blockers"]
    assert readiness["schema_version"] == "real_cached_replay_readiness_v1"
    assert readiness["readiness_status"] == "PRIMARY_EVIDENCE_STILL_TOO_THIN"
    assert readiness["ready_for_expanded_shadow_replay"] is False
    assert readiness["live_readiness_claimed"] is False
    assert readiness["canary_readiness_claimed"] is False
    assert readiness["live_trading_enabled"] is False
    assert readiness["execution_authority"] == "NONE"
    assert readiness["autonomy_milestones"]["real_cached_evidence_acquisition"] == "partial"
    assert readiness["autonomy_milestones"]["expanded_shadow_replay"] == "blocked"


def test_sequence39_cli_commands_are_fixture_safe_and_non_executing(local_project: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = {
        **os.environ,
        "PYTHONPATH": str(repo_root / "src"),
    }
    commands = [
        [sys.executable, "-m", "quant_os.cli", "data", "pm-crypto-updown-capture-plan"],
        [
            sys.executable,
            "-m",
            "quant_os.cli",
            "data",
            "pm-crypto-updown-real-cached-import",
            "--import-root",
            str(REAL_CACHED_SAMPLE_ROOT),
        ],
        [
            sys.executable,
            "-m",
            "quant_os.cli",
            "research",
            "pm-crypto-updown-threshold-progress",
            "--real-cached-root",
            str(REAL_CACHED_SAMPLE_ROOT),
        ],
        [
            sys.executable,
            "-m",
            "quant_os.cli",
            "research",
            "pm-crypto-updown-real-cached-replay-eval",
            "--real-cached-root",
            str(REAL_CACHED_SAMPLE_ROOT),
        ],
        [
            sys.executable,
            "-m",
            "quant_os.cli",
            "readiness",
            "real-cached-replay-readiness",
            "--real-cached-root",
            str(REAL_CACHED_SAMPLE_ROOT),
        ],
        [sys.executable, "-m", "quant_os.cli", "guard-live"],
        [sys.executable, "-m", "quant_os.cli", "freqtrade", "validate"],
    ]

    for command in commands:
        cwd = repo_root if command[3:5] == ["freqtrade", "validate"] else local_project
        result = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        assert "live_trading_enabled" in result.stdout or "guard" in result.stdout or "passed" in result.stdout
        assert "False" in result.stdout or "True" in result.stdout
        if "guard-live" not in command and "validate" not in command:
            assert "execution_authority" in result.stdout
            assert "NONE" in result.stdout


def test_sequence39_modules_do_not_add_auth_signing_order_cancel_or_evasion_paths() -> None:
    source_paths = [
        Path("src/quant_os/data/prediction_markets/pm_updown_real_cached_capture.py"),
        Path("src/quant_os/research/replay_candidates/real_cached_artifact_models.py"),
        Path("src/quant_os/research/replay_candidates/pm_crypto_updown_real_cached_import.py"),
        Path("src/quant_os/research/replay_candidates/pm_crypto_updown_threshold_progress.py"),
        Path("src/quant_os/research/replay_candidates/pm_crypto_updown_real_cached_replay_eval.py"),
        Path("src/quant_os/readiness/real_cached_replay_readiness.py"),
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
