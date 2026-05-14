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
        run_id="pm_crypto_updown_manual_001",
    )
    return root / payload["run_root"]


def test_sequence40_manifest_only_manual_run_is_not_a_malformed_artifact(
    tmp_path: Path,
) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_real_cached_import import (
        import_pm_crypto_updown_real_cached_artifacts,
    )

    manual_root = _write_manifest_only_run(tmp_path)

    payload = import_pm_crypto_updown_real_cached_artifacts(
        import_root=manual_root,
        output_root=tmp_path,
    )

    assert payload["import_status"] == "REAL_CACHED_CAPTURE_READY"
    assert payload["accepted_artifact_count"] == 0
    assert payload["rejected_artifact_count"] == 0
    assert payload["rejected_by_reason"] == {}
    assert payload["real_cached_rows_imported"] == 0


def test_sequence40_threshold_progress_combines_roots_and_reports_precise_source_coverage(
    tmp_path: Path,
) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_threshold_progress import (
        write_pm_crypto_updown_threshold_progress_report,
    )

    manual_root = _write_manifest_only_run(tmp_path)

    payload = write_pm_crypto_updown_threshold_progress_report(
        fixture_root=FIXTURE_ROOT,
        real_cached_artifact_roots=[REAL_CACHED_SAMPLE_ROOT, manual_root],
        output_root=tmp_path,
    )

    coverage = payload["source_coverage"]
    manual_summary = next(
        item for item in coverage["real_cached_roots"] if item["import_root"].endswith("pm_crypto_updown_manual_001")
    )

    assert payload["current_primary_row_count"] == 10
    assert payload["current_real_cached_row_count"] == 4
    assert payload["row_gap"] == 10
    assert payload["readiness_status"] == "PRIMARY_EVIDENCE_STILL_TOO_THIN"
    assert coverage["coverage_status"] == "REAL_CACHED_SOURCE_COVERAGE_INCOMPLETE"
    assert coverage["additional_primary_rows_needed"] == 10
    assert coverage["additional_two_token_windows_needed_estimate"] == 5
    assert coverage["accepted_artifact_count"] == 12
    assert coverage["real_cached_replay_ready_row_count"] == 4
    assert manual_summary["accepted_artifact_count"] == 0
    assert manual_summary["coverage_status"] == "NO_REPLAY_ARTIFACTS_FOUND"
    assert manual_summary["missing_replay_artifact_types"] == [
        "pm_clob_snapshot",
        "pm_market_window",
        "pm_window_label_or_pm_resolution_label",
        "spot_snapshot_or_spot_candle",
    ]
    assert "SOURCE_COVERAGE_REAL_CACHED_ROWS_4_LT_REQUIRED_14" in payload["blockers"]


def test_sequence40_cli_accepts_multiple_real_cached_roots(
    tmp_path: Path,
    local_project: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    manual_root = _write_manifest_only_run(tmp_path)
    env = {
        **os.environ,
        "PYTHONPATH": str(repo_root / "src"),
    }

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "quant_os.cli",
            "research",
            "pm-crypto-updown-threshold-progress",
            "--real-cached-root",
            str(REAL_CACHED_SAMPLE_ROOT),
            "--real-cached-root",
            str(manual_root),
        ],
        cwd=local_project,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "'current_primary_row_count': 10" in result.stdout
    assert "'current_real_cached_row_count': 4" in result.stdout
    assert "'row_gap': 10" in result.stdout


def test_sequence40_make_target_exists_and_runs_read_only_blocker_flow() -> None:
    make_cmd = Path("make.cmd").read_text(encoding="utf-8")

    assert 'if "%TARGET%"=="sequence40-smoke"' in make_cmd
    assert "pm-crypto-updown-capture-plan --manual-network-ok --run-id pm_crypto_updown_manual_001" in make_cmd
    assert "tests/test_sequence40_real_cached_replay_threshold.py" in make_cmd


def test_sequence40_blocker_report_is_written_with_source_coverage(
    tmp_path: Path,
) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_threshold_progress import (
        write_pm_crypto_updown_threshold_progress_report,
    )

    manual_root = _write_manifest_only_run(tmp_path)
    payload = write_pm_crypto_updown_threshold_progress_report(
        fixture_root=FIXTURE_ROOT,
        real_cached_artifact_roots=[REAL_CACHED_SAMPLE_ROOT, manual_root],
        output_root=tmp_path,
    )

    report_path = tmp_path / payload["report_paths"]["json"]
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["source_coverage"]["coverage_status"] == "REAL_CACHED_SOURCE_COVERAGE_INCOMPLETE"
    assert report["source_coverage"]["additional_primary_rows_needed"] == 10
    assert report["phase40_can_run_expanded_shadow_replay"] is False
