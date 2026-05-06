from __future__ import annotations

from pathlib import Path

PHASE27_FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "prediction_markets"
    / "activity"
    / "polymarket_real_cached_activity_oos_sample.json"
)


def test_sequence27_reference_context_alignment_and_quality_are_offline_safe(
    local_project: Path,
) -> None:
    from quant_os.data.prediction_markets.activity_capture import (
        build_activity_dataset_from_capture,
    )
    from quant_os.research.prediction_markets.reference_alignment import (
        build_reference_alignment,
        write_reference_context_report,
    )
    from quant_os.research.prediction_markets.reference_quality import (
        evaluate_reference_quality,
        write_reference_quality_report,
    )

    dataset = build_activity_dataset_from_capture(PHASE27_FIXTURE)
    alignment = build_reference_alignment(dataset)
    quality = evaluate_reference_quality(dataset=dataset, alignment=alignment)

    assert alignment["sequence"] == "27"
    assert alignment["reference_context_status"] == "REFERENCE_CONTEXT_ATTACHED_WITH_GAPS"
    assert alignment["summary"]["market_count"] == 28
    assert alignment["summary"]["attached_reference_count"] == 26
    assert alignment["summary"]["missing_reference_count"] == 2
    assert alignment["summary"]["aligned_resolved_count"] == 24
    assert alignment["internet_required"] is False
    assert alignment["execution_authority"] == "NONE"

    by_market = {item["market_id"]: item for item in alignment["market_reference_alignment"]}
    assert by_market["pm-oos-weather-unresolved-01"]["reference_status"] == "MISSING_REFERENCE_CONTEXT"
    assert by_market["pm-oos-weather-unresolved-01"]["alignment_status"] == "MISSING_CONTEXT"
    assert by_market["pm-oos-weather-yes-01"]["alignment_status"] == "ALIGNED_RESOLVED"
    assert by_market["pm-oos-weather-yes-01"]["provenance"]["source_sha256"]

    assert quality["reference_quality_status"] == "REFERENCE_CONTEXT_USABLE_WITH_WARNINGS"
    assert quality["summary"]["usable_reference_count"] == 24
    assert quality["summary"]["missing_reference_count"] == 2
    assert quality["summary"]["weak_reference_count"] == 2
    assert "MISSING_REFERENCE_CONTEXT_PRESENT" in quality["warnings"]
    assert "WEAK_REFERENCE_OR_LABEL_CONFIDENCE_PRESENT" in quality["warnings"]

    context_report = write_reference_context_report(
        fixture_path=PHASE27_FIXTURE,
        output_root=local_project,
    )
    quality_report = write_reference_quality_report(
        fixture_path=PHASE27_FIXTURE,
        output_root=local_project,
    )
    for payload in (context_report, quality_report):
        assert Path(payload["report_paths"]["json"]).exists()
        markdown = Path(payload["report_paths"]["markdown"]).read_text("utf-8")
        assert "Research-only" in markdown
        assert "No execution authority" in markdown


def test_sequence27_market_quality_filters_flag_suspicious_conditions(
    local_project: Path,
) -> None:
    from quant_os.data.prediction_markets.activity_capture import (
        build_activity_dataset_from_capture,
    )
    from quant_os.research.prediction_markets.manipulation_flags import (
        write_manipulation_flags_report,
    )
    from quant_os.research.prediction_markets.market_quality_filters import (
        evaluate_market_quality_filters,
        write_market_quality_filter_report,
    )

    dataset = build_activity_dataset_from_capture(PHASE27_FIXTURE)
    filters = evaluate_market_quality_filters(dataset)

    assert filters["sequence"] == "27"
    assert filters["market_quality_status"] == "MARKET_QUALITY_FILTERED_RESEARCH_ONLY"
    assert filters["summary"]["market_count"] == 28
    assert filters["summary"]["included_market_count"] == 26
    assert filters["summary"]["quality_filtered_count"] < 26
    assert filters["summary"]["flagged_market_count"] > 0
    assert filters["summary"]["excluded_from_signal_testing_count"] > 0
    assert "FILTERING_REDUCES_SAMPLE_SIZE" in filters["warnings"]
    assert filters["execution_authority"] == "NONE"

    by_market = {item["market_id"]: item for item in filters["market_quality"]}
    assert "MISSING_REFERENCE_CONTEXT" in by_market["pm-oos-weather-unresolved-01"]["quality_flags"]
    assert by_market["pm-oos-ambiguous-excluded-01"]["usable_for_signal_testing"] is False
    assert by_market["pm-oos-outside-lane-01"]["usable_for_signal_testing"] is False

    report = write_market_quality_filter_report(
        fixture_path=PHASE27_FIXTURE,
        output_root=local_project,
    )
    manipulation = write_manipulation_flags_report(
        fixture_path=PHASE27_FIXTURE,
        output_root=local_project,
    )
    assert manipulation["summary"]["flagged_market_count"] == filters["summary"]["flagged_market_count"]
    for payload in (report, manipulation):
        assert Path(payload["report_paths"]["json"]).exists()
        markdown = Path(payload["report_paths"]["markdown"]).read_text("utf-8")
        assert "Research-only" in markdown
        assert "No execution authority" in markdown


def test_sequence27_venue_signal_families_are_interpretable_and_blocked_when_weak(
    local_project: Path,
) -> None:
    from quant_os.data.prediction_markets.activity_capture import (
        build_activity_dataset_from_capture,
    )
    from quant_os.research.prediction_markets.venue_signals import (
        VENUE_SIGNAL_FAMILIES,
        evaluate_venue_signal_oos,
        write_venue_signal_report,
    )

    dataset = build_activity_dataset_from_capture(PHASE27_FIXTURE)
    evaluation = evaluate_venue_signal_oos(dataset)

    assert evaluation["sequence"] == "27"
    assert evaluation["venue_signal_status"] == "BASELINES_NOT_BEATEN"
    assert evaluation["lane_id"] == "short_dated_clean_binary"
    assert evaluation["resolved_observation_count"] == 24
    assert evaluation["oos_observation_count"] == 12
    assert evaluation["quality_filtered_observation_count"] < 24
    assert evaluation["candidate_signal_survives_oos"] is False
    assert evaluation["market_baseline_dominant"] is True
    assert evaluation["baseline_names"] == [
        "naive_50_50",
        "current_market_probability",
        "simple_calibrated_heuristic",
        "best_generic_dynamic_family",
    ]
    assert len(VENUE_SIGNAL_FAMILIES) >= 4
    for family in VENUE_SIGNAL_FAMILIES:
        assert family["plain_english_explanation"]
        assert family["what_it_measures"]
        assert family["why_it_might_work"]
        assert family["why_it_might_fail"]
        assert family["failure_mode_notes"]
        assert family["opaque_model"] is False
    for result in evaluation["candidate_results"].values():
        assert result["opaque_model"] is False
        assert result["survives_oos"] is False
        assert result["credible_signal_family"] is False
        assert "current_market_probability" in result["oos_baseline_comparisons"]
        assert "best_generic_dynamic_family" in result["oos_baseline_comparisons"]

    report = write_venue_signal_report(
        fixture_path=PHASE27_FIXTURE,
        output_root=local_project,
    )
    assert report["venue_signal_status"] == "BASELINES_NOT_BEATEN"
    assert Path(report["report_paths"]["json"]).exists()
    markdown = Path(report["report_paths"]["markdown"]).read_text("utf-8")
    assert "Research-only" in markdown
    assert "No execution authority" in markdown


def test_sequence27_ablation_preserves_oos_discipline_and_prevents_filter_cherry_picking(
    local_project: Path,
) -> None:
    from quant_os.data.prediction_markets.activity_capture import (
        build_activity_dataset_from_capture,
    )
    from quant_os.research.prediction_markets.ablation import (
        evaluate_venue_signal_ablation,
        write_ablation_report,
    )
    from quant_os.research.prediction_markets.venue_signals import evaluate_venue_signal_oos

    dataset = build_activity_dataset_from_capture(PHASE27_FIXTURE)
    evaluation = evaluate_venue_signal_oos(dataset)
    ablation = evaluate_venue_signal_ablation(dataset=dataset, venue_evaluation=evaluation)

    assert ablation["sequence"] == "27"
    assert ablation["ablation_status"] == "NO_ABLATION_BEATS_MARKET_BASELINE_OOS"
    assert ablation["leakage_check"]["passed"] is True
    assert ablation["components"]["reference_context"]["oos_brier_improvement_vs_market"] <= 0
    assert ablation["components"]["market_quality_filters"]["filtered_observation_count"] < 24
    assert ablation["components"]["market_quality_filters"]["performance_inflation_allowed"] is False
    assert ablation["components"]["wallet_flow_after_filtering"]["oos_brier_improvement_vs_market"] <= 0
    assert "FILTERED_SAMPLE_TOO_SMALL_FOR_WIN_CLAIM" in ablation["warnings"]

    report = write_ablation_report(
        fixture_path=PHASE27_FIXTURE,
        output_root=local_project,
    )
    assert report["ablation_status"] == "NO_ABLATION_BEATS_MARKET_BASELINE_OOS"
    assert Path(report["report_paths"]["json"]).exists()
    markdown = Path(report["report_paths"]["markdown"]).read_text("utf-8")
    assert "Research-only" in markdown
    assert "No execution authority" in markdown


def test_sequence27_lane_decision_can_retire_candidate_and_blocks_minimal_replay(
    local_project: Path,
) -> None:
    from quant_os.data.prediction_markets.activity_capture import (
        build_activity_dataset_from_capture,
    )
    from quant_os.research.prediction_markets.ablation import evaluate_venue_signal_ablation
    from quant_os.research.prediction_markets.lane_decision import (
        evaluate_lane_decision,
        write_lane_decision_report,
    )
    from quant_os.research.prediction_markets.replay_feasibility import (
        REPLAY_FEASIBILITY_SAFETY,
        evaluate_venue_replay_readiness,
    )
    from quant_os.research.prediction_markets.replay_feasibility_report import (
        write_venue_replay_readiness_report,
    )
    from quant_os.research.prediction_markets.venue_signals import evaluate_venue_signal_oos

    dataset = build_activity_dataset_from_capture(PHASE27_FIXTURE)
    venue_evaluation = evaluate_venue_signal_oos(dataset)
    ablation = evaluate_venue_signal_ablation(
        dataset=dataset,
        venue_evaluation=venue_evaluation,
    )
    decision = evaluate_lane_decision(
        dataset=dataset,
        venue_evaluation=venue_evaluation,
        ablation=ablation,
    )
    readiness = evaluate_venue_replay_readiness(
        lane_activity_dataset=dataset,
        venue_evaluation=venue_evaluation,
        ablation=ablation,
        lane_decision=decision,
    )

    assert decision["lane_decision_status"] == "LANE_RETIRE_CANDIDATE"
    assert decision["recommended_action"] == "DEPRIORITIZE_SHORT_DATED_CLEAN_BINARY"
    assert decision["best_candidate_lane"]["lane_id"] == "short_dated_clean_binary"
    assert "NO_CREDIBLE_SIGNAL_FAMILY" in decision["blockers"]
    assert "BASELINES_NOT_BEATEN" in decision["blockers"]
    assert decision["ready_for_minimal_replay_spec"] is False

    assert readiness["replay_readiness_status"] == "LANE_RETIRE_CANDIDATE"
    assert readiness["ready_for_minimal_replay_spec"] is False
    assert readiness["ready_for_narrow_replay_design"] is False
    assert "NO_CREDIBLE_SIGNAL_FAMILY" in readiness["blockers"]
    assert "BASELINES_NOT_BEATEN" in readiness["blockers"]
    assert readiness["live_trading_enabled"] is False
    assert readiness["execution_authority"] == "NONE"

    optimistic_venue = {
        **venue_evaluation,
        "venue_signal_status": "CANDIDATE_SIGNAL_SURVIVES_OOS",
        "candidate_signal_survives_oos": True,
    }
    bad_reference_decision = evaluate_lane_decision(
        dataset={**dataset, "resolved_market_count": 24},
        venue_evaluation={
            **optimistic_venue,
            "reference_quality_status": "REFERENCE_CONTEXT_INSUFFICIENT",
        },
        ablation={**ablation, "ablation_status": "REFERENCE_CONTEXT_INSUFFICIENT"},
    )
    assert bad_reference_decision["ready_for_minimal_replay_spec"] is False
    assert "REFERENCE_CONTEXT_INSUFFICIENT" in bad_reference_decision["blockers"]

    lane_report = write_lane_decision_report(
        fixture_path=PHASE27_FIXTURE,
        output_root=local_project,
    )
    readiness_report = write_venue_replay_readiness_report(
        fixture_path=PHASE27_FIXTURE,
        output_root=local_project,
    )
    for payload in (lane_report, readiness_report):
        assert Path(payload["report_paths"]["json"]).exists()
        markdown = Path(payload["report_paths"]["markdown"]).read_text("utf-8")
        assert "Research-only" in markdown
        assert "No execution authority" in markdown

    for safety in (REPLAY_FEASIBILITY_SAFETY, readiness):
        assert safety["execution_authority"] == "NONE"
        assert safety["wallet_signing_enabled"] is False
        assert safety["live_trading_enabled"] is False
        assert safety["copy_trading_enabled"] is False
        assert safety["real_orders_enabled"] is False
