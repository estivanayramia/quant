from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

BENCHMARK_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "benchmark_sources"
POLYMARKET_SNAPSHOT = BENCHMARK_FIXTURE_ROOT / "polymarket_public_snapshot.json"
PMXT_MANIFEST = BENCHMARK_FIXTURE_ROOT / "pmxt_manifest.json"
REFERENCE_DATASETS = BENCHMARK_FIXTURE_ROOT / "reference_datasets_manifest.json"


def test_sequence32_shadow_proving_spec_is_deterministic_and_conservative(
    local_project: Path,
) -> None:
    from quant_os.proving.shadow_proving_spec import write_shadow_proving_spec_report

    first = write_shadow_proving_spec_report(output_root=local_project)
    second = write_shadow_proving_spec_report(output_root=local_project)

    assert first["schema_version"] == "shadow_proving_spec_v1"
    assert first["thresholds"] == second["thresholds"]
    assert first["thresholds"]["minimum_shadow_windows"] >= 5
    assert first["thresholds"]["minimum_total_intents"] >= 30
    assert first["thresholds"]["maximum_blocked_trade_ratio"] == "0.35"
    assert first["thresholds"]["minimum_fill_rate"] == "0.05"
    assert first["thresholds"]["maximum_fill_rate"] == "0.50"
    assert first["thresholds"]["maximum_expectancy_degradation_ratio"] == "0.25"
    assert "all_intents_blocked" in first["instant_fail_conditions"]
    assert "unresolved_realism_disqualifier" in first["instant_fail_conditions"]
    assert first["live_trading_enabled"] is False
    assert first["execution_authority"] == "NONE"
    assert (
        local_project
        / "reports"
        / "sequence32"
        / "shadow_proving"
        / "latest_shadow_proving_spec.json"
    ).exists()


def test_sequence32_shadow_proving_blocks_thin_or_fragile_shadow_samples(
    local_project: Path,
) -> None:
    from quant_os.proving.shadow_proving_report import write_shadow_proving_report

    payload = write_shadow_proving_report(
        output_root=local_project,
        polymarket_snapshot_path=POLYMARKET_SNAPSHOT,
        pmxt_manifest_path=PMXT_MANIFEST,
        reference_datasets_manifest_path=REFERENCE_DATASETS,
    )

    assert payload["shadow_proving_status"] == "SHADOW_PROVING_TOO_THIN"
    assert payload["ready_for_tiny_canary_consideration"] is False
    assert payload["aggregate_metrics"]["window_count"] == 1
    assert payload["aggregate_metrics"]["total_intent_count"] == 1
    assert payload["aggregate_metrics"]["blocked_trade_ratio"] == "1"
    assert payload["aggregate_metrics"]["fill_rate"] == "0"
    assert "SHADOW_SAMPLE_TOO_THIN" in payload["blockers"]
    assert "RISK_BLOCKS_CANARY_CONSIDERATION" in payload["blockers"]
    assert "WEAK_EVIDENCE_BLOCKS_PROMOTION" in payload["blockers"]
    assert payload["live_trading_enabled"] is False
    assert payload["prediction_market_execution_authority_added"] is False


def test_sequence32_canary_preconditions_fail_closed_by_default(
    local_project: Path,
) -> None:
    from quant_os.readiness.canary_preconditions_report import (
        write_canary_preconditions_report,
    )

    payload = write_canary_preconditions_report(
        output_root=local_project,
        polymarket_snapshot_path=POLYMARKET_SNAPSHOT,
        pmxt_manifest_path=PMXT_MANIFEST,
        reference_datasets_manifest_path=REFERENCE_DATASETS,
    )

    assert payload["canary_preconditions_status"] == "CANARY_PRECONDITIONS_NOT_MET"
    assert payload["ready_for_tiny_canary_consideration"] is False
    assert payload["manual_enablement_required"] is True
    assert payload["manual_enablement_present"] is False
    assert payload["tiny_nominal_capital_only"]["max_nominal_usd"] == "10"
    assert payload["hard_max_order_count"] == 1
    assert payload["hard_max_exposure_usd"] == "10"
    assert payload["dry_run_parity_required"] is True
    assert payload["reconciliation_required"] is True
    assert payload["shadow_proving_thresholds_met"] is False
    assert payload["no_unresolved_realism_disqualifier"] is False
    assert "shadow_proving_not_ready" in payload["still_blocked_reasons"]
    assert "manual_enablement_absent" in payload["still_blocked_reasons"]
    assert payload["live_trading_enabled"] is False
    assert payload["execution_authority"] == "NONE"


def test_sequence32_canary_blocker_report_is_truthful_and_stable(
    local_project: Path,
) -> None:
    from quant_os.readiness.canary_blockers_report import write_canary_blockers_report

    first = write_canary_blockers_report(
        output_root=local_project,
        polymarket_snapshot_path=POLYMARKET_SNAPSHOT,
        pmxt_manifest_path=PMXT_MANIFEST,
        reference_datasets_manifest_path=REFERENCE_DATASETS,
    )
    second = write_canary_blockers_report(
        output_root=local_project,
        polymarket_snapshot_path=POLYMARKET_SNAPSHOT,
        pmxt_manifest_path=PMXT_MANIFEST,
        reference_datasets_manifest_path=REFERENCE_DATASETS,
    )

    assert first["canary_blocker_status"] == "TINY_CANARY_BLOCKED"
    assert first["still_blocked"] is True
    assert first["not_almost_ready"] is True
    assert first["blocker_categories"] == second["blocker_categories"]
    assert "edge_weakness" in first["blocker_categories"]
    assert "replay_realism_gaps" in first["blocker_categories"]
    assert "fill_uncertainty" in first["blocker_categories"]
    assert "shadow_sample_too_thin" in first["blocker_categories"]
    assert "risk_envelope_blocks" in first["blocker_categories"]
    assert first["live_trading_enabled"] is False
    assert first["prediction_market_execution_authority_added"] is False


def test_sequence32_cli_commands_are_fixture_safe_and_non_executing(
    local_project: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = {
        **os.environ,
        "PYTHONPATH": str(repo_root / "src"),
    }
    commands = [
        [sys.executable, "-m", "quant_os.cli", "proving", "shadow-proving-report"],
        [sys.executable, "-m", "quant_os.cli", "readiness", "canary-preconditions"],
        [sys.executable, "-m", "quant_os.cli", "readiness", "canary-blockers"],
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


def test_sequence32_modules_do_not_expose_live_order_authority() -> None:
    source_paths = [
        Path("src/quant_os/proving/shadow_proving_spec.py"),
        Path("src/quant_os/proving/shadow_proving_report.py"),
        Path("src/quant_os/proving/shadow_proving_eval.py"),
        Path("src/quant_os/readiness/canary_preconditions_report.py"),
        Path("src/quant_os/readiness/canary_blockers_report.py"),
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
