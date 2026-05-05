from __future__ import annotations

from pathlib import Path

from quant_os.research.crypto.ingest import generate_crypto_fixture


def test_calibrated_edge_report_blocks_weak_fixture_edge(local_project: Path) -> None:
    from quant_os.research.crypto.calibrated_edge_report import write_calibrated_edge_report

    calibration = {
        "status": "WARN",
        "suggested_replay_parameters": {
            "fee_bps": 5.0,
            "slippage_bps": 12.0,
            "min_liquidity_score": 0.35,
            "min_top_of_book_notional": 25_000.0,
            "max_quote_age_ms": 1_000.0,
        },
        "warnings": ["STALE_BOOK_OBSERVED"],
        "blockers": [],
        "live_trading_enabled": False,
    }

    payload = write_calibrated_edge_report(
        generate_crypto_fixture(periods=240),
        calibration_summary=calibration,
        output_root=local_project,
    )

    assert payload["status"] == "BLOCKED"
    assert payload["credibility_status"] == "NOT_CREDIBLE_AFTER_CALIBRATION"
    assert payload["live_trading_enabled"] is False
    assert payload["live_allowed"] is False
    assert payload["live_promotion_status"] == "LIVE_BLOCKED"
    assert "CALIBRATED_OOS_EXPECTANCY_BELOW_THRESHOLD" in payload["blockers"]
    assert "PLACEBO_NOT_BEATEN_AFTER_CALIBRATION" in payload["blockers"]
    assert payload["aggregate"]["mean_test_expectancy_after_costs_bps"] < 0.0
    assert "random_placebo" in payload["baselines"]
    assert (
        local_project
        / "reports"
        / "sequence3"
        / "calibrated_edge"
        / "latest_calibrated_edge.json"
    ).exists()
    assert (
        local_project
        / "reports"
        / "sequence3"
        / "calibrated_edge"
        / "latest_calibrated_edge.md"
    ).exists()


def test_calibrated_edge_inherits_blocked_calibration_without_inflating_readiness(
    local_project: Path,
) -> None:
    from quant_os.research.crypto.calibrated_edge_report import write_calibrated_edge_report

    payload = write_calibrated_edge_report(
        generate_crypto_fixture(periods=120),
        calibration_summary={
            "status": "BLOCKED",
            "suggested_replay_parameters": {"fee_bps": 5.0, "slippage_bps": 5.0},
            "blockers": ["NETWORK_FETCH_REQUIRES_EXPLICIT_FLAG"],
            "warnings": [],
            "live_trading_enabled": False,
        },
        output_root=local_project,
    )

    assert payload["status"] == "BLOCKED"
    assert "VENUE_CALIBRATION_BLOCKED" in payload["blockers"]
    assert payload["live_allowed"] is False
    assert payload["live_promotion_status"] == "LIVE_BLOCKED"
