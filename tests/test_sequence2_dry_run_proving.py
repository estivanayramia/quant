from __future__ import annotations

import json

import pandas as pd

from quant_os.autonomy.dry_run_proving import DryRunProvingConfig, run_dry_run_proving_cycle
from quant_os.autonomy.proving_health import (
    Sequence2ReadinessStatus,
    evaluate_sequence2_readiness,
)
from quant_os.readiness.sequence2 import write_sequence2_readiness_report


def _frame(periods: int = 90) -> pd.DataFrame:
    timestamps = pd.date_range("2026-01-01T00:00:00Z", periods=periods, freq="min")
    rows = []
    for index, timestamp in enumerate(timestamps):
        close = 100.0 + (index * 0.18) + (2.0 if index % 17 == 0 else 0.0)
        rows.append(
            {
                "timestamp": timestamp,
                "symbol": "BTC/USDT",
                "open": close - 0.2,
                "high": close + 0.8,
                "low": close - 0.8,
                "close": close,
                "volume": 250.0,
                "spread_bps": 2.0,
                "liquidity_score": 0.85,
                "top_of_book_notional": 60_000.0,
                "quote_age_ms": 100.0,
            }
        )
    stale = rows[-1].copy()
    stale["symbol"] = "ETH/USDT"
    stale["quote_age_ms"] = 9_000.0
    rows.append(stale)
    return pd.DataFrame(rows)


def test_dry_run_proving_records_allowed_and_blocked_actions(tmp_path) -> None:
    payload = run_dry_run_proving_cycle(
        frame=_frame(),
        config=DryRunProvingConfig(
            min_edge_bps=3.0,
            max_order_quantity=0.01,
            output_root=tmp_path,
        ),
    )

    assert payload["live_trading_enabled"] is False
    assert payload["order_proposals"]
    assert payload["allowed_action_count"] >= 1
    assert payload["blocked_action_count"] >= 1
    assert "STALE_BOOK" in payload["block_reasons"]
    assert "MISSING_REPLAY_REALISM_EVIDENCE" not in payload["readiness"]["blockers"]
    assert (tmp_path / "reports" / "sequence2" / "proving" / "latest_proving_summary.json").exists()
    assert (tmp_path / "reports" / "sequence2" / "proving" / "latest_proving_summary.md").exists()


def test_dry_run_proving_handles_missing_quote_age_column(tmp_path) -> None:
    payload = run_dry_run_proving_cycle(
        frame=_frame().drop(columns=["quote_age_ms"]),
        config=DryRunProvingConfig(output_root=tmp_path, min_edge_bps=3.0),
    )

    assert payload["live_trading_enabled"] is False
    assert "STALE_BOOK" not in payload["block_reasons"]


def test_degraded_expectancy_downgrades_proving_state() -> None:
    readiness = evaluate_sequence2_readiness(
        walk_forward_summary={
            "status": "WARN",
            "aggregate": {"mean_test_expectancy_after_costs_bps": -3.0},
            "warnings": ["EDGE_DEGRADATION"],
            "live_trading_enabled": False,
        },
        proving_summary={
            "status": "PROVING",
            "cycle_count": 4,
            "blocked_action_count": 0,
            "replay_to_dry_run_drift_bps": 1.0,
            "warnings": [],
            "live_trading_enabled": False,
        },
        validation_summary={
            "status": "PASS",
            "unsafe_action_failure_count": 0,
            "live_trading_enabled": False,
        },
        realism_summary={"status": "PASS", "live_trading_enabled": False},
    )

    assert readiness["status"] == Sequence2ReadinessStatus.PROVING_WITH_WARNINGS.value
    assert "EDGE_DEGRADATION" in readiness["warnings"]


def test_drift_downgrades_dry_run_proving_status(tmp_path) -> None:
    payload = run_dry_run_proving_cycle(
        frame=_frame(),
        config=DryRunProvingConfig(
            min_edge_bps=3.0,
            max_drift_bps=1.0,
            output_root=tmp_path,
        ),
        walk_forward_summary={
            "status": "PASS",
            "aggregate": {"mean_test_expectancy_after_costs_bps": -100.0},
            "warnings": [],
            "live_trading_enabled": False,
        },
    )

    assert payload["status"] == Sequence2ReadinessStatus.BLOCKED.value
    assert "REPLAY_DRY_RUN_DRIFT_TOO_HIGH" in payload["warnings"]


def test_drift_blocks_readiness() -> None:
    readiness = evaluate_sequence2_readiness(
        walk_forward_summary={
            "status": "PASS",
            "aggregate": {"mean_test_expectancy_after_costs_bps": 2.0},
            "warnings": [],
            "live_trading_enabled": False,
        },
        proving_summary={
            "status": "PROVING",
            "cycle_count": 4,
            "blocked_action_count": 0,
            "replay_to_dry_run_drift_bps": 25.0,
            "warnings": [],
            "live_trading_enabled": False,
        },
        validation_summary={
            "status": "PASS",
            "unsafe_action_failure_count": 0,
            "live_trading_enabled": False,
        },
        realism_summary={"status": "PASS", "live_trading_enabled": False},
        max_drift_bps=10.0,
    )

    assert readiness["status"] == Sequence2ReadinessStatus.BLOCKED.value
    assert "REPLAY_DRY_RUN_DRIFT_TOO_HIGH" in readiness["blockers"]


def test_expected_adversarial_validation_failure_warns_without_blocking() -> None:
    readiness = evaluate_sequence2_readiness(
        walk_forward_summary={
            "status": "PASS",
            "aggregate": {"mean_test_expectancy_after_costs_bps": 2.0},
            "warnings": [],
            "live_trading_enabled": False,
        },
        proving_summary={
            "status": "PROVING",
            "cycle_count": 3,
            "blocked_action_count": 0,
            "replay_to_dry_run_drift_bps": 1.0,
            "warnings": [],
            "live_trading_enabled": False,
        },
        validation_summary={
            "status": "FAIL",
            "failed_scenarios": ["missing_explanation_validation_fail"],
            "unsafe_action_failure_count": 1,
            "live_trading_enabled": False,
        },
        realism_summary={"status": "PASS", "live_trading_enabled": False},
    )

    assert (
        readiness["status"]
        == Sequence2ReadinessStatus.PROVING_WITH_WARNINGS.value
    )
    assert "EXPECTED_ADVERSARIAL_VALIDATION_FAILURE_CAUGHT" in readiness["warnings"]
    assert "VALIDATION_UNSAFE_ACTIONS_PRESENT" not in readiness["blockers"]


def test_missing_evidence_cannot_produce_ready_state() -> None:
    readiness = evaluate_sequence2_readiness()

    assert readiness["status"] == Sequence2ReadinessStatus.NOT_READY.value
    assert "MISSING_WALK_FORWARD_EVIDENCE" in readiness["blockers"]
    assert "MISSING_REPLAY_REALISM_EVIDENCE" in readiness["blockers"]
    assert readiness["live_allowed"] is False


def test_readiness_report_loads_latest_evidence_files(tmp_path) -> None:
    walk_forward_root = tmp_path / "reports" / "sequence2" / "walk_forward"
    proving_root = tmp_path / "reports" / "sequence2" / "proving"
    realism_root = tmp_path / "reports" / "sequence2" / "replay_realism"
    validation_root = tmp_path / "reports" / "validation"
    walk_forward_root.mkdir(parents=True)
    proving_root.mkdir(parents=True)
    realism_root.mkdir(parents=True)
    validation_root.mkdir(parents=True)
    (walk_forward_root / "latest_walk_forward.json").write_text(
        json.dumps(
            {
                "status": "PASS",
                "aggregate": {"mean_test_expectancy_after_costs_bps": 2.0},
                "warnings": [],
                "live_trading_enabled": False,
            }
        ),
        encoding="utf-8",
    )
    (proving_root / "latest_proving_summary.json").write_text(
        json.dumps(
            {
                "status": "PROVING",
                "cycle_count": 3,
                "blocked_action_count": 0,
                "replay_to_dry_run_drift_bps": 1.0,
                "warnings": [],
                "live_trading_enabled": False,
            }
        ),
        encoding="utf-8",
    )
    (validation_root / "latest_summary.json").write_text(
        json.dumps(
            {
                "status": "PASS",
                "unsafe_action_failure_count": 0,
                "live_trading_enabled": False,
            }
        ),
        encoding="utf-8",
    )
    (realism_root / "latest_realism_report.json").write_text(
        json.dumps({"status": "PASS", "live_trading_enabled": False}),
        encoding="utf-8",
    )

    payload = write_sequence2_readiness_report(output_root=tmp_path)

    assert (
        payload["status"]
        == Sequence2ReadinessStatus.CONDITIONALLY_READY_FOR_TINY_MANUAL_CANARY.value
    )
    assert payload["live_allowed"] is False
