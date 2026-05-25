from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _write_json(root: Path, relative: str, payload: dict) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _crypto_fixture() -> dict:
    return {
        "source": "fixture_public_kraken_shape",
        "fetched_at": "2026-05-17T18:00:00Z",
        "symbols": {
            "BTC/USD": {
                "source_pair": "XXBTZUSD",
                "candles": [
                    {"timestamp": "2026-05-17T17:50:00Z", "open": 100.0, "high": 100.2, "low": 99.8, "close": 100.0, "volume": 12.0},
                    {"timestamp": "2026-05-17T17:51:00Z", "open": 100.0, "high": 100.5, "low": 99.9, "close": 100.2, "volume": 12.0},
                    {"timestamp": "2026-05-17T17:52:00Z", "open": 100.2, "high": 101.0, "low": 100.1, "close": 100.6, "volume": 13.0},
                    {"timestamp": "2026-05-17T17:53:00Z", "open": 100.6, "high": 101.5, "low": 100.5, "close": 101.2, "volume": 14.0},
                    {"timestamp": "2026-05-17T17:54:00Z", "open": 101.2, "high": 101.8, "low": 101.1, "close": 101.7, "volume": 15.0},
                    {"timestamp": "2026-05-17T17:55:00Z", "open": 101.7, "high": 102.3, "low": 101.6, "close": 102.1, "volume": 16.0},
                    {"timestamp": "2026-05-17T17:56:00Z", "open": 102.1, "high": 102.8, "low": 102.0, "close": 102.7, "volume": 17.0},
                    {"timestamp": "2026-05-17T17:57:00Z", "open": 102.7, "high": 103.2, "low": 102.6, "close": 103.1, "volume": 18.0},
                ],
                "book": {"bid": 103.09, "ask": 103.11, "spread": 0.02, "bid_size": 4.0, "ask_size": 4.0},
            },
            "ETH/USD": {
                "source_pair": "XETHZUSD",
                "candles": [
                    {"timestamp": "2026-05-17T17:50:00Z", "open": 50.0, "high": 50.2, "low": 49.9, "close": 50.0, "volume": 20.0},
                    {"timestamp": "2026-05-17T17:51:00Z", "open": 50.0, "high": 50.1, "low": 49.8, "close": 49.95, "volume": 20.0},
                    {"timestamp": "2026-05-17T17:52:00Z", "open": 49.95, "high": 50.0, "low": 49.7, "close": 49.9, "volume": 21.0},
                    {"timestamp": "2026-05-17T17:53:00Z", "open": 49.9, "high": 50.0, "low": 49.6, "close": 49.8, "volume": 21.0},
                    {"timestamp": "2026-05-17T17:54:00Z", "open": 49.8, "high": 49.9, "low": 49.5, "close": 49.7, "volume": 22.0},
                    {"timestamp": "2026-05-17T17:55:00Z", "open": 49.7, "high": 49.8, "low": 49.4, "close": 49.6, "volume": 23.0},
                    {"timestamp": "2026-05-17T17:56:00Z", "open": 49.6, "high": 49.7, "low": 49.3, "close": 49.5, "volume": 24.0},
                    {"timestamp": "2026-05-17T17:57:00Z", "open": 49.5, "high": 49.6, "low": 49.2, "close": 49.4, "volume": 25.0},
                ],
                "book": {"bid": 49.39, "ask": 49.41, "spread": 0.02, "bid_size": 8.0, "ask_size": 8.0},
            },
        },
    }


def test_sequence61_router_routes_to_crypto_while_weather_pending(local_project: Path) -> None:
    from quant_os.autonomy.multi_market_live_sim_router import build_multi_market_live_sim_router

    weather = {"status": "LIVE_MARKET_SIMULATED_PROFITABILITY_PENDING_OUTCOMES", "pending_outcome_count": 20}
    router = build_multi_market_live_sim_router(weather_profitability=weather)

    assert router["status"] == "MARKET_FAMILY_SELECTED"
    assert router["selected_market_family"] == "crypto_spot"
    assert "weather_prediction_markets" in router["market_family_statuses"]
    assert router["live_trading_enabled"] is False
    assert router["execution_authority"] == "NONE"
    assert router["order_transmission_enabled"] is False


def test_sequence61_crypto_fixture_pipeline_proves_fake_money_profitability(local_project: Path) -> None:
    from quant_os.autonomy.crypto_spot_live_sim_fill import write_crypto_spot_live_sim_fill_report
    from quant_os.autonomy.crypto_spot_live_sim_intents import (
        write_crypto_spot_live_sim_intents_report,
    )
    from quant_os.autonomy.crypto_spot_live_sim_ledger import (
        write_crypto_spot_live_sim_ledger_report,
    )
    from quant_os.autonomy.crypto_spot_live_sim_observer import (
        write_crypto_spot_live_sim_observer_report,
    )
    from quant_os.autonomy.crypto_spot_live_sim_pnl import write_crypto_spot_live_sim_pnl_report
    from quant_os.autonomy.crypto_spot_live_sim_reconciliation import (
        write_crypto_spot_live_sim_reconciliation_report,
    )
    from quant_os.proving.crypto_spot_live_sim_comparison import (
        write_crypto_spot_live_sim_comparison_report,
    )
    from quant_os.readiness.crypto_spot_live_sim_profitability import (
        write_crypto_spot_live_sim_profitability_report,
    )

    observer = write_crypto_spot_live_sim_observer_report(
        output_root=local_project,
        public_snapshot=_crypto_fixture(),
    )
    intents = write_crypto_spot_live_sim_intents_report(output_root=local_project)
    fills = write_crypto_spot_live_sim_fill_report(output_root=local_project)
    ledger = write_crypto_spot_live_sim_ledger_report(output_root=local_project)
    pnl = write_crypto_spot_live_sim_pnl_report(output_root=local_project)
    comparison = write_crypto_spot_live_sim_comparison_report(output_root=local_project)
    reconciliation = write_crypto_spot_live_sim_reconciliation_report(output_root=local_project)
    readiness = write_crypto_spot_live_sim_profitability_report(
        output_root=local_project,
        min_observations=6,
        min_intents=5,
        min_fills=3,
        min_completed_marks=5,
    )

    assert observer["status"] == "CRYPTO_OBSERVER_READY"
    assert observer["public_unauthenticated_data_only"] is True
    assert observer["credential_sources_used"] == []
    assert intents["eligible_intent_count"] >= 5
    assert all(intent["fake_money"] and intent["no_transmit"] for intent in intents["intents"])
    assert all(not intent["contains_signed_headers"] for intent in intents["intents"])
    assert all("/orders" not in " ".join(intent.get("blocked_endpoints", [])) for intent in intents["intents"])
    assert fills["fake_fill_count"] >= 3
    assert fills["guaranteed_fill"] is False
    assert ledger["position_state"] == "FAKE_POSITIONS_TRACKED"
    assert pnl["completed_mark_count"] >= 5
    assert all(row["mark_timestamp"] > row["entry_timestamp"] for row in pnl["pnl_rows"])
    assert pnl["fake_net_pnl"] > 0
    assert comparison["baseline_beaten"] is True
    assert comparison["placebo_beaten"] is True
    assert reconciliation["status"] == "CRYPTO_LIVE_SIM_RECONCILIATION_PASSED"
    assert readiness["status"] == "CRYPTO_LIVE_SIM_PROFITABILITY_PROVEN"
    assert readiness["live_trading_enabled"] is False
    assert readiness["request_signing_enabled"] is False
    assert readiness["actual_order_count"] == 0


def test_sequence61_crypto_pnl_blocks_lookahead(local_project: Path) -> None:
    from quant_os.autonomy.crypto_spot_live_sim_pnl import build_crypto_spot_live_sim_pnl

    ledger = {
        "ledger_entries": [
            {
                "fake_fill_id": "fill_bad",
                "fake_client_order_id": "intent_bad",
                "symbol": "BTC/USD",
                "side": "buy",
                "entry_timestamp": "2026-05-17T17:55:00Z",
                "entry_price": 101.0,
                "quantity": 1.0,
                "mark_timestamp": "2026-05-17T17:54:00Z",
                "mark_price": 102.0,
                "spread_cost": 0.01,
                "slippage_cost": 0.01,
                "fee_cost": 0.0,
                "evidence_hash": "hash",
            }
        ]
    }
    result = build_crypto_spot_live_sim_pnl(ledger=ledger)

    assert result["status"] == "CRYPTO_LIVE_SIM_PNL_BLOCKED"
    assert "LOOKAHEAD_MARK_NOT_AFTER_ENTRY" in result["blockers"]


def test_sequence61_crypto_observer_tolerates_public_spread_float_boundary() -> None:
    from quant_os.autonomy.crypto_spot_live_sim_observer import build_crypto_spot_live_sim_observer

    snapshot = _crypto_fixture()
    snapshot["symbols"]["BTC/USD"]["book"]["spread"] = 0.10000000000582077
    payload = build_crypto_spot_live_sim_observer(public_snapshot=snapshot)

    assert any(observation["eligible"] for observation in payload["observations"])


def test_sequence61_crypto_fill_tolerates_public_spread_float_boundary() -> None:
    from quant_os.autonomy.crypto_spot_live_sim_fill import apply_crypto_spot_live_sim_fill_model

    observation = {
        "observation_id": "obs",
        "spread": 0.10000000000582077,
        "ask_size": 1.0,
        "entry_price": 100.0,
    }
    intent = {
        "fake_client_order_id": "intent",
        "observation_id": "obs",
        "symbol": "BTC/USD",
        "side": "buy",
        "quantity": 1.0,
        "limit_price": 100.1,
        "entry_timestamp": "2026-05-17T17:55:00Z",
        "mark_timestamp": "2026-05-17T17:56:00Z",
        "mark_price": 100.5,
    }
    payload = apply_crypto_spot_live_sim_fill_model(intents=[intent], observations=[observation])

    assert payload["fake_fill_count"] == 1
    assert payload["guaranteed_fill"] is False


def test_sequence61_market_family_blockers_and_final_gate(local_project: Path) -> None:
    from quant_os.readiness.multi_market_live_sim_profitability import (
        build_multi_market_live_sim_profitability,
        build_prediction_market_structural_profitability,
        build_weather_live_sim_profitability,
        evaluate_etf_equity_source_policy,
    )

    weather = build_weather_live_sim_profitability(
        sequence60_payload={"status": "LIVE_MARKET_SIMULATED_PROFITABILITY_PENDING_OUTCOMES", "pending_outcome_count": 20}
    )
    pm = build_prediction_market_structural_profitability(
        relations=[{"lane": "pm_negation_pair_arbitrage", "relation_confidence": "subjective"}]
    )
    etf = evaluate_etf_equity_source_policy({"source": "unknown_scrape", "policy": "ambiguous"})
    pending_final = build_multi_market_live_sim_profitability(
        crypto={"status": "CRYPTO_LIVE_SIM_PENDING_MARKS"},
        weather=weather,
        prediction_market_structural=pm,
        etf_equity=etf,
    )
    proven_final = build_multi_market_live_sim_profitability(
        crypto={"status": "CRYPTO_LIVE_SIM_PROFITABILITY_PROVEN", "fake_net_pnl": 1.25, "baseline_beaten": True, "placebo_beaten": True, "reconciliation_status": "CRYPTO_LIVE_SIM_RECONCILIATION_PASSED"},
        weather=weather,
        prediction_market_structural=pm,
        etf_equity=etf,
    )

    assert weather["status"] == "WEATHER_LIVE_SIM_PENDING_OUTCOMES"
    assert weather["fake_net_pnl"] == 0.0
    assert pm["status"] == "PM_STRUCTURAL_LIVE_SIM_BLOCKED"
    assert "AMBIGUOUS_RELATION_MAPPING" in pm["blockers"]
    assert etf["status"] == "ETF_LIVE_SIM_NEEDS_APPROVED_SOURCE"
    assert pending_final["status"] == "MULTI_MARKET_LIVE_SIM_PENDING_OUTCOMES"
    assert proven_final["status"] == "MULTI_MARKET_LIVE_SIM_PROFITABILITY_PROVEN"
    assert proven_final["live_trading_enabled"] is False
    assert proven_final["api_keys_loaded"] is False
    assert proven_final["actual_cancel_count"] == 0


def test_sequence61_scheduler_and_cli_are_data_only(local_project: Path) -> None:
    from quant_os.autonomy.multi_market_live_sim_schedule import (
        write_multi_market_live_sim_schedule_report,
    )

    payload = write_multi_market_live_sim_schedule_report(output_root=local_project)

    assert payload["status"] == "MULTI_MARKET_LIVE_SIM_SCHEDULE_READY"
    assert payload["data_only"] is True
    assert payload["live_trading_enabled"] is False
    assert "no credentials" in payload["powershell_command"].lower()
    assert "orders" not in payload["powershell_command"].lower()
    make_cmd = (Path(__file__).resolve().parents[1] / "make.cmd").read_text(encoding="utf-8")
    assert "sequence61-smoke" in make_cmd
    assert "multi-market-live-sim-smoke" in make_cmd

    commands = [
        [sys.executable, "-m", "quant_os.cli", "autonomy", "multi-market-live-sim-router"],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "crypto-spot-live-sim-observer"],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "crypto-spot-live-sim-intents"],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "crypto-spot-live-sim-fill"],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "crypto-spot-live-sim-ledger"],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "crypto-spot-live-sim-pnl"],
        [sys.executable, "-m", "quant_os.cli", "proving", "crypto-spot-live-sim-comparison"],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "crypto-spot-live-sim-reconciliation"],
        [sys.executable, "-m", "quant_os.cli", "readiness", "crypto-spot-live-sim-profitability"],
        [sys.executable, "-m", "quant_os.cli", "readiness", "multi-market-live-sim-profitability"],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "multi-market-live-sim-schedule"],
    ]
    for command in commands:
        result = subprocess.run(command, cwd=local_project, capture_output=True, text=True, check=False)
        assert result.returncode == 0, result.stderr
        assert "ORDER_SENT" not in result.stdout
        assert "LIVE_READY" not in result.stdout
