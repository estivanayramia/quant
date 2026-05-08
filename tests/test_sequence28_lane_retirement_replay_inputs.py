from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PREDICTION_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "prediction_markets"
BENCHMARK_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "benchmark_sources"
OOS_ACTIVITY_FIXTURE = (
    PREDICTION_FIXTURE_ROOT
    / "activity"
    / "polymarket_real_cached_activity_oos_sample.json"
)


def test_sequence28_formalizes_lane_deprioritization_without_live_promotion(
    local_project: Path,
) -> None:
    from quant_os.research.prediction_markets.lane_retirement import (
        write_lane_retirement_report,
    )

    payload = write_lane_retirement_report(
        fixture_path=OOS_ACTIVITY_FIXTURE,
        output_root=local_project,
    )

    assert payload["lane_id"] == "short_dated_clean_binary"
    assert payload["lane_retirement_status"] == "LANE_DEPRIORITIZED"
    assert payload["recommended_action"] == "DEPRIORITIZE_SHORT_DATED_CLEAN_BINARY"
    assert payload["replay_ready"] is False
    assert "BASELINES_NOT_BEATEN" in payload["blockers"]
    assert payload["why_merging_improves_honesty"]
    assert payload["live_trading_enabled"] is False
    assert payload["execution_authority"] == "NONE"
    assert payload["live_promotion_status"] == "LIVE_BLOCKED"
    assert (
        local_project
        / "reports"
        / "sequence28"
        / "lane_retirement"
        / "latest_lane_retirement.json"
    ).exists()


def test_sequence28_selects_replay_inputs_before_forcing_another_lane(
    local_project: Path,
) -> None:
    from quant_os.research.next_lane_selection_v2 import write_next_lane_selection_report

    payload = write_next_lane_selection_report(output_root=local_project)

    assert payload["selection_status"] == "BUILD_REPLAY_INPUTS_BEFORE_LANE_PROMOTION"
    assert payload["selected_lane_id"] == "prediction_market_replay_input_infrastructure"
    assert payload["selected_lane"]["live_execution_allowed"] is False
    assert payload["current_lane"]["lane_id"] == "short_dated_clean_binary"
    assert payload["current_lane"]["status"] == "DEPRIORITIZED"
    assert "required_data" in payload["selected_lane"]
    assert "validation_blockers" in payload["selected_lane"]
    assert payload["prediction_market_execution_authority_added"] is False
    assert payload["live_trading_enabled"] is False


def test_sequence28_normalizes_fixture_safe_replay_input_events(
    local_project: Path,
) -> None:
    from quant_os.replay.prediction_market_replay_inputs import (
        normalize_replay_inputs,
        write_replay_input_summary,
    )

    events = normalize_replay_inputs(
        polymarket_snapshot_path=BENCHMARK_FIXTURE_ROOT / "polymarket_public_snapshot.json",
        pmxt_manifest_path=BENCHMARK_FIXTURE_ROOT / "pmxt_manifest.json",
        reference_datasets_manifest_path=BENCHMARK_FIXTURE_ROOT / "reference_datasets_manifest.json",
    )
    event_dicts = [event.to_report_dict() for event in events]
    event_types = {event["event_type"] for event in event_dicts}

    assert {"market_state", "orderbook_snapshot", "trade"} <= event_types
    assert "orderbook_archive_manifest" in event_types
    assert "reference_dataset_manifest" in event_types
    assert all(event["source_id"] for event in event_dicts)
    assert all(event["provenance"] for event in event_dicts)

    trade = next(event for event in event_dicts if event["event_type"] == "trade")
    assert trade["timestamp"] == "2025-01-01T00:00:00+00:00"
    assert trade["condition_id"] == "0xabc"
    assert trade["slug"] == "sample-market"
    assert trade["token_id"] == "yes-token"
    assert trade["trade_price"] == "0.43"
    assert trade["trade_size"] == "5"

    orderbook = next(event for event in event_dicts if event["event_type"] == "orderbook_snapshot")
    assert orderbook["best_bid_price"] == "0.42"
    assert orderbook["best_ask_price"] == "0.44"
    assert orderbook["best_bid_size"] == "10"
    assert orderbook["best_ask_size"] == "12"

    summary = write_replay_input_summary(
        output_root=local_project,
        polymarket_snapshot_path=BENCHMARK_FIXTURE_ROOT / "polymarket_public_snapshot.json",
        pmxt_manifest_path=BENCHMARK_FIXTURE_ROOT / "pmxt_manifest.json",
        reference_datasets_manifest_path=BENCHMARK_FIXTURE_ROOT / "reference_datasets_manifest.json",
    )

    assert summary["status"] == "PASS"
    assert summary["event_counts"]["orderbook_snapshot"] == 1
    assert summary["event_counts"]["trade"] == 1
    assert summary["live_trading_enabled"] is False
    assert summary["prediction_market_execution_authority_added"] is False
    assert any("queue position" in limitation.lower() for limitation in summary["limitations"])
    assert (
        local_project
        / "reports"
        / "sequence28"
        / "replay_inputs"
        / "latest_replay_inputs_summary.json"
    ).exists()


def test_sequence28_replay_input_normalization_degrades_missing_fields_gracefully(
    tmp_path: Path,
) -> None:
    from quant_os.replay.prediction_market_replay_inputs import normalize_replay_inputs

    thin_snapshot = tmp_path / "thin_snapshot.json"
    thin_snapshot.write_text(
        """
{
  "markets": [{"market_slug": "thin-market", "tokens": [{"outcome": "Yes"}]}],
  "orderbooks": [{"market": "thin-market", "token_id": "yes-token", "bids": [], "asks": []}],
  "trades": [{"market": "thin-market", "token_id": "yes-token"}]
}
""".strip(),
        encoding="utf-8",
    )

    events = normalize_replay_inputs(polymarket_snapshot_path=thin_snapshot)
    flags = {
        flag
        for event in events
        for flag in event.quality_flags
    }

    assert "missing_timestamp" in flags
    assert "missing_condition_id" in flags
    assert "empty_orderbook_side" in flags
    assert "missing_trade_price" in flags
    assert "missing_trade_size" in flags


def test_sequence28_replay_input_readiness_stays_research_only_and_conservative(
    local_project: Path,
) -> None:
    from quant_os.research.prediction_markets.replay_input_readiness import (
        write_replay_input_readiness_report,
    )

    payload = write_replay_input_readiness_report(
        output_root=local_project,
        polymarket_snapshot_path=BENCHMARK_FIXTURE_ROOT / "polymarket_public_snapshot.json",
        pmxt_manifest_path=BENCHMARK_FIXTURE_ROOT / "pmxt_manifest.json",
        reference_datasets_manifest_path=BENCHMARK_FIXTURE_ROOT / "reference_datasets_manifest.json",
    )

    assert payload["replay_input_readiness_status"] == "REPLAY_INPUTS_PARTIAL"
    assert payload["ready_for_narrow_replay_design"] is False
    assert payload["not_live_readiness"] is True
    assert payload["not_profitability_evidence"] is True
    assert "REPLAY_LIMITATIONS_UNMODELED" in payload["blockers"]
    assert payload["live_trading_enabled"] is False
    assert payload["execution_authority"] == "NONE"


def test_sequence28_cli_commands_are_offline_and_support_only(local_project: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = {
        **os.environ,
        "PYTHONPATH": str(repo_root / "src"),
    }
    commands = [
        [
            sys.executable,
            "-m",
            "quant_os.cli",
            "research",
            "lane-retirement",
            "--fixture-path",
            str(OOS_ACTIVITY_FIXTURE),
        ],
        [sys.executable, "-m", "quant_os.cli", "research", "next-lane-selection-v2"],
        [
            sys.executable,
            "-m",
            "quant_os.cli",
            "research",
            "replay-input-summary",
            "--polymarket-snapshot-path",
            str(BENCHMARK_FIXTURE_ROOT / "polymarket_public_snapshot.json"),
            "--pmxt-manifest-path",
            str(BENCHMARK_FIXTURE_ROOT / "pmxt_manifest.json"),
            "--reference-datasets-manifest-path",
            str(BENCHMARK_FIXTURE_ROOT / "reference_datasets_manifest.json"),
        ],
        [
            sys.executable,
            "-m",
            "quant_os.cli",
            "research",
            "replay-input-readiness",
            "--polymarket-snapshot-path",
            str(BENCHMARK_FIXTURE_ROOT / "polymarket_public_snapshot.json"),
            "--pmxt-manifest-path",
            str(BENCHMARK_FIXTURE_ROOT / "pmxt_manifest.json"),
            "--reference-datasets-manifest-path",
            str(BENCHMARK_FIXTURE_ROOT / "reference_datasets_manifest.json"),
        ],
    ]

    for command in commands:
        result = subprocess.run(
            command,
            cwd=local_project,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        assert "live_trading_enabled" in result.stdout
        assert "False" in result.stdout
