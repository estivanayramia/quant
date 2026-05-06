from __future__ import annotations

from pathlib import Path

PHASE24_ACTIVITY_FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "prediction_markets"
    / "activity"
    / "polymarket_short_dated_lane_activity_sample.json"
)
REAL_CACHED_ACTIVITY_FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "prediction_markets"
    / "activity"
    / "polymarket_real_cached_activity_sample.json"
)


def test_polymarket_activity_capture_is_read_only_manual_and_provenance_safe(
    local_project: Path,
) -> None:
    from quant_os.data.prediction_markets.activity_capture import (
        ACTIVITY_CAPTURE_SAFETY,
        capture_polymarket_activity,
    )
    from quant_os.data.prediction_markets.polymarket_activity_provider import (
        PolymarketActivityProvider,
    )

    blocked = capture_polymarket_activity(fixture_path=None)
    manual_not_explicit = capture_polymarket_activity(
        fixture_path=None,
        manual_network=True,
        explicit_network_ack=False,
    )
    captured = capture_polymarket_activity(
        fixture_path=REAL_CACHED_ACTIVITY_FIXTURE,
        output_root=local_project,
    )
    provider = PolymarketActivityProvider(http_client=None)
    provider_blocked = provider.fetch_activity(
        lane_id="short_dated_clean_binary",
        manual_network=False,
        explicit_network_ack=False,
    )

    assert blocked["status"] == "BLOCKED"
    assert blocked["reason"] == "MANUAL_NETWORK_NOT_REQUESTED"
    assert manual_not_explicit["status"] == "BLOCKED"
    assert manual_not_explicit["reason"] == "EXPLICIT_NETWORK_ACK_REQUIRED"
    assert provider_blocked["status"] == "BLOCKED"
    assert provider_blocked["network_fetch_attempted"] is False

    assert captured["status"] == "CAPTURED_FROM_SAVED_ARTIFACT"
    assert captured["source_mode"] == "real_cached"
    assert captured["raw_event_count"] == 62
    assert captured["usable_event_count"] == 60
    assert captured["raw_payload_sha256"]
    assert captured["normalized_artifact"]["source_mode"] == "real_cached"
    assert Path(captured["artifact_path"]).exists()
    assert Path(captured["report_paths"]["json"]).exists()

    assert ACTIVITY_CAPTURE_SAFETY["execution_authority"] == "NONE"
    assert ACTIVITY_CAPTURE_SAFETY["wallet_signing_enabled"] is False
    assert ACTIVITY_CAPTURE_SAFETY["live_trading_enabled"] is False
    assert ACTIVITY_CAPTURE_SAFETY["copy_trading_enabled"] is False
    assert ACTIVITY_CAPTURE_SAFETY["real_orders_enabled"] is False


def test_activity_events_normalize_order_and_reject_bad_records() -> None:
    from quant_os.data.prediction_markets.activity_capture import load_activity_capture
    from quant_os.data.prediction_markets.activity_events import (
        ACTIVITY_EVENT_SAFETY,
        normalize_activity_events,
    )

    payload = load_activity_capture(REAL_CACHED_ACTIVITY_FIXTURE)
    normalized = normalize_activity_events(payload)

    assert normalized["raw_event_count"] == 62
    assert normalized["usable_event_count"] == 60
    assert normalized["malformed_event_count"] == 2
    assert normalized["timestamp_problem_count"] == 1
    assert normalized["missing_critical_field_count"] == 1
    assert normalized["event_type_counts"]["trade"] == 12
    assert normalized["event_type_counts"]["order_book_snapshot"] == 12
    assert normalized["event_type_counts"]["resolution_update"] == 11
    timestamps = [event["timestamp"] for event in normalized["events"]]
    assert timestamps == sorted(timestamps)

    rejected_by_id = {event["event_id"]: event for event in normalized["rejected_events"]}
    assert rejected_by_id["evt-bad-missing-price"]["usable"] is False
    assert "MISSING_PRICE" in rejected_by_id["evt-bad-missing-price"]["quality_flags"]
    assert "BAD_TIMESTAMP" in rejected_by_id["evt-bad-timestamp"]["quality_flags"]

    assert ACTIVITY_EVENT_SAFETY["execution_authority"] == "NONE"
    assert ACTIVITY_EVENT_SAFETY["wallet_signing_enabled"] is False
    assert ACTIVITY_EVENT_SAFETY["real_orders_enabled"] is False


def test_real_cached_lane_dataset_growth_and_quality_reports(local_project: Path) -> None:
    from quant_os.data.prediction_markets.activity_capture import (
        build_activity_dataset_from_capture,
    )
    from quant_os.research.prediction_markets.activity_dataset_growth import (
        write_activity_dataset_growth_report,
    )
    from quant_os.research.prediction_markets.lane_activity_dataset import (
        write_sequence25_activity_dataset_report,
    )
    from quant_os.research.prediction_markets.lane_activity_quality import (
        evaluate_lane_activity_quality,
        write_lane_activity_quality_report,
    )

    dataset = build_activity_dataset_from_capture(REAL_CACHED_ACTIVITY_FIXTURE)
    repeated = build_activity_dataset_from_capture(REAL_CACHED_ACTIVITY_FIXTURE)
    quality = evaluate_lane_activity_quality(dataset)

    assert dataset == repeated
    assert dataset["sequence"] == "25"
    assert dataset["source_mode"] == "real_cached"
    assert dataset["activity_source_mode_counts"]["real_cached"] == 60
    assert dataset["market_count"] == 12
    assert dataset["included_market_count"] == 11
    assert dataset["resolved_market_count"] == 10
    assert dataset["activity_observation_count"] == 60
    assert dataset["raw_event_count"] == 62
    assert dataset["usable_event_count"] == 60
    assert dataset["malformed_event_count"] == 2
    assert dataset["activity_depth_status"] == "LANE_ACTIVITY_ENRICHED"
    assert dataset["real_activity_status"] == "REAL_CACHED_ACTIVITY_PRESENT"

    by_market = {market["market_id"]: market for market in dataset["markets"]}
    assert by_market["pm-real-ambiguous-excluded-01"]["exclusion_reason"] == "AMBIGUOUS"
    assert by_market["pm-real-weather-yes-01"]["provenance"]["raw_payload_sha256"]
    assert by_market["pm-real-weather-yes-01"]["activity_density"]["usable_event_count"] == 5

    assert quality["activity_quality_status"] == "REAL_CACHED_ACTIVITY_USABLE_BUT_REPLAY_LIMITED"
    assert quality["summary"]["min_events_per_included_market"] == 5
    assert quality["summary"]["malformed_event_count"] == 2
    assert "REPLAY_INPUTS_NOT_FULL_ORDER_BOOK_OR_FILL_MODEL" in quality["warnings"]

    dataset_report = write_sequence25_activity_dataset_report(
        fixture_path=REAL_CACHED_ACTIVITY_FIXTURE,
        output_root=local_project,
    )
    growth_report = write_activity_dataset_growth_report(
        previous_fixture_path=PHASE24_ACTIVITY_FIXTURE,
        expanded_fixture_path=REAL_CACHED_ACTIVITY_FIXTURE,
        output_root=local_project,
    )
    quality_report = write_lane_activity_quality_report(
        fixture_path=REAL_CACHED_ACTIVITY_FIXTURE,
        output_root=local_project,
    )
    assert growth_report["market_delta"] == 2
    assert growth_report["resolved_delta"] == 2
    assert growth_report["activity_observation_delta"] == 10
    for payload in (dataset_report, growth_report, quality_report):
        assert Path(payload["report_paths"]["json"]).exists()
        markdown = Path(payload["report_paths"]["markdown"]).read_text("utf-8")
        assert "Research-only" in markdown
        assert "No execution authority" in markdown


def test_sequence25_signal_evaluation_uses_real_cached_activity_but_blocks_weak_signals(
    local_project: Path,
) -> None:
    from quant_os.data.prediction_markets.activity_capture import (
        build_activity_dataset_from_capture,
    )
    from quant_os.research.prediction_markets.evaluation import (
        evaluate_real_activity_signals,
        write_real_activity_signal_evaluation_report,
    )

    dataset = build_activity_dataset_from_capture(REAL_CACHED_ACTIVITY_FIXTURE)
    evaluation = evaluate_real_activity_signals(dataset)

    assert evaluation["sequence"] == "25"
    assert evaluation["source_mode"] == "real_cached"
    assert evaluation["lane_id"] == "short_dated_clean_binary"
    assert evaluation["lane_evaluation_status"] == "BASELINES_NOT_BEATEN"
    assert evaluation["resolved_observation_count"] == 10
    assert evaluation["activity_quality_summary"]["raw_event_count"] == 62
    assert evaluation["baselines"]["current_market_probability"]["observation_count"] == 10
    assert set(evaluation["baselines"]) >= {
        "naive_50_50",
        "current_market_probability",
        "simple_calibrated_heuristic",
    }
    for result in evaluation["candidate_results"].values():
        assert "current_market_probability" in result["baseline_comparisons"]
        assert result["beats_current_market_probability"] is False
        assert result["credible_signal_family"] is False
        assert result["opaque_model"] is False

    report = write_real_activity_signal_evaluation_report(
        fixture_path=REAL_CACHED_ACTIVITY_FIXTURE,
        output_root=local_project,
    )
    assert report["lane_evaluation_status"] == "BASELINES_NOT_BEATEN"
    assert Path(report["report_paths"]["json"]).exists()
    markdown = Path(report["report_paths"]["markdown"]).read_text("utf-8")
    assert "Research-only" in markdown
    assert "No execution authority" in markdown


def test_sequence25_replay_readiness_requires_real_activity_depth_and_baseline_edge(
    local_project: Path,
) -> None:
    from quant_os.data.prediction_markets.activity_capture import (
        build_activity_dataset_from_capture,
    )
    from quant_os.data.prediction_markets.activity_history import build_lane_activity_history
    from quant_os.research.prediction_markets.evaluation import evaluate_real_activity_signals
    from quant_os.research.prediction_markets.replay_feasibility import (
        evaluate_real_activity_replay_readiness,
    )
    from quant_os.research.prediction_markets.replay_feasibility_report import (
        write_real_activity_replay_readiness_report,
    )

    dataset = build_activity_dataset_from_capture(REAL_CACHED_ACTIVITY_FIXTURE)
    evaluation = evaluate_real_activity_signals(dataset)
    readiness = evaluate_real_activity_replay_readiness(
        lane_activity_dataset=dataset,
        lane_evaluation=evaluation,
    )

    assert readiness["sequence"] == "25"
    assert readiness["replay_readiness_status"] == "LANE_IMPROVED_BUT_REPLAY_NOT_READY"
    assert readiness["ready_for_narrow_replay_design"] is False
    assert "INSUFFICIENT_RESOLVED_HISTORY" in readiness["blockers"]
    assert "BASELINES_NOT_BEATEN" in readiness["blockers"]
    assert "SIGNAL_WEAK" in readiness["blockers"]
    assert readiness["best_candidate_lane"]["lane_id"] == "short_dated_clean_binary"
    assert readiness["activity_quality_status"] == "REAL_CACHED_ACTIVITY_USABLE_BUT_REPLAY_LIMITED"
    assert readiness["live_trading_enabled"] is False
    assert readiness["execution_authority"] == "NONE"

    fixture_dataset = build_lane_activity_history(PHASE24_ACTIVITY_FIXTURE)
    fixture_gate = evaluate_real_activity_replay_readiness(
        lane_activity_dataset=fixture_dataset,
        lane_evaluation=evaluate_real_activity_signals(fixture_dataset),
    )
    assert fixture_gate["replay_readiness_status"] == "INSUFFICIENT_REAL_ACTIVITY"
    assert "INSUFFICIENT_REAL_ACTIVITY" in fixture_gate["blockers"]
    assert fixture_gate["ready_for_narrow_replay_design"] is False

    report = write_real_activity_replay_readiness_report(
        fixture_path=REAL_CACHED_ACTIVITY_FIXTURE,
        output_root=local_project,
    )
    assert report["replay_readiness_status"] == "LANE_IMPROVED_BUT_REPLAY_NOT_READY"
    assert Path(report["report_paths"]["json"]).exists()
    markdown = Path(report["report_paths"]["markdown"]).read_text("utf-8")
    assert "Research-only" in markdown
    assert "No execution authority" in markdown


def test_sequence25_adds_no_prediction_market_execution_or_signing_authority() -> None:
    from quant_os.data.prediction_markets.activity_capture import ACTIVITY_CAPTURE_SAFETY
    from quant_os.data.prediction_markets.activity_events import ACTIVITY_EVENT_SAFETY
    from quant_os.data.prediction_markets.polymarket_activity_provider import (
        POLYMARKET_ACTIVITY_PROVIDER_SAFETY,
    )
    from quant_os.research.prediction_markets.replay_feasibility import (
        REPLAY_FEASIBILITY_SAFETY,
    )

    for safety in (
        ACTIVITY_CAPTURE_SAFETY,
        ACTIVITY_EVENT_SAFETY,
        POLYMARKET_ACTIVITY_PROVIDER_SAFETY,
        REPLAY_FEASIBILITY_SAFETY,
    ):
        assert safety["execution_authority"] == "NONE"
        assert safety["wallet_signing_enabled"] is False
        assert safety["live_trading_enabled"] is False
        assert safety["copy_trading_enabled"] is False
        assert safety["real_orders_enabled"] is False
