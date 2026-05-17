from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

NOW = "2026-05-17T21:00:00Z"
FRESH_TS = "2026-05-17T20:59:00Z"
STALE_TS = "2026-05-17T20:40:00Z"


def _write_json(root: Path, relative: str, payload: dict[str, Any]) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _market(**overrides: Any) -> dict[str, Any]:
    payload = {
        "candidate_id": "pm_weather_forecast_market_mismatch",
        "venue": "kalshi",
        "ticker": "KXHIGHNY-26MAY18-B83.5",
        "event_ticker": "KXHIGHNY-26MAY18",
        "series_ticker": "KXHIGHNY",
        "title": "Will the high temp in NYC be 83-84 deg on May 18, 2026?",
        "status": "active",
        "threshold_bucket": "83_to_84_f_inclusive",
        "yes_bid": 0.25,
        "yes_ask": 0.27,
        "no_bid": 0.73,
        "no_ask": 0.75,
        "spread": 0.02,
        "liquidity": 12.0,
        "orderbook_ts": FRESH_TS,
        "market_evidence_hash": "market-hash",
        "resolution_ts": "2026-05-19T14:00:00Z",
    }
    payload.update(overrides)
    return payload


def _forecast(**overrides: Any) -> dict[str, Any]:
    payload = {
        "status": "CURRENT_FORECAST_MATCHED",
        "source_id": "nws_api",
        "source_kind": "forecast",
        "forecast_issue_ts": "2026-05-17T20:55:00Z",
        "forecast_valid_ts": "2026-05-18T14:00:00-04:00",
        "known_at_ts": "2026-05-17T20:55:00Z",
        "forecast_value": 83,
        "forecast_bucket": "83_to_84_f_inclusive",
        "bucket_match": True,
        "evidence_hash": "forecast-hash",
    }
    payload.update(overrides)
    return payload


def _decision(*, status: str = "AUTONOMOUS_DECISION_READY") -> dict[str, Any]:
    return {
        "status": status,
        "decision": "PAPER_ORDER_INTENT" if status == "AUTONOMOUS_DECISION_READY" else "NO_TRADE",
        "candidate_id": "pm_weather_forecast_market_mismatch",
        "market_ticker": "KXHIGHNY-26MAY18-B83.5",
        "side": "yes",
        "action": "buy",
        "limit_price": 0.27,
        "max_contracts": 1,
        "max_nominal_exposure": 1.0,
        "max_total_loss": 1.0,
        "reason_code": "ELIGIBLE_FIRE_DRILL_MARKET",
        "forecast_evidence_hash": "forecast-hash",
        "market_evidence_hash": "market-hash",
        "client_order_id_preview": "fd_co_1",
        "blockers": [] if status == "AUTONOMOUS_DECISION_READY" else ["NO_TRADE"],
        "live_trading_enabled": False,
        "execution_authority": "NONE",
    }


def _intent() -> dict[str, Any]:
    return {
        "candidate_id": "pm_weather_forecast_market_mismatch",
        "market_ticker": "KXHIGHNY-26MAY18-B83.5",
        "side": "yes",
        "action": "buy",
        "limit_price": 0.27,
        "max_contracts": 1,
        "max_nominal_exposure": 1.0,
        "max_total_loss": 1.0,
        "reason_code": "ELIGIBLE_FIRE_DRILL_MARKET",
        "forecast_evidence_hash": "forecast-hash",
        "market_evidence_hash": "market-hash",
        "client_order_id_preview": "fd_co_1",
        "fake_money": True,
        "dry_run_only": True,
        "no_send": True,
        "order_transmission_enabled": False,
        "authenticated_requests_enabled": False,
        "api_keys_loaded": False,
        "private_keys_loaded": False,
    }


def test_watcher_uses_public_unauthenticated_data_only(local_project: Path) -> None:
    from quant_os.autonomy.autonomous_market_watcher import build_autonomous_market_watcher

    payload = build_autonomous_market_watcher(
        output_root=local_project,
        now_ts=NOW,
        market_payload={"status": "CURRENT_MARKET_ELIGIBILITY_PASSED", "market": _market()},
        forecast_payload=_forecast(),
    )

    assert payload["status"] == "AUTONOMOUS_WATCHER_READY"
    assert payload["public_read_only"] is True
    assert payload["authenticated_endpoint_called"] is False
    assert payload["order_transmission_enabled"] is False
    assert payload["market_state"] == "eligible"
    assert payload["classification_reasons"] == []


def test_decision_engine_emits_no_trade_on_stale_data(local_project: Path) -> None:
    from quant_os.autonomy.autonomous_decision_engine import build_autonomous_decision_engine

    watcher = {
        "status": "AUTONOMOUS_WATCHER_NO_ELIGIBLE_MARKET",
        "market_state": "stale",
        "market": _market(orderbook_ts=STALE_TS),
        "forecast_evidence": _forecast(),
        "blockers": ["STALE_DATA"],
    }

    payload = build_autonomous_decision_engine(output_root=local_project, watcher_payload=watcher)

    assert payload["status"] == "AUTONOMOUS_DECISION_NO_TRADE"
    assert payload["decision"] == "NO_TRADE"
    assert "STALE_DATA" in payload["blockers"]


def test_decision_engine_emits_no_trade_on_missing_forecast(local_project: Path) -> None:
    from quant_os.autonomy.autonomous_decision_engine import build_autonomous_decision_engine

    watcher = {
        "status": "AUTONOMOUS_WATCHER_NO_ELIGIBLE_MARKET",
        "market_state": "missing forecast",
        "market": _market(),
        "forecast_evidence": None,
        "blockers": ["MISSING_FORECAST"],
    }

    payload = build_autonomous_decision_engine(output_root=local_project, watcher_payload=watcher)

    assert payload["status"] == "AUTONOMOUS_DECISION_NO_TRADE"
    assert payload["decision"] == "NO_TRADE"
    assert "MISSING_FORECAST" in payload["blockers"]


def test_no_transmit_intent_cannot_contain_signed_headers_private_keys_or_post(
    local_project: Path,
) -> None:
    from quant_os.autonomy.autonomous_no_transmit_intent import build_no_transmit_intent

    payload = build_no_transmit_intent(output_root=local_project, decision_payload=_decision())
    text = json.dumps(payload, sort_keys=True)

    assert payload["status"] == "NO_TRANSMIT_INTENT_READY"
    assert payload["intent"]["fake_money"] is True
    assert payload["intent"]["dry_run_only"] is True
    assert payload["intent"]["no_send"] is True
    assert payload["intent"]["contains_signed_headers"] is False
    assert payload["intent"]["contains_private_key_path"] is False
    assert payload["intent"]["contains_executable_submission_code"] is False
    assert "KALSHI-ACCESS-SIGNATURE" not in text
    assert payload["intent"]["contains_private_key_path"] is False
    assert "requests.post" not in text
    assert "/portfolio/orders" not in text


def test_mock_venue_accepts_duplicates_no_fill_partial_and_rejects(local_project: Path) -> None:
    from quant_os.execution.mock_prediction_market_venue import MockPredictionMarketVenue

    venue = MockPredictionMarketVenue()
    accepted = venue.submit_order(_intent(), scenario="accept")
    duplicate = venue.submit_order(_intent(), scenario="accept")
    no_fill = venue.submit_order({**_intent(), "client_order_id_preview": "fd_co_2"}, scenario="no_fill")
    partial = venue.submit_order(
        {**_intent(), "client_order_id_preview": "fd_co_3", "max_contracts": 2},
        scenario="partial_fill",
    )
    rejected = venue.submit_order({**_intent(), "client_order_id_preview": "fd_co_4"}, scenario="reject")

    assert accepted["status"] == "MOCK_ACCEPTED"
    assert duplicate["status"] == "MOCK_REJECTED"
    assert duplicate["reason_code"] == "DUPLICATE_CLIENT_ORDER_ID"
    assert no_fill["status"] == "MOCK_NO_FILL"
    assert partial["status"] == "MOCK_PARTIAL_FILL"
    assert partial["filled_contracts"] == 1
    assert rejected["status"] == "MOCK_REJECTED"
    assert venue.actual_order_count == 0
    assert venue.authenticated_endpoint_called is False


def test_mock_lifecycle_report_exercises_required_paths(local_project: Path) -> None:
    from quant_os.execution.mock_order_lifecycle import build_mock_order_lifecycle

    payload = build_mock_order_lifecycle(output_root=local_project)
    scenario_names = {event["scenario"] for event in payload["events"]}

    assert payload["status"] == "MOCK_ORDER_LIFECYCLE_PASSED"
    assert {
        "accepted",
        "rejected",
        "partial_fill",
        "full_fill",
        "no_fill",
        "timeout",
        "cancel_accepted",
        "cancel_rejected",
        "duplicate_rejected",
        "market_closed_rejected",
        "stale_price_rejected",
        "price_moved_no_fill",
        "unknown_order_rejected",
        "idempotency_replay",
    }.issubset(scenario_names)


def test_fake_execution_never_calls_real_endpoints_loads_keys_or_signs(local_project: Path) -> None:
    from quant_os.execution.autonomous_fake_execution_runner import run_fake_execution

    payload = run_fake_execution(output_root=local_project, intent_payload={"intent": _intent()})
    text = json.dumps(payload, sort_keys=True)

    assert payload["status"] == "FAKE_EXECUTION_PASSED"
    assert payload["actual_order_count"] == 0
    assert payload["actual_cancel_count"] == 0
    assert payload["authenticated_endpoint_called"] is False
    assert payload["api_keys_loaded"] is False
    assert payload["private_keys_loaded"] is False
    assert payload["request_signing_enabled"] is False
    assert "/portfolio/orders" not in text


def test_risk_blocks_second_order_and_max_notional_breach(local_project: Path) -> None:
    from quant_os.risk.autonomous_fire_drill_risk import evaluate_fire_drill_risk

    second = evaluate_fire_drill_risk(fake_orders=[_intent(), {**_intent(), "client_order_id_preview": "fd_co_2"}])
    notional = evaluate_fire_drill_risk(fake_orders=[{**_intent(), "max_nominal_exposure": 2.0}])

    assert second["status"] == "FIRE_DRILL_RISK_BLOCKED"
    assert "ONE_SHOT_LIMIT_EXCEEDED" in second["blockers"]
    assert notional["status"] == "FIRE_DRILL_RISK_BLOCKED"
    assert "MAX_FAKE_NOTIONAL_EXCEEDED" in notional["blockers"]


def test_kill_switch_self_disables_on_stale_reconciliation_and_exception(
    local_project: Path,
) -> None:
    from quant_os.risk.autonomous_fire_drill_kill_switch import evaluate_fire_drill_kill_switch

    stale = evaluate_fire_drill_kill_switch(watcher_status="stale")
    mismatch = evaluate_fire_drill_kill_switch(reconciliation_status="FAKE_RECONCILIATION_FAILED")
    exception = evaluate_fire_drill_kill_switch(exception_raised=True)

    assert stale["status"] == "FIRE_DRILL_KILL_SWITCH_BLOCKED"
    assert stale["self_disabled"] is True
    assert mismatch["status"] == "FIRE_DRILL_KILL_SWITCH_BLOCKED"
    assert mismatch["self_disabled"] is True
    assert exception["status"] == "FIRE_DRILL_KILL_SWITCH_BLOCKED"
    assert exception["self_disabled"] is True


def test_fake_ledger_enforces_idempotency(local_project: Path) -> None:
    from quant_os.execution.autonomous_fake_ledger import build_fake_ledger

    first = build_fake_ledger(output_root=local_project, events=[{"event_id": "e1", "evidence_hash": "h1"}])
    duplicate = build_fake_ledger(
        output_root=local_project,
        events=[{"event_id": "e1", "evidence_hash": "h1"}, {"event_id": "e1", "evidence_hash": "h1"}],
    )

    assert first["status"] == "FAKE_LEDGER_PASSED"
    assert duplicate["status"] == "FAKE_LEDGER_BLOCKED"
    assert "DUPLICATE_FAKE_LEDGER_EVENT" in duplicate["blockers"]


def test_fake_reconciliation_detects_missing_evidence_hash(local_project: Path) -> None:
    from quant_os.execution.autonomous_fake_reconciliation import build_fake_reconciliation

    payload = build_fake_reconciliation(
        output_root=local_project,
        ledger_payload={"status": "FAKE_LEDGER_PASSED", "events": [{"event_id": "e1"}]},
    )

    assert payload["status"] == "FAKE_RECONCILIATION_FAILED"
    assert "MISSING_EVIDENCE_HASH" in payload["blockers"]


def test_scenario_suite_covers_fill_no_trade_reject_timeout_cancel_and_hard_fails(
    local_project: Path,
) -> None:
    from quant_os.validation.autonomous_fire_drill_scenarios import run_fire_drill_scenarios

    payload = run_fire_drill_scenarios(output_root=local_project)
    names = {scenario["name"]: scenario for scenario in payload["scenarios"]}

    assert payload["status"] == "FIRE_DRILL_SCENARIOS_PASSED"
    assert names["eligible_fill"]["status"] == "PASSED"
    assert names["stale_data_no_trade"]["status"] == "PASSED"
    assert names["mock_reject"]["status"] == "PASSED"
    assert names["timeout_self_disable"]["status"] == "PASSED"
    assert names["cancel_path_ledger_consistent"]["status"] == "PASSED"
    assert names["attempted_auth_endpoint_call"]["status"] == "PASSED"
    assert names["live_flag_true"]["status"] == "PASSED"


def test_readiness_requires_all_gates_and_keeps_live_flags_false(local_project: Path) -> None:
    from quant_os.readiness.autonomous_live_fire_drill_readiness import build_fire_drill_readiness

    blocked = build_fire_drill_readiness(output_root=local_project)

    assert blocked["status"] != "AUTONOMOUS_LIVE_FIRE_DRILL_READY_AWAITING_HUMAN_CREDENTIALS_AND_ARMING"
    assert "PAPER_CANDIDATE_MISSING" in blocked["blockers"]
    assert blocked["live_trading_enabled"] is False
    assert blocked["execution_authority"] == "NONE"
    assert blocked["order_transmission_enabled"] is False
    assert blocked["authenticated_requests_enabled"] is False
    assert blocked["request_signing_enabled"] is False
    assert blocked["api_keys_loaded"] is False
    assert blocked["private_keys_loaded"] is False
    assert blocked["actual_order_count"] == 0
    assert blocked["actual_cancel_count"] == 0


def test_readiness_success_after_deterministic_gates(local_project: Path) -> None:
    from quant_os.readiness.autonomous_live_fire_drill_readiness import build_fire_drill_readiness

    _seed_success_gate_reports(local_project)

    payload = build_fire_drill_readiness(output_root=local_project)

    assert payload["status"] == "AUTONOMOUS_LIVE_FIRE_DRILL_READY_AWAITING_HUMAN_CREDENTIALS_AND_ARMING"
    assert payload["no_executable_real_order_path_exists"] is True
    assert payload["next_missing_thing"] == "human_credentials_account_authority_legal_approval_and_arming"


def test_human_boundary_packet_contains_required_statements_and_no_instructions(
    local_project: Path,
) -> None:
    from quant_os.readiness.human_live_boundary_packet import build_human_live_boundary_packet

    _seed_success_gate_reports(local_project)
    payload = build_human_live_boundary_packet(output_root=local_project)
    text = json.dumps(payload, sort_keys=True)

    assert payload["status"] == "HUMAN_LIVE_BOUNDARY_PACKET_READY"
    assert "The repo is not authorized to trade." in payload["statements"]
    assert "No live order has been placed." in payload["statements"]
    assert "AI must not directly place orders." in payload["statements"]
    assert (
        "Deterministic code may only trade after a separate human arming process."
        in payload["statements"]
    )
    assert "private key" in " ".join(payload["missing_human_only_items"]).lower()
    assert "KALSHI-ACCESS-SIGNATURE" not in text
    assert "requests.post" not in text
    assert "/portfolio/orders" not in text


def test_cli_commands_make_targets_and_guard_validations(local_project: Path) -> None:
    commands = [
        [sys.executable, "-m", "quant_os.cli", "autonomy", "autonomous-market-watcher"],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "autonomous-decision-engine"],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "autonomous-no-transmit-intent"],
        [sys.executable, "-m", "quant_os.cli", "execution", "mock-order-lifecycle"],
        [sys.executable, "-m", "quant_os.cli", "execution", "autonomous-fake-execution"],
        [sys.executable, "-m", "quant_os.cli", "risk", "autonomous-fire-drill-risk"],
        [sys.executable, "-m", "quant_os.cli", "execution", "autonomous-fake-reconciliation"],
        [sys.executable, "-m", "quant_os.cli", "validation", "autonomous-fire-drill-scenarios"],
        [sys.executable, "-m", "quant_os.cli", "readiness", "autonomous-live-fire-drill"],
        [sys.executable, "-m", "quant_os.cli", "readiness", "human-live-boundary-packet"],
        [sys.executable, "-m", "quant_os.cli", "guard-live"],
        [sys.executable, "-m", "quant_os.cli", "freqtrade", "generate-config"],
        [sys.executable, "-m", "quant_os.cli", "freqtrade", "validate"],
    ]
    for command in commands:
        result = subprocess.run(command, cwd=local_project, capture_output=True, text=True, check=False)
        assert result.returncode == 0, result.stderr

    make_cmd = (Path(__file__).resolve().parents[1] / "make.cmd").read_text(encoding="utf-8")
    assert 'if "%TARGET%"=="sequence59-smoke"' in make_cmd
    assert 'if "%TARGET%"=="autonomous-live-fire-drill-smoke"' in make_cmd


def _seed_success_gate_reports(root: Path) -> None:
    reports = {
        "reports/profit_campaign/latest_profit_campaign.json": {"status": "PAPER_PROFIT_CANDIDATE_FOUND"},
        "reports/first_dollar_preflight/final/latest_first_dollar_preflight.json": {
            "status": "FIRST_DOLLAR_PREFLIGHT_READY"
        },
        "reports/live_market_paper_rehearsal/final/latest_live_market_paper_rehearsal.json": {
            "status": "LIVE_MARKET_PAPER_REHEARSAL_PASSED"
        },
        "reports/autonomous_live_fire_drill/watcher/latest_watcher.json": {
            "status": "AUTONOMOUS_WATCHER_READY"
        },
        "reports/autonomous_live_fire_drill/decision/latest_decision.json": {
            "status": "AUTONOMOUS_DECISION_READY"
        },
        "reports/autonomous_live_fire_drill/no_transmit_intent/latest_intent.json": {
            "status": "NO_TRANSMIT_INTENT_READY"
        },
        "reports/autonomous_live_fire_drill/mock_lifecycle/latest_mock_lifecycle.json": {
            "status": "MOCK_ORDER_LIFECYCLE_PASSED"
        },
        "reports/autonomous_live_fire_drill/fake_execution/latest_fake_execution.json": {
            "status": "FAKE_EXECUTION_PASSED"
        },
        "reports/autonomous_live_fire_drill/risk/latest_risk.json": {
            "status": "FIRE_DRILL_RISK_PASSED",
            "kill_switch_status": "FIRE_DRILL_KILL_SWITCH_PASSED",
        },
        "reports/autonomous_live_fire_drill/reconciliation/latest_reconciliation.json": {
            "status": "FAKE_RECONCILIATION_PASSED"
        },
        "reports/autonomous_live_fire_drill/post_trade/latest_post_trade_report.json": {
            "status": "POST_TRADE_REPORT_READY"
        },
        "reports/autonomous_live_fire_drill/scenarios/latest_scenarios.json": {
            "status": "FIRE_DRILL_SCENARIOS_PASSED"
        },
        "reports/live_market_paper_rehearsal/schedule/latest_schedule.json": {
            "status": "LIVE_MARKET_PAPER_REHEARSAL_SCHEDULE_READY"
        },
    }
    for relative, payload in reports.items():
        _write_json(root, relative, {**payload, "live_trading_enabled": False, "execution_authority": "NONE"})
