from __future__ import annotations

from pathlib import Path

from quant_os.validation.runner import list_scenarios, run_scenario


def test_sequence2_validation_scenarios_are_registered() -> None:
    scenario_ids = {scenario.scenario_id for scenario in list_scenarios()}

    assert {
        "walk_forward_degradation_blocks",
        "dry_run_expectancy_collapse_downgrades",
        "liquidity_too_weak_blocks",
        "stale_book_blocks",
        "replay_dry_run_divergence_not_ready",
        "edge_concentrated_unstable_window_warns",
        "calibration_drift_reduces_size",
    }.issubset(scenario_ids)


def test_sequence2_scenarios_block_or_warn_with_reason_codes(tmp_path: Path) -> None:
    walk_forward = run_scenario("walk_forward_degradation_blocks", output_root=tmp_path)
    liquidity = run_scenario("liquidity_too_weak_blocks", output_root=tmp_path)
    drift = run_scenario("replay_dry_run_divergence_not_ready", output_root=tmp_path)
    calibration = run_scenario("calibration_drift_reduces_size", output_root=tmp_path)

    assert walk_forward.status == "PASS"
    assert walk_forward.action == "BLOCK"
    assert "EDGE_DEGRADATION" in walk_forward.reason_codes
    assert liquidity.blocked_correctly is True
    assert "LIQUIDITY_TOO_WEAK" in liquidity.reason_codes
    assert drift.action == "BLOCK"
    assert "REPLAY_DRY_RUN_DRIFT_TOO_HIGH" in drift.reason_codes
    assert calibration.action == "SIZE_REDUCED"
    assert calibration.metrics["size_multiplier"] < 1.0
    assert (
        tmp_path
        / "reports"
        / "validation"
        / "scenarios"
        / "walk_forward_degradation_blocks.json"
    ).exists()
