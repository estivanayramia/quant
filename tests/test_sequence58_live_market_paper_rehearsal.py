from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

NOW = "2026-05-17T20:10:00Z"
FRESH_ORDERBOOK_TS = "2026-05-17T20:09:00Z"


def _write_json(root: Path, relative: str, payload: dict[str, object]) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _market(**overrides: object) -> dict[str, object]:
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
        "orderbook_ts": FRESH_ORDERBOOK_TS,
        "market_evidence_hash": "market-hash",
        "resolution_ts": "2026-05-19T14:00:00Z",
    }
    payload.update(overrides)
    return payload


def _forecast(**overrides: object) -> dict[str, object]:
    payload = {
        "status": "CURRENT_FORECAST_MATCHED",
        "source_id": "nws_api",
        "source_kind": "forecast",
        "forecast_issue_ts": "2026-05-17T20:00:00Z",
        "forecast_valid_ts": "2026-05-18T14:00:00-04:00",
        "known_at_ts": "2026-05-17T20:00:00Z",
        "orderbook_ts": FRESH_ORDERBOOK_TS,
        "forecast_value": 83,
        "forecast_bucket": "83_to_84_f_inclusive",
        "bucket_match": True,
        "evidence_hash": "forecast-hash",
    }
    payload.update(overrides)
    return payload


def _seed_no_market_preflight(root: Path) -> None:
    _write_json(
        root,
        "reports/first_dollar_preflight/final/latest_first_dollar_preflight.json",
        {
            "status": "FIRST_DOLLAR_PREFLIGHT_STRUCTURALLY_READY_NO_CURRENT_MARKET",
            "blockers": ["NO_CURRENT_ELIGIBLE_MARKET"],
            "live_trading_enabled": False,
            "execution_authority": "NONE",
            "order_transmission_enabled": False,
            "authenticated_requests_enabled": False,
            "api_keys_loaded": False,
            "private_keys_loaded": False,
            "actual_order_count": 0,
            "actual_cancel_count": 0,
        },
    )
    _write_json(
        root,
        "reports/first_dollar_preflight/current_market/latest_current_market_eligibility.json",
        {
            "status": "CURRENT_MARKET_ELIGIBILITY_NO_CURRENT_MARKET",
            "blockers": ["NO_CURRENT_PUBLIC_MARKET_SUPPLIED"],
            "market": None,
            "forecast_evidence": {"status": "CURRENT_FORECAST_BLOCKED"},
            "live_trading_enabled": False,
            "execution_authority": "NONE",
            "order_transmission_enabled": False,
            "authenticated_requests_enabled": False,
            "api_keys_loaded": False,
            "private_keys_loaded": False,
            "actual_order_count": 0,
            "actual_cancel_count": 0,
        },
    )


def test_sequence58_no_current_market_does_not_block_framework_creation(local_project: Path) -> None:
    from quant_os.autonomy.live_market_paper_observer import write_live_market_paper_observer_report

    _seed_no_market_preflight(local_project)

    payload = write_live_market_paper_observer_report(output_root=local_project, now_ts=NOW)

    assert payload["status"] == "LIVE_MARKET_OBSERVATION_NO_ELIGIBLE_MARKET"
    assert payload["observation"]["observation_kind"] == "NO_CURRENT_ELIGIBLE_MARKET"
    assert payload["observation"]["eligible_market"] is False
    assert payload["blockers"] == []
    assert (local_project / "reports/live_market_paper_rehearsal/observer/latest_observer.json").exists()


def test_sequence58_no_current_market_produces_no_trade_observation(local_project: Path) -> None:
    from quant_os.autonomy.live_market_paper_intents import build_live_market_paper_intents
    from quant_os.autonomy.live_market_paper_observer import write_live_market_paper_observer_report

    _seed_no_market_preflight(local_project)
    observer = write_live_market_paper_observer_report(output_root=local_project, now_ts=NOW)
    payload = build_live_market_paper_intents(output_root=local_project)

    assert observer["status"] == "LIVE_MARKET_OBSERVATION_NO_ELIGIBLE_MARKET"
    assert payload["status"] == "PAPER_INTENT_NO_TRADE"
    assert payload["intent"] is None
    assert payload["observation_kind"] == "NO_CURRENT_ELIGIBLE_MARKET"
    assert payload["dry_run_only"] is True
    assert payload["no_send"] is True
    assert payload["fake_money"] is True


def test_sequence58_no_trade_observation_reconciles_safely(local_project: Path) -> None:
    from quant_os.autonomy.live_market_fake_fill_model import write_live_market_fake_fill_report
    from quant_os.autonomy.live_market_paper_intents import write_live_market_paper_intents_report
    from quant_os.autonomy.live_market_paper_ledger import write_live_market_paper_ledger_report
    from quant_os.autonomy.live_market_paper_observer import write_live_market_paper_observer_report
    from quant_os.autonomy.live_market_paper_reconciliation import (
        write_live_market_paper_reconciliation_report,
    )

    _seed_no_market_preflight(local_project)
    write_live_market_paper_observer_report(output_root=local_project, now_ts=NOW)
    write_live_market_paper_intents_report(output_root=local_project)
    write_live_market_fake_fill_report(output_root=local_project)
    write_live_market_paper_ledger_report(output_root=local_project)
    payload = write_live_market_paper_reconciliation_report(output_root=local_project)

    assert payload["status"] == "PAPER_RECONCILIATION_PASSED"
    assert payload["checks"]["no_trade_no_fill_consistent"] is True
    assert payload["blockers"] == []


def test_sequence58_eligible_market_can_produce_no_transmit_fake_money_intent(
    local_project: Path,
) -> None:
    from quant_os.autonomy.live_market_paper_intents import build_live_market_paper_intents
    from quant_os.autonomy.live_market_paper_observer import write_live_market_paper_observer_report

    observer = write_live_market_paper_observer_report(
        output_root=local_project,
        now_ts=NOW,
        current_market_payload={
            "status": "CURRENT_MARKET_ELIGIBILITY_PASSED",
            "market": _market(),
            "forecast_evidence": _forecast(),
            "forecast_evidence_hash": "forecast-hash",
            "market_evidence_hash": "market-hash",
            "blockers": [],
        },
        preflight_payload={"status": "FIRST_DOLLAR_PREFLIGHT_READY", "blockers": []},
    )
    payload = build_live_market_paper_intents(output_root=local_project)

    assert observer["status"] == "LIVE_MARKET_OBSERVATION_READY"
    assert payload["status"] == "PAPER_INTENT_READY"
    assert payload["intent"]["dry_run_only"] is True
    assert payload["intent"]["no_send"] is True
    assert payload["intent"]["fake_money"] is True
    assert payload["intent"]["order_transmission_enabled"] is False
    assert payload["intent"]["authenticated_requests_enabled"] is False
    text = json.dumps(payload, sort_keys=True)
    assert "KALSHI-ACCESS-SIGNATURE" not in text
    assert "/portfolio/orders" not in text
    assert payload["intent"]["contains_private_key_path"] is False


def test_sequence58_fake_fill_never_guarantees_fills(local_project: Path) -> None:
    from quant_os.autonomy.live_market_fake_fill_model import apply_fake_fill_model

    payload = apply_fake_fill_model(
        intent={
            "market_ticker": "KXHIGHNY-26MAY18-B83.5",
            "side": "yes",
            "action": "buy",
            "limit_price": 0.27,
            "fake_contracts": 1,
        },
        observation={"market": _market(yes_ask=0.27, yes_bid=0.25, spread=0.02, liquidity=12.0)},
    )

    assert payload["status"] == "FAKE_FILL_APPLIED"
    assert payload["guaranteed_fill"] is False
    assert payload["fake_fill_confidence"] < 1.0


def test_sequence58_fake_fill_blocks_wide_spread(local_project: Path) -> None:
    from quant_os.autonomy.live_market_fake_fill_model import apply_fake_fill_model

    payload = apply_fake_fill_model(
        intent={
            "market_ticker": "KXHIGHNY-26MAY18-B83.5",
            "side": "yes",
            "action": "buy",
            "limit_price": 0.35,
            "fake_contracts": 1,
        },
        observation={"market": _market(yes_ask=0.35, yes_bid=0.20, spread=0.15, liquidity=12.0)},
    )

    assert payload["status"] == "FAKE_FILL_BLOCKED"
    assert "SPREAD_TOO_WIDE_FOR_FAKE_FILL" in payload["blockers"]


def test_sequence58_ledger_records_no_trade_no_fill_and_fake_fill_states(
    local_project: Path,
) -> None:
    from quant_os.autonomy.live_market_paper_ledger import build_live_market_paper_ledger

    no_trade = build_live_market_paper_ledger(
        output_root=local_project,
        intents_payload={"status": "PAPER_INTENT_NO_TRADE", "intent": None, "observation_id": "obs-no-market"},
        fills_payload={"status": "FAKE_NO_FILL", "fake_fill": None, "observation_id": "obs-no-market"},
    )
    filled = build_live_market_paper_ledger(
        output_root=local_project,
        intents_payload={
            "status": "PAPER_INTENT_READY",
            "intent": {
                "fake_client_order_id": "paper-1",
                "market_ticker": "KXHIGHNY-26MAY18-B83.5",
                "limit_price": 0.27,
                "fake_contracts": 1,
                "forecast_evidence_hash": "forecast-hash",
                "market_evidence_hash": "market-hash",
            },
            "observation_id": "obs-fill",
        },
        fills_payload={
            "status": "FAKE_FILL_APPLIED",
            "fake_fill": {
                "fake_fill_id": "fill-1",
                "fake_client_order_id": "paper-1",
                "fill_price": 0.27,
                "filled_contracts": 1,
            },
            "observation_id": "obs-fill",
        },
    )

    assert no_trade["status"] == "PAPER_LEDGER_UPDATED"
    assert no_trade["fake_position"]["state"] == "NO_POSITION"
    assert no_trade["fake_pnl"]["mark_to_market_pnl"] == 0.0
    assert filled["status"] == "PAPER_LEDGER_UPDATED"
    assert filled["fake_position"]["state"] == "OPEN_FAKE_POSITION"
    assert filled["fake_position"]["contracts"] == 1


def test_sequence58_readiness_returns_needs_more_observations_when_sample_too_small(
    local_project: Path,
) -> None:
    from quant_os.autonomy.live_market_fake_fill_model import write_live_market_fake_fill_report
    from quant_os.autonomy.live_market_paper_intents import write_live_market_paper_intents_report
    from quant_os.autonomy.live_market_paper_ledger import write_live_market_paper_ledger_report
    from quant_os.autonomy.live_market_paper_observer import write_live_market_paper_observer_report
    from quant_os.autonomy.live_market_paper_reconciliation import (
        write_live_market_paper_reconciliation_report,
    )
    from quant_os.readiness.live_market_paper_rehearsal_readiness import (
        write_live_market_paper_rehearsal_readiness_report,
    )

    _seed_no_market_preflight(local_project)
    write_live_market_paper_observer_report(output_root=local_project, now_ts=NOW)
    write_live_market_paper_intents_report(output_root=local_project)
    write_live_market_fake_fill_report(output_root=local_project)
    write_live_market_paper_ledger_report(output_root=local_project)
    write_live_market_paper_reconciliation_report(output_root=local_project)
    payload = write_live_market_paper_rehearsal_readiness_report(output_root=local_project)

    assert payload["status"] == "LIVE_MARKET_PAPER_REHEARSAL_NEEDS_MORE_OBSERVATIONS"
    assert payload["observation_count"] == 1
    assert "MIN_OBSERVATIONS_NOT_MET" in payload["blockers"]


def test_sequence58_readiness_can_pass_with_repeated_correct_no_trade_blocks(
    local_project: Path,
) -> None:
    from quant_os.readiness.live_market_paper_rehearsal_readiness import (
        build_live_market_paper_rehearsal_readiness,
    )

    observations = [
        {
            "observation_id": f"obs-{index}",
            "observation_kind": "MARKET_OR_FORECAST_BLOCKED",
            "current_market_status": "CURRENT_MARKET_ELIGIBILITY_BLOCKED",
            "eligible_market": False,
            "market": {"ticker": "KXHIGHNY-26MAY18-T84", "yes_ask": 0.68, "spread": 0.03},
        }
        for index in range(5)
    ]
    _write_json(
        local_project,
        "reports/live_market_paper_rehearsal/state/latest_state.json",
        {"observations": observations},
    )
    _write_json(
        local_project,
        "reports/live_market_paper_rehearsal/reconciliation/latest_reconciliation.json",
        {"status": "PAPER_RECONCILIATION_PASSED"},
    )
    _write_json(
        local_project,
        "reports/live_market_paper_rehearsal/fills/latest_fake_fills.json",
        {"status": "FAKE_NO_FILL"},
    )
    _write_json(
        local_project,
        "reports/live_market_paper_rehearsal/ledger/latest_paper_ledger.json",
        {"status": "PAPER_LEDGER_UPDATED"},
    )
    _write_json(
        local_project,
        "reports/live_market_paper_rehearsal/intents/latest_intents.json",
        {"status": "PAPER_INTENT_NO_TRADE"},
    )

    payload = build_live_market_paper_rehearsal_readiness(output_root=local_project)

    assert payload["status"] == "LIVE_MARKET_PAPER_REHEARSAL_PASSED"
    assert payload["no_transmit_intents_generated"] == 0
    assert payload["repeated_blocked_trade_proof"] is True
    assert payload["correctly_blocked_observation_count"] == 5


def test_sequence58_scheduler_is_data_only(local_project: Path) -> None:
    from quant_os.autonomy.live_market_paper_rehearsal_schedule import (
        write_live_market_paper_rehearsal_schedule_report,
    )

    payload = write_live_market_paper_rehearsal_schedule_report(output_root=local_project)

    assert payload["status"] == "LIVE_MARKET_PAPER_REHEARSAL_SCHEDULE_READY"
    assert payload["data_only"] is True
    assert payload["public_network_optional_flag"] == "--public-network-ok"
    assert payload["max_runs"] == 8
    assert "for ($i = 1; $i -le 8; $i++)" in payload["exact_powershell_command"]
    assert payload["credentials_required"] is False
    assert payload["order_transmission_enabled"] is False
    assert "live-market-paper-observer --public-network-ok" in payload["exact_resume_command"]


def test_sequence58_cli_make_target_and_no_auth_order_cancel_path(local_project: Path) -> None:
    commands = [
        [sys.executable, "-m", "quant_os.cli", "autonomy", "live-market-paper-observer"],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "live-market-paper-intents"],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "live-market-fake-fill"],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "live-market-paper-ledger"],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "live-market-paper-reconciliation"],
        [sys.executable, "-m", "quant_os.cli", "readiness", "live-market-paper-rehearsal"],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "live-market-paper-rehearsal-schedule"],
    ]
    for command in commands:
        result = subprocess.run(
            command,
            cwd=local_project,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert "live_trading_enabled" in result.stdout

    make_cmd = (Path(__file__).resolve().parents[1] / "make.cmd").read_text(encoding="utf-8")
    assert 'if "%TARGET%"=="sequence58-smoke"' in make_cmd
    for path in [
        "src/quant_os/autonomy/live_market_paper_observer.py",
        "src/quant_os/autonomy/live_market_paper_intents.py",
        "src/quant_os/autonomy/live_market_fake_fill_model.py",
        "src/quant_os/autonomy/live_market_paper_ledger.py",
        "src/quant_os/autonomy/live_market_paper_reconciliation.py",
        "src/quant_os/readiness/live_market_paper_rehearsal_readiness.py",
        "src/quant_os/autonomy/live_market_paper_rehearsal_schedule.py",
    ]:
        text = (Path(__file__).resolve().parents[1] / path).read_text(encoding="utf-8")
        assert "requests.post" not in text
        assert "urllib.request.Request" not in text
        assert "/portfolio/orders" not in text
        assert "KALSHI-ACCESS-SIGNATURE" not in text
        assert "cancel_order" not in text
