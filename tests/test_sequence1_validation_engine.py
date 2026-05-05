from __future__ import annotations

from pathlib import Path

from quant_os.validation.runner import list_scenarios, run_all_scenarios, run_scenario


def test_validation_scenarios_cover_required_sequence1_behaviors() -> None:
    scenario_ids = {scenario.scenario_id for scenario in list_scenarios()}

    assert {
        "no_edge_no_trade",
        "negative_edge_no_trade",
        "stale_data_block",
        "corrupted_data_block",
        "reconciliation_mismatch_block",
        "kill_switch_hard_stop",
        "latency_mismatch_degrade_or_block",
        "partial_fill_state_handling",
        "symbol_cap_breach_hard_fail",
        "missing_explanation_validation_fail",
    }.issubset(scenario_ids)


def test_no_edge_stale_data_and_kill_switch_scenarios_block_correctly(tmp_path: Path) -> None:
    no_edge = run_scenario("no_edge_no_trade", output_root=tmp_path)
    stale = run_scenario("stale_data_block", output_root=tmp_path)
    kill = run_scenario("kill_switch_hard_stop", output_root=tmp_path)

    assert no_edge.status == "PASS"
    assert no_edge.action == "NO_TRADE"
    assert stale.blocked_correctly is True
    assert kill.unsafe_action_count == 0
    assert kill.action == "HARD_STOP"


def test_partial_fill_and_missing_explanation_validation(tmp_path: Path) -> None:
    partial = run_scenario("partial_fill_state_handling", output_root=tmp_path)
    missing = run_scenario("missing_explanation_validation_fail", output_root=tmp_path)

    assert partial.status == "PASS"
    assert partial.metrics["open_quantity"] == 0.5
    assert missing.status == "FAIL"
    assert missing.unsafe_action_count == 1
    assert "MISSING_REASON_CODE" in missing.reason_codes


def test_validation_reports_and_summary_are_generated(tmp_path: Path) -> None:
    summary = run_all_scenarios(output_root=tmp_path)

    assert summary["unsafe_action_failure_count"] >= 1
    assert summary["blocked_correctly_count"] >= 6
    assert summary["autonomy_health"]["live_trading_enabled"] is False
    assert (tmp_path / "reports" / "validation" / "latest_summary.json").exists()
    assert (tmp_path / "reports" / "validation" / "latest_summary.md").exists()
    assert (tmp_path / "reports" / "validation" / "scenarios" / "no_edge_no_trade.json").exists()
    assert (tmp_path / "reports" / "validation" / "scenarios" / "no_edge_no_trade.md").exists()
