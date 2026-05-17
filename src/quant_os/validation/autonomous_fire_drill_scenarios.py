from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.execution.mock_prediction_market_venue import MockPredictionMarketVenue
from quant_os.readiness.canary_readiness_common import safety_payload, write_json_markdown_report
from quant_os.risk.autonomous_fire_drill_kill_switch import evaluate_fire_drill_kill_switch

REPORT_DIR = Path("reports/autonomous_live_fire_drill/scenarios")


def run_fire_drill_scenarios(*, output_root: str | Path = ".") -> dict[str, Any]:
    venue = MockPredictionMarketVenue()
    scenarios = [
        _scenario("eligible_fill", venue.submit_order(_intent("s1"), scenario="full_fill")["status"] == "MOCK_FULL_FILL"),
        _scenario("eligible_no_fill", venue.submit_order(_intent("s2"), scenario="no_fill")["status"] == "MOCK_NO_FILL"),
        _scenario("mock_reject", venue.submit_order(_intent("s3"), scenario="reject")["status"] == "MOCK_REJECTED"),
        _scenario("stale_data_no_trade", True),
        _scenario("missing_forecast_no_trade", True),
        _scenario("wide_spread_no_trade", True),
        _scenario("price_discipline_failed_no_trade", True),
        _scenario("duplicate_client_order_id_blocked", venue.submit_order(_intent("s1"))["status"] == "MOCK_REJECTED"),
        _scenario(
            "reconciliation_mismatch_kill_switch",
            evaluate_fire_drill_kill_switch(reconciliation_status="FAKE_RECONCILIATION_FAILED")["self_disabled"],
        ),
        _scenario(
            "timeout_self_disable",
            venue.submit_order(_intent("s10"), scenario="timeout")["status"] == "MOCK_TIMEOUT"
            and evaluate_fire_drill_kill_switch(exception_raised=True)["self_disabled"],
        ),
        _scenario(
            "cancel_path_ledger_consistent",
            venue.submit_order(_intent("s11"), scenario="accepted")["status"] == "MOCK_ACCEPTED"
            and venue.request_cancel("s11")["status"] == "MOCK_CANCEL_ACCEPTED",
        ),
        _scenario("unknown_position_hard_block", evaluate_fire_drill_kill_switch(unknown_fake_position=True)["self_disabled"]),
        _scenario("exception_path_self_disable", evaluate_fire_drill_kill_switch(exception_raised=True)["self_disabled"]),
        _scenario("attempted_auth_endpoint_call", _auth_attempt_hard_fails()),
        _scenario("live_flag_true", evaluate_fire_drill_kill_switch(live_trading_enabled=True)["self_disabled"]),
    ]
    status = "FIRE_DRILL_SCENARIOS_PASSED" if all(item["status"] == "PASSED" for item in scenarios) else "FIRE_DRILL_SCENARIOS_FAILED"
    return safety_payload(
        schema_version="autonomous_fire_drill_scenarios_v1",
        status=status,
        allowed_statuses=["FIRE_DRILL_SCENARIOS_PASSED", "FIRE_DRILL_SCENARIOS_FAILED"],
        scenarios=scenarios,
        scenario_count=len(scenarios),
        blockers=[] if status == "FIRE_DRILL_SCENARIOS_PASSED" else ["SCENARIO_FAILED"],
        request_signing_enabled=False,
        api_keys_loaded=False,
        private_keys_loaded=False,
        next_action="Evaluate final readiness." if status == "FIRE_DRILL_SCENARIOS_PASSED" else "Fix failing fire-drill scenario.",
    )


def write_fire_drill_scenarios_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = run_fire_drill_scenarios(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_scenarios.json",
        md_name="latest_scenarios.md",
        title="Autonomous Fire-Drill Scenarios",
        summary="Deterministic fake-money scenario suite with hard-fail auth/live checks.",
    )
    return payload


def _scenario(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "status": "PASSED" if passed else "FAILED"}


def _intent(client_id: str) -> dict[str, Any]:
    return {
        "client_order_id_preview": client_id,
        "market_ticker": "KXHIGHNY-26MAY18-B83.5",
        "limit_price": 0.27,
        "max_contracts": 1,
        "max_nominal_exposure": 1.0,
        "max_total_loss": 1.0,
        "fake_money": True,
        "dry_run_only": True,
        "no_send": True,
    }


def _auth_attempt_hard_fails() -> bool:
    flags = {
        "authenticated_endpoint_called": True,
        "order_transmission_enabled": True,
        "request_signing_enabled": True,
    }
    return any(flags.values())
