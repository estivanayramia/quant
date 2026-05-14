from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

BENCHMARK_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "benchmark_sources"
POLYMARKET_SNAPSHOT = BENCHMARK_FIXTURE_ROOT / "polymarket_public_snapshot.json"
PMXT_MANIFEST = BENCHMARK_FIXTURE_ROOT / "pmxt_manifest.json"
REFERENCE_DATASETS = BENCHMARK_FIXTURE_ROOT / "reference_datasets_manifest.json"


def test_sequence33_shadow_windows_are_deterministic_and_label_synthetic_stress(
    local_project: Path,
) -> None:
    from quant_os.proving.shadow_window_report import write_shadow_window_report

    first = write_shadow_window_report(
        output_root=local_project,
        polymarket_snapshot_path=POLYMARKET_SNAPSHOT,
        pmxt_manifest_path=PMXT_MANIFEST,
        reference_datasets_manifest_path=REFERENCE_DATASETS,
    )
    second = write_shadow_window_report(
        output_root=local_project,
        polymarket_snapshot_path=POLYMARKET_SNAPSHOT,
        pmxt_manifest_path=PMXT_MANIFEST,
        reference_datasets_manifest_path=REFERENCE_DATASETS,
    )

    assert first["schema_version"] == "shadow_sample_windows_v1"
    assert first["windows"] == second["windows"]
    assert first["total_window_count"] >= 5
    assert first["proving_effective_window_count"] == 1
    assert first["evidence_class_counts"]["fixture_evidence"] == 1
    assert first["evidence_class_counts"]["real_cached_evidence"] == 0
    assert first["evidence_class_counts"]["synthetic_stress"] >= 4
    assert all(window["provenance"]["source_id"] for window in first["windows"])
    synthetic_windows = [
        window for window in first["windows"] if window["evidence_class"] == "synthetic_stress"
    ]
    assert synthetic_windows
    assert all(window["counts_for_proving_thresholds"] is False for window in synthetic_windows)
    assert all(window["profitability_evidence"] is False for window in synthetic_windows)
    assert first["live_trading_enabled"] is False
    assert first["execution_authority"] == "NONE"
    assert (
        local_project
        / "reports"
        / "sequence33"
        / "shadow_samples"
        / "latest_shadow_windows.json"
    ).exists()


def test_sequence33_blocker_attribution_is_stable_and_distinguishes_fixability(
    local_project: Path,
) -> None:
    from quant_os.proving.shadow_blocker_report import write_shadow_blocker_report

    first = write_shadow_blocker_report(
        output_root=local_project,
        polymarket_snapshot_path=POLYMARKET_SNAPSHOT,
        pmxt_manifest_path=PMXT_MANIFEST,
        reference_datasets_manifest_path=REFERENCE_DATASETS,
    )
    second = write_shadow_blocker_report(
        output_root=local_project,
        polymarket_snapshot_path=POLYMARKET_SNAPSHOT,
        pmxt_manifest_path=PMXT_MANIFEST,
        reference_datasets_manifest_path=REFERENCE_DATASETS,
    )

    assert first["schema_version"] == "shadow_blocker_attribution_v1"
    assert first["blocker_sources"] == second["blocker_sources"]
    assert "confidence_too_weak" in first["blocker_sources"]
    assert "replay_input_insufficient" in first["blocker_sources"]
    assert "risk_envelope" in first["blocker_sources"]
    assert "sample_too_thin" in first["blocker_sources"]
    assert "signal_edge_blockers" in first["blocker_groups"]
    assert "data_replay_blockers" in first["blocker_groups"]
    assert "risk_policy_blockers" in first["blocker_groups"]
    assert "fixture_artifact_blockers" in first["blocker_groups"]
    assert "replay_input_insufficient" in first["fixability"]["fixable_by_better_data"]
    assert "confidence_too_weak" in first["fixability"]["genuine_do_not_trade_blockers"]
    assert first["live_trading_enabled"] is False
    assert first["prediction_market_execution_authority_added"] is False


def test_sequence33_sensitivity_keeps_blocked_state_under_conservative_variants(
    local_project: Path,
) -> None:
    from quant_os.proving.shadow_sensitivity_report import write_shadow_sensitivity_report

    payload = write_shadow_sensitivity_report(
        output_root=local_project,
        polymarket_snapshot_path=POLYMARKET_SNAPSHOT,
        pmxt_manifest_path=PMXT_MANIFEST,
        reference_datasets_manifest_path=REFERENCE_DATASETS,
    )

    assert payload["schema_version"] == "shadow_sensitivity_v1"
    assert payload["blocked_state_robust_across_assumptions"] is True
    assert payload["optimistic_assumptions_rewarded"] is False
    assert len(payload["variants"]) >= 6
    assert all(variant["accepted_for_unblocking"] is False for variant in payload["variants"])
    assert any(variant["too_lenient_flag"] is True for variant in payload["variants"])
    assert {
        "latency_penalty",
        "stale_book_penalty",
        "max_fill_fraction",
        "spread_tolerance",
        "minimum_confidence",
        "max_exposure",
    }.issubset(payload["varied_assumptions"])
    assert payload["live_trading_enabled"] is False
    assert payload["execution_authority"] == "NONE"


def test_sequence33_unblockability_stays_blocked_when_real_evidence_is_thin(
    local_project: Path,
) -> None:
    from quant_os.proving.unblockability_report import write_unblockability_report

    payload = write_unblockability_report(
        output_root=local_project,
        polymarket_snapshot_path=POLYMARKET_SNAPSHOT,
        pmxt_manifest_path=PMXT_MANIFEST,
        reference_datasets_manifest_path=REFERENCE_DATASETS,
    )

    assert payload["schema_version"] == "shadow_unblockability_v1"
    assert payload["unblockability_status"] == "BLOCKED_BY_THIN_EVIDENCE"
    assert payload["ready_for_bounded_shadow_rehearsal"] is False
    assert payload["synthetic_stress_not_profitability_evidence"] is True
    assert payload["real_or_fixture_effective_window_count"] == 1
    assert "BLOCKED_BY_SIGNAL_WEAKNESS" in payload["secondary_blockers"]
    assert "BLOCKED_BY_REPLAY_REALISM" in payload["secondary_blockers"]
    assert "BLOCKED_BY_RISK_POLICY" in payload["secondary_blockers"]
    assert payload["hidden_live_authority_detected"] is False
    assert payload["live_trading_enabled"] is False


def test_sequence33_shadow_rehearsal_readiness_does_not_promote_weak_evidence(
    local_project: Path,
) -> None:
    from quant_os.readiness.shadow_rehearsal_report import write_shadow_rehearsal_report

    payload = write_shadow_rehearsal_report(
        output_root=local_project,
        polymarket_snapshot_path=POLYMARKET_SNAPSHOT,
        pmxt_manifest_path=PMXT_MANIFEST,
        reference_datasets_manifest_path=REFERENCE_DATASETS,
    )

    assert payload["schema_version"] == "shadow_rehearsal_readiness_v1"
    assert payload["shadow_rehearsal_status"] == "SHADOW_EVIDENCE_TOO_THIN"
    assert payload["ready_for_bounded_shadow_rehearsal"] is False
    assert payload["ready_for_live_trading"] is False
    assert "shadow_evidence_too_thin" in payload["blockers"]
    assert "unresolved_replay_realism" in payload["blockers"]
    assert "weak_signal_evidence" in payload["blockers"]
    assert payload["execution_authority"] == "NONE"


def test_sequence33_cli_commands_are_fixture_safe_and_non_executing(
    local_project: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = {
        **os.environ,
        "PYTHONPATH": str(repo_root / "src"),
    }
    commands = [
        [sys.executable, "-m", "quant_os.cli", "proving", "shadow-sample-windows"],
        [sys.executable, "-m", "quant_os.cli", "proving", "shadow-blocker-attribution"],
        [sys.executable, "-m", "quant_os.cli", "proving", "shadow-sensitivity"],
        [sys.executable, "-m", "quant_os.cli", "proving", "unblockability"],
        [sys.executable, "-m", "quant_os.cli", "readiness", "shadow-rehearsal"],
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


def test_sequence33_modules_do_not_expose_live_order_authority() -> None:
    source_paths = [
        Path("src/quant_os/proving/shadow_sample_expansion.py"),
        Path("src/quant_os/proving/shadow_window_report.py"),
        Path("src/quant_os/proving/shadow_blocker_attribution.py"),
        Path("src/quant_os/proving/shadow_blocker_report.py"),
        Path("src/quant_os/proving/shadow_sensitivity.py"),
        Path("src/quant_os/proving/shadow_sensitivity_report.py"),
        Path("src/quant_os/proving/unblockability.py"),
        Path("src/quant_os/proving/unblockability_report.py"),
        Path("src/quant_os/readiness/shadow_rehearsal_report.py"),
    ]
    forbidden_tokens = [
        "create_order",
        "cancel_order",
        "post_order",
        "private_key",
        "wallet_signer",
        "sign_order",
    ]

    for path in source_paths:
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        for token in forbidden_tokens:
            assert token not in lowered
