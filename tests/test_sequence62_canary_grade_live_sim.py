from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_sequence62_previous_10_intent_result_is_not_canary_grade() -> None:
    from quant_os.readiness.canary_grade_live_sim_readiness import (
        build_canary_grade_live_sim_readiness,
    )

    payload = build_canary_grade_live_sim_readiness(
        state={
            "observations_count": 30,
            "eligible_intent_count": 10,
            "fake_fill_count": 10,
            "completed_mark_count": 10,
            "assets_tested": ["BTC/USD"],
            "strategy_families_tested": ["btc_eth_relative_strength_rotation"],
            "walk_forward_windows": ["w1"],
            "regime_buckets": ["medium_vol"],
            "fake_net_pnl": 129.40,
            "baseline_beaten": True,
            "placebo_beaten": True,
            "reconciliation_failures": 0,
        },
        repeatability={"status": "REPEATABILITY_PASSED"},
        capacity={"status": "CAPACITY_TINY_CANARY_PASSED"},
        fresh_repro={"status": "FRESH_REPRO_PASSED"},
    )

    assert payload["status"] == "CANARY_GRADE_LIVE_SIM_NEEDS_MORE_OBSERVATIONS"
    assert "MIN_OBSERVATIONS_NOT_MET" in payload["blockers"]
    assert "MIN_ASSETS_NOT_MET" in payload["blockers"]


def test_sequence62_canary_grade_pipeline_proves_large_fixture(local_project: Path) -> None:
    from quant_os.autonomy.crypto_canary_grade_fill import write_crypto_canary_grade_fill_report
    from quant_os.autonomy.crypto_canary_grade_intents import (
        write_crypto_canary_grade_intents_report,
    )
    from quant_os.autonomy.crypto_canary_grade_ledger import write_crypto_canary_grade_ledger_report
    from quant_os.autonomy.crypto_canary_grade_observer import (
        write_crypto_canary_grade_observer_report,
    )
    from quant_os.autonomy.crypto_canary_grade_pnl import write_crypto_canary_grade_pnl_report
    from quant_os.autonomy.crypto_canary_grade_reconciliation import (
        write_crypto_canary_grade_reconciliation_report,
    )
    from quant_os.proving.crypto_live_sim_capacity import write_crypto_live_sim_capacity_report
    from quant_os.proving.crypto_live_sim_repeatability import (
        write_crypto_live_sim_repeatability_report,
    )
    from quant_os.readiness.canary_grade_live_sim_readiness import (
        write_canary_grade_live_sim_readiness_report,
    )
    from quant_os.readiness.canary_grade_manual_packet import (
        write_canary_grade_manual_packet_report,
    )

    observer = write_crypto_canary_grade_observer_report(output_root=local_project)
    intents = write_crypto_canary_grade_intents_report(output_root=local_project)
    fills = write_crypto_canary_grade_fill_report(output_root=local_project)
    ledger = write_crypto_canary_grade_ledger_report(output_root=local_project)
    pnl = write_crypto_canary_grade_pnl_report(output_root=local_project)
    reconciliation = write_crypto_canary_grade_reconciliation_report(output_root=local_project)
    repeatability = write_crypto_live_sim_repeatability_report(output_root=local_project)
    capacity = write_crypto_live_sim_capacity_report(output_root=local_project)
    readiness = write_canary_grade_live_sim_readiness_report(output_root=local_project)
    packet = write_canary_grade_manual_packet_report(output_root=local_project)

    assert observer["observation_count"] >= 1000
    assert len(observer["assets_tested"]) >= 3
    assert len(observer["regime_buckets"]) >= 2
    assert intents["eligible_intent_count"] >= 300
    assert all(intent["fake_money"] and intent["no_transmit"] for intent in intents["intents"])
    assert fills["fake_fill_count"] >= 150
    assert fills["guaranteed_fill"] is False
    assert ledger["hidden_local_state_dependency"] is False
    assert pnl["completed_mark_count"] >= 150
    assert all(row["mark_timestamp"] > row["entry_timestamp"] for row in pnl["pnl_rows"])
    assert pnl["fake_net_pnl"] > 0
    assert reconciliation["status"] == "CANARY_GRADE_RECONCILIATION_PASSED"
    assert repeatability["status"] == "REPEATABILITY_PASSED"
    assert repeatability["one_trade_dominance"] < repeatability["one_trade_dominance_cap"]
    assert repeatability["one_window_dominance"] < repeatability["one_window_dominance_cap"]
    assert repeatability["baseline_beaten"] is True
    assert repeatability["placebo_beaten"] is True
    assert capacity["status"] == "CAPACITY_TINY_CANARY_PASSED"
    assert readiness["status"] == "CANARY_GRADE_LIVE_SIM_PROFITABILITY_PROVEN"
    assert packet["status"] == "FIRST_TINY_MANUAL_CANARY_PACKET_READY"
    assert packet["order_transmission_enabled"] is False
    assert packet["actual_order_count"] == 0


def test_sequence62_readiness_blocks_baseline_placebo_dominance_stress_and_repro() -> None:
    from quant_os.readiness.canary_grade_live_sim_readiness import (
        build_canary_grade_live_sim_readiness,
    )

    state = {
        "observations_count": 1200,
        "eligible_intent_count": 400,
        "fake_fill_count": 200,
        "completed_mark_count": 200,
        "assets_tested": ["BTC/USD", "ETH/USD", "SOL/USD"],
        "strategy_families_tested": ["s1", "s2"],
        "walk_forward_windows": ["w1", "w2", "w3"],
        "regime_buckets": ["low_vol", "high_vol"],
        "fake_net_pnl": 100.0,
        "baseline_beaten": False,
        "placebo_beaten": False,
        "reconciliation_failures": 0,
    }
    repeatability = {
        "status": "REPEATABILITY_BLOCKED",
        "one_trade_dominance": 0.60,
        "one_trade_dominance_cap": 0.25,
        "one_window_dominance": 0.70,
        "one_window_dominance_cap": 0.35,
        "worse_fill_status": "BLOCKED",
        "higher_fee_status": "BLOCKED",
        "delayed_entry_status": "BLOCKED",
        "baseline_beaten": False,
        "placebo_beaten": False,
    }

    payload = build_canary_grade_live_sim_readiness(
        state=state,
        repeatability=repeatability,
        capacity={"status": "CAPACITY_BLOCKED_BY_LIQUIDITY"},
        fresh_repro={"status": "LOCAL_ONLY_DEPENDENCY_BLOCKED"},
    )

    assert payload["status"] == "CANARY_GRADE_LIVE_SIM_BLOCKED_BY_RECONCILIATION"
    assert "BASELINE_NOT_BEATEN" in payload["blockers"]
    assert "PLACEBO_NOT_BEATEN" in payload["blockers"]
    assert "ONE_TRADE_DOMINANCE_TOO_HIGH" in payload["blockers"]
    assert "ONE_WINDOW_DOMINANCE_TOO_HIGH" in payload["blockers"]
    assert "WORSE_FILL_STRESS_FAILED" in payload["blockers"]
    assert "HIGHER_FEE_STRESS_FAILED" in payload["blockers"]
    assert "DELAYED_ENTRY_STRESS_FAILED" in payload["blockers"]
    assert "CAPACITY_TINY_CANARY_NOT_PASSED" in payload["blockers"]
    assert "FRESH_WORKTREE_REPRO_NOT_PASSED" in payload["blockers"]


def test_sequence62_pnl_blocks_lookahead() -> None:
    from quant_os.autonomy.crypto_canary_grade_pnl import build_crypto_canary_grade_pnl

    payload = build_crypto_canary_grade_pnl(
        ledger={
            "ledger_entries": [
                {
                    "entry_timestamp": "2026-05-18T10:05:00Z",
                    "mark_timestamp": "2026-05-18T10:04:00Z",
                    "entry_price": 100.0,
                    "mark_price": 101.0,
                    "quantity": 1.0,
                    "side": "buy",
                    "spread_cost": 0.01,
                    "slippage_cost": 0.01,
                    "fee_cost": 0.01,
                }
            ]
        }
    )

    assert payload["status"] == "CANARY_GRADE_PNL_BLOCKED"
    assert "LOOKAHEAD_MARK_NOT_AFTER_ENTRY" in payload["blockers"]


def test_sequence62_capacity_blocks_unsupported_size() -> None:
    from quant_os.proving.crypto_live_sim_capacity import build_crypto_live_sim_capacity

    payload = build_crypto_live_sim_capacity(
        fills={
            "fake_fills": [
                {
                    "symbol": "BTC/USD",
                    "entry_price": 100.0,
                    "quantity": 0.001,
                    "public_depth_notional": 0.50,
                    "spread": 0.02,
                }
            ]
        }
    )

    assert payload["status"] == "CAPACITY_BLOCKED_BY_LIQUIDITY"
    assert payload["capacity_by_size"]["1_usd"]["supported"] is False


def test_sequence62_scheduler_and_cli_are_data_only(local_project: Path) -> None:
    from quant_os.autonomy.canary_grade_live_sim_schedule import (
        write_canary_grade_live_sim_schedule_report,
    )

    payload = write_canary_grade_live_sim_schedule_report(output_root=local_project)

    assert payload["status"] == "CANARY_GRADE_LIVE_SIM_SCHEDULE_READY"
    assert payload["data_only"] is True
    assert payload["live_trading_enabled"] is False
    assert payload["execution_authority"] == "NONE"
    assert "no credentials" in payload["powershell_command"].lower()
    assert "no orders" in payload["powershell_command"].lower()
    make_cmd = (Path(__file__).resolve().parents[1] / "make.cmd").read_text(encoding="utf-8")
    assert "sequence62-smoke" in make_cmd
    assert "canary-grade-live-sim-smoke" in make_cmd

    commands = [
        [sys.executable, "-m", "quant_os.cli", "autonomy", "crypto-canary-grade-observer"],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "crypto-canary-grade-intents"],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "crypto-canary-grade-fill"],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "crypto-canary-grade-ledger"],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "crypto-canary-grade-pnl"],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "crypto-canary-grade-reconciliation"],
        [sys.executable, "-m", "quant_os.cli", "proving", "crypto-live-sim-repeatability"],
        [sys.executable, "-m", "quant_os.cli", "proving", "crypto-live-sim-capacity"],
        [sys.executable, "-m", "quant_os.cli", "readiness", "canary-grade-live-sim"],
        [sys.executable, "-m", "quant_os.cli", "readiness", "canary-grade-manual-packet"],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "canary-grade-live-sim-schedule"],
    ]
    for command in commands:
        result = subprocess.run(command, cwd=local_project, capture_output=True, text=True, check=False)
        assert result.returncode == 0, result.stderr
        assert "ORDER_SENT" not in result.stdout
        assert "LIVE_READY" not in result.stdout
