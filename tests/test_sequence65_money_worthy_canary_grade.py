from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def _write_json(root: Path, relative: str, payload: dict[str, Any]) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _seed_rehearsal(root: Path, *, unsafe: bool = False) -> None:
    common = {
        "live_trading_enabled": False,
        "execution_authority": "NONE",
        "order_transmission_enabled": False,
        "authenticated_requests_enabled": False,
        "request_signing_enabled": False,
        "api_keys_loaded": False,
        "private_keys_loaded": False,
        "actual_order_count": 0,
        "actual_cancel_count": 0,
    }
    if unsafe:
        common["actual_order_count"] = 1
    _write_json(
        root,
        "reports/autonomous_live_fire_drill/final/latest_fire_drill_readiness.json",
        {
            **common,
            "status": "AUTONOMOUS_LIVE_FIRE_DRILL_READY_AWAITING_HUMAN_CREDENTIALS_AND_ARMING",
            "no_executable_real_order_path_exists": True,
        },
    )
    _write_json(
        root,
        "reports/autonomous_live_fire_drill/no_transmit_intent/latest_intent.json",
        {**common, "status": "NO_TRANSMIT_INTENT_NO_TRADE"},
    )
    _write_json(
        root,
        "reports/autonomous_live_fire_drill/mock_lifecycle/latest_mock_lifecycle.json",
        {
            **common,
            "status": "MOCK_ORDER_LIFECYCLE_PASSED",
            "mock_accepted_count": 2,
            "mock_rejected_count": 5,
            "fake_fills_count": 2,
            "fake_no_fills_count": 2,
        },
    )
    _write_json(
        root,
        "reports/autonomous_live_fire_drill/fake_execution/latest_fake_execution.json",
        {
            **common,
            "status": "FAKE_EXECUTION_NO_TRADE",
            "fake_order_state": "NO_TRADE",
            "fake_position_state": "NO_POSITION",
            "fake_pnl": {"realized_pnl": 0.0, "mark_to_market_pnl": 0.0},
        },
    )
    _write_json(
        root,
        "reports/autonomous_live_fire_drill/risk/latest_risk.json",
        {**common, "status": "FIRE_DRILL_RISK_PASSED", "kill_switch_status": "FIRE_DRILL_KILL_SWITCH_PASSED"},
    )
    _write_json(
        root,
        "reports/autonomous_live_fire_drill/reconciliation/latest_reconciliation.json",
        {**common, "status": "FAKE_RECONCILIATION_PASSED"},
    )
    _write_json(
        root,
        "reports/autonomous_live_fire_drill/scenarios/latest_scenarios.json",
        {**common, "status": "FIRE_DRILL_SCENARIOS_PASSED"},
    )


def _seed_canary(root: Path, *, fake_net_pnl: float = 0.65, baseline: bool = True) -> None:
    common = {
        "live_trading_enabled": False,
        "execution_authority": "NONE",
        "order_transmission_enabled": False,
        "authenticated_requests_enabled": False,
        "request_signing_enabled": False,
        "api_keys_loaded": False,
        "private_keys_loaded": False,
        "actual_order_count": 0,
        "actual_cancel_count": 0,
        "unsafe_action_attempts": 0,
    }
    _write_json(
        root,
        "reports/canary_grade_live_sim/final/latest_canary_grade_live_sim_readiness.json",
        {
            **common,
            "status": "CANARY_GRADE_LIVE_SIM_PROFITABILITY_PROVEN",
            "active_market_family": "crypto_spot",
            "active_strategy": "multi_strategy_canary_grade_crypto_spot",
            "assets_tested": ["BTC/USD", "ETH/USD", "SOL/USD"],
            "venues_tested": ["kraken_public"],
            "observations_count": 1200,
            "eligible_intent_count": 320,
            "fake_fill_count": 300,
            "completed_mark_count": 300,
            "fake_gross_pnl": fake_net_pnl + 0.1,
            "fake_net_pnl": fake_net_pnl,
            "baseline_pnl": 0.2,
            "placebo_pnl": 0.05,
            "baseline_beaten": baseline,
            "placebo_beaten": True,
            "reconciliation_failures": 0,
            "repeatability_status": "REPEATABILITY_PASSED",
            "capacity_status": "CAPACITY_TINY_CANARY_PASSED",
            "fresh_repro_status": "FRESH_REPRO_PASSED",
        },
    )
    _write_json(
        root,
        "reports/canary_grade_live_sim/manual_canary_packet/latest_manual_canary_packet.json",
        {**common, "status": "FIRST_TINY_MANUAL_CANARY_PACKET_READY"},
    )


def test_sequence65_no_transmit_execution_rehearsal_passes_and_blocks_unsafe(
    local_project: Path,
) -> None:
    from quant_os.readiness.autonomous_no_transmit_execution_rehearsal import (
        build_autonomous_no_transmit_execution_rehearsal,
    )

    _seed_rehearsal(local_project)
    passed = build_autonomous_no_transmit_execution_rehearsal(output_root=local_project)
    _seed_rehearsal(local_project, unsafe=True)
    unsafe = build_autonomous_no_transmit_execution_rehearsal(output_root=local_project)

    assert passed["status"] == "AUTONOMOUS_NO_TRANSMIT_EXECUTION_REHEARSAL_PASSED"
    assert passed["actual_order_count"] == 0
    assert passed["order_transmission_enabled"] is False
    assert passed["request_signing_enabled"] is False
    assert passed["api_keys_loaded"] is False
    assert passed["private_keys_loaded"] is False
    assert unsafe["status"] == "AUTONOMOUS_NO_TRANSMIT_EXECUTION_REHEARSAL_BLOCKED"
    assert any(blocker.startswith("UNSAFE_COUNTER_NONZERO") for blocker in unsafe["blockers"])


def test_sequence65_money_worthy_canary_grade_requires_profit_packet_and_rehearsal(
    local_project: Path,
) -> None:
    from quant_os.readiness.autonomous_no_transmit_execution_rehearsal import (
        write_autonomous_no_transmit_execution_rehearsal_report,
    )
    from quant_os.readiness.money_worthy_canary_grade import build_money_worthy_canary_grade

    _seed_canary(local_project)
    blocked = build_money_worthy_canary_grade(output_root=local_project)
    _seed_rehearsal(local_project)
    write_autonomous_no_transmit_execution_rehearsal_report(output_root=local_project)
    proven = build_money_worthy_canary_grade(output_root=local_project)
    _seed_canary(local_project, fake_net_pnl=-0.01)
    not_proven = build_money_worthy_canary_grade(output_root=local_project)

    assert blocked["status"] == "MONEY_WORTHY_CANARY_GRADE_BLOCKED_BY_REHEARSAL"
    assert proven["status"] == "MONEY_WORTHY_CANARY_GRADE_PROFITABILITY_PROVEN"
    assert proven["fake_net_pnl"] > 0
    assert proven["baseline_beaten"] is True
    assert proven["placebo_beaten"] is True
    assert proven["live_trading_enabled"] is False
    assert not_proven["status"] == "MONEY_WORTHY_CANARY_GRADE_NOT_PROVEN"
    assert "FAKE_NET_PNL_NOT_POSITIVE" in not_proven["blockers"]


def test_sequence65_cli_make_targets_are_data_only(local_project: Path) -> None:
    _seed_canary(local_project)
    _seed_rehearsal(local_project)

    commands = [
        [sys.executable, "-m", "quant_os.cli", "readiness", "autonomous-no-transmit-execution-rehearsal"],
        [sys.executable, "-m", "quant_os.cli", "readiness", "money-worthy-canary-grade"],
    ]
    for command in commands:
        result = subprocess.run(command, cwd=local_project, capture_output=True, text=True, check=False)
        assert result.returncode == 0, result.stderr
        assert "ORDER_SENT" not in result.stdout
        assert "LIVE_READY" not in result.stdout
        assert "ORDER_READY_TO_SEND" not in result.stdout

    make_cmd = (Path(__file__).resolve().parents[1] / "make.cmd").read_text(encoding="utf-8")
    assert 'if "%TARGET%"=="money-worthy-canary-grade-smoke"' in make_cmd
    assert 'if "%TARGET%"=="money-worthy-canary-grade-public-run"' in make_cmd
    assert 'if "%TARGET%"=="sequence65-smoke"' in make_cmd
