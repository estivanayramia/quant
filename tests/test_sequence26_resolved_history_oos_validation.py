from __future__ import annotations

from pathlib import Path

PHASE25_ACTIVITY_FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "prediction_markets"
    / "activity"
    / "polymarket_real_cached_activity_sample.json"
)
PHASE26_ACTIVITY_FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "prediction_markets"
    / "activity"
    / "polymarket_real_cached_activity_oos_sample.json"
)


def test_sequence26_resolved_history_growth_is_deterministic_and_diagnostic(
    local_project: Path,
) -> None:
    from quant_os.data.prediction_markets.activity_capture import (
        build_activity_dataset_from_capture,
    )
    from quant_os.research.prediction_markets.resolved_history_growth import (
        evaluate_resolved_history_growth,
        write_resolved_history_growth_report,
    )

    previous_dataset = build_activity_dataset_from_capture(PHASE25_ACTIVITY_FIXTURE)
    expanded_dataset = build_activity_dataset_from_capture(PHASE26_ACTIVITY_FIXTURE)
    repeated = build_activity_dataset_from_capture(PHASE26_ACTIVITY_FIXTURE)
    growth = evaluate_resolved_history_growth(
        previous_dataset=previous_dataset,
        expanded_dataset=expanded_dataset,
    )

    assert expanded_dataset == repeated
    assert expanded_dataset["sequence"] == "26"
    assert expanded_dataset["source_mode"] == "real_cached"
    assert expanded_dataset["lane_id"] == "short_dated_clean_binary"
    assert expanded_dataset["market_count"] == 28
    assert expanded_dataset["included_market_count"] == 26
    assert expanded_dataset["resolved_market_count"] == 24
    assert expanded_dataset["unresolved_market_count"] == 2
    assert expanded_dataset["ambiguous_market_count"] == 1
    assert expanded_dataset["excluded_market_count"] == 2
    assert expanded_dataset["activity_observation_count"] == 135
    assert expanded_dataset["activity_source_mode_counts"]["real_cached"] == 135
    assert expanded_dataset["dataset_hash"]

    assert growth["sequence"] == "26"
    assert growth["resolved_history_status"] == "RESOLVED_HISTORY_EXPANDED_RESEARCH_ONLY"
    assert growth["resolved_delta"] == 14
    assert growth["market_delta"] == 16
    assert growth["expanded_summary"]["resolved_market_count"] == 24
    assert growth["expanded_summary"]["usable_resolved_market_count"] == 24
    assert growth["expanded_summary"]["excluded_market_count"] == 2
    assert growth["inclusion_exclusion_summary"]["AMBIGUOUS"] == 1
    assert growth["inclusion_exclusion_summary"]["OUTSIDE_TARGET_LANE"] == 1
    assert growth["ready_for_narrow_replay_design"] is False
    assert growth["execution_authority"] == "NONE"

    report = write_resolved_history_growth_report(
        previous_fixture_path=PHASE25_ACTIVITY_FIXTURE,
        expanded_fixture_path=PHASE26_ACTIVITY_FIXTURE,
        output_root=local_project,
    )
    assert report["resolved_delta"] == 14
    assert Path(report["report_paths"]["json"]).exists()
    markdown = Path(report["report_paths"]["markdown"]).read_text("utf-8")
    assert "Research-only" in markdown
    assert "No execution authority" in markdown


def test_sequence26_label_quality_distinguishes_confident_weak_and_excluded(
    local_project: Path,
) -> None:
    from quant_os.data.prediction_markets.activity_capture import (
        build_activity_dataset_from_capture,
    )
    from quant_os.research.prediction_markets.label_quality import (
        evaluate_label_quality,
        write_label_quality_report,
    )

    dataset = build_activity_dataset_from_capture(PHASE26_ACTIVITY_FIXTURE)
    quality = evaluate_label_quality(dataset)

    assert quality["sequence"] == "26"
    assert quality["label_quality_status"] == "LABELS_USABLE_FOR_OOS_RESEARCH"
    assert quality["summary"]["confidently_resolved_count"] == 22
    assert quality["summary"]["weakly_resolved_count"] == 2
    assert quality["summary"]["unresolved_count"] == 2
    assert quality["summary"]["ambiguous_count"] == 1
    assert quality["summary"]["excluded_count"] == 2
    assert quality["summary"]["usable_resolved_label_count"] == 24
    assert quality["summary"]["missing_reference_context_count"] == 2
    assert quality["summary"]["incomplete_activity_history_count"] == 0
    assert quality["exclusion_reasons"]["AMBIGUOUS"] == 1
    assert quality["exclusion_reasons"]["OUTSIDE_TARGET_LANE"] == 1
    assert "WEAK_LABEL_CONFIDENCE_PRESENT" in quality["warnings"]
    assert quality["ready_for_narrow_replay_design"] is False

    by_market = {item["market_id"]: item for item in quality["market_label_quality"]}
    assert by_market["pm-oos-politics-weak-01"]["label_quality_status"] == "WEAKLY_RESOLVED"
    assert by_market["pm-oos-weather-unresolved-01"]["label_quality_status"] == "UNRESOLVED"
    assert by_market["pm-oos-ambiguous-excluded-01"]["label_quality_status"] == "AMBIGUOUS"
    assert by_market["pm-oos-outside-lane-01"]["label_quality_status"] == "EXCLUDED"

    report = write_label_quality_report(
        fixture_path=PHASE26_ACTIVITY_FIXTURE,
        output_root=local_project,
    )
    assert report["label_quality_status"] == "LABELS_USABLE_FOR_OOS_RESEARCH"
    assert Path(report["report_paths"]["json"]).exists()
    markdown = Path(report["report_paths"]["markdown"]).read_text("utf-8")
    assert "Research-only" in markdown
    assert "No execution authority" in markdown


def test_sequence26_lane_oos_validation_is_chronological_and_blocks_in_sample_hope(
    local_project: Path,
) -> None:
    from quant_os.data.prediction_markets.activity_capture import (
        build_activity_dataset_from_capture,
    )
    from quant_os.research.prediction_markets.lane_splits import (
        build_chronological_lane_splits,
    )
    from quant_os.research.prediction_markets.oos_validation import (
        evaluate_lane_oos_validation,
        write_lane_oos_validation_report,
    )

    dataset = build_activity_dataset_from_capture(PHASE26_ACTIVITY_FIXTURE)
    splits = build_chronological_lane_splits(dataset)
    validation = evaluate_lane_oos_validation(dataset)

    assert splits["split_status"] == "OOS_SPLITS_READY"
    assert splits["split_counts"] == {"train": 12, "validation": 6, "test": 6}
    train_end = max(item["prediction_timestamp"] for item in splits["splits"]["train"])
    validation_start = min(item["prediction_timestamp"] for item in splits["splits"]["validation"])
    validation_end = max(item["prediction_timestamp"] for item in splits["splits"]["validation"])
    test_start = min(item["prediction_timestamp"] for item in splits["splits"]["test"])
    assert train_end < validation_start
    assert validation_end < test_start
    assert validation["leakage_check"]["passed"] is True
    assert validation["oos_validation_status"] == "BASELINES_NOT_BEATEN"
    assert validation["resolved_observation_count"] == 24
    assert validation["oos_observation_count"] == 12
    assert validation["baseline_names"] == [
        "naive_50_50",
        "current_market_probability",
        "simple_calibrated_heuristic",
    ]
    assert validation["market_baseline_dominant"] is True
    assert validation["candidate_signal_survives_oos"] is False
    assert validation["in_sample_only_signal_count"] == 0
    for result in validation["candidate_results"].values():
        assert result["opaque_model"] is False
        assert "plain_english_explanation" in result
        assert result["oos"]["observation_count"] == 12
        assert result["survives_oos"] is False
        assert result["credible_signal_family"] is False
        assert "current_market_probability" in result["oos_baseline_comparisons"]

    report = write_lane_oos_validation_report(
        fixture_path=PHASE26_ACTIVITY_FIXTURE,
        output_root=local_project,
    )
    assert report["oos_validation_status"] == "BASELINES_NOT_BEATEN"
    assert Path(report["report_paths"]["json"]).exists()
    markdown = Path(report["report_paths"]["markdown"]).read_text("utf-8")
    assert "Research-only" in markdown
    assert "No execution authority" in markdown


def test_sequence26_robustness_and_replay_readiness_stay_conservative(
    local_project: Path,
) -> None:
    from quant_os.data.prediction_markets.activity_capture import (
        build_activity_dataset_from_capture,
    )
    from quant_os.research.prediction_markets.oos_validation import (
        evaluate_lane_oos_validation,
    )
    from quant_os.research.prediction_markets.replay_feasibility import (
        evaluate_oos_replay_readiness,
    )
    from quant_os.research.prediction_markets.replay_feasibility_report import (
        write_oos_replay_readiness_report,
    )
    from quant_os.research.prediction_markets.robustness import (
        evaluate_lane_robustness,
        write_lane_robustness_report,
    )

    dataset = build_activity_dataset_from_capture(PHASE26_ACTIVITY_FIXTURE)
    validation = evaluate_lane_oos_validation(dataset)
    robustness = evaluate_lane_robustness(oos_validation=validation)
    readiness = evaluate_oos_replay_readiness(
        lane_activity_dataset=dataset,
        oos_validation=validation,
        robustness=robustness,
    )

    assert robustness["sequence"] == "26"
    assert robustness["robustness_status"] == "OOS_SIGNAL_NOT_ROBUST"
    assert "MARKET_BASELINE_NOT_BEATEN_OOS" in robustness["warnings"]
    assert robustness["summary"]["oos_observation_count"] == 12
    assert robustness["summary"]["candidate_signal_survives_oos"] is False

    assert readiness["sequence"] == "26"
    assert readiness["replay_readiness_status"] == "LANE_IMPROVED_BUT_REPLAY_NOT_READY"
    assert readiness["ready_for_narrow_replay_design"] is False
    assert readiness["best_candidate_lane"]["lane_id"] == "short_dated_clean_binary"
    assert "BASELINES_NOT_BEATEN" in readiness["blockers"]
    assert "NO_CREDIBLE_SIGNAL_FAMILY" in readiness["blockers"]
    assert "SIGNAL_WEAK" in readiness["blockers"]
    assert "LANE_OOS_TOO_THIN" not in readiness["blockers"]
    assert "INSUFFICIENT_RESOLVED_HISTORY" not in readiness["blockers"]
    assert readiness["live_trading_enabled"] is False
    assert readiness["execution_authority"] == "NONE"

    robustness_report = write_lane_robustness_report(
        fixture_path=PHASE26_ACTIVITY_FIXTURE,
        output_root=local_project,
    )
    readiness_report = write_oos_replay_readiness_report(
        fixture_path=PHASE26_ACTIVITY_FIXTURE,
        output_root=local_project,
    )
    for payload in (robustness_report, readiness_report):
        assert Path(payload["report_paths"]["json"]).exists()
        markdown = Path(payload["report_paths"]["markdown"]).read_text("utf-8")
        assert "Research-only" in markdown
        assert "No execution authority" in markdown


def test_sequence26_ready_for_replay_requires_oos_survival_and_quality() -> None:
    from quant_os.data.prediction_markets.activity_capture import (
        build_activity_dataset_from_capture,
    )
    from quant_os.research.prediction_markets.oos_validation import (
        evaluate_lane_oos_validation,
    )
    from quant_os.research.prediction_markets.replay_feasibility import (
        REPLAY_FEASIBILITY_SAFETY,
        evaluate_oos_replay_readiness,
    )
    from quant_os.research.prediction_markets.robustness import evaluate_lane_robustness

    dataset = build_activity_dataset_from_capture(PHASE26_ACTIVITY_FIXTURE)
    validation = evaluate_lane_oos_validation(dataset)
    robustness = evaluate_lane_robustness(oos_validation=validation)
    readiness = evaluate_oos_replay_readiness(
        lane_activity_dataset=dataset,
        oos_validation=validation,
        robustness=robustness,
    )

    assert readiness["ready_for_narrow_replay_design"] is False
    assert readiness["replay_readiness_status"] != "READY_FOR_NARROW_REPLAY_DESIGN"

    optimistic_validation = {
        **validation,
        "oos_validation_status": "CANDIDATE_SIGNAL_SURVIVES_OOS",
        "candidate_signal_survives_oos": True,
    }
    optimistic_robustness = {
        **robustness,
        "robustness_status": "OOS_SIGNAL_ROBUST_ENOUGH_FOR_REPLAY_DESIGN",
        "warnings": [],
    }
    too_thin_dataset = {
        **dataset,
        "resolved_market_count": 8,
    }
    too_thin_validation = {
        **optimistic_validation,
        "resolved_observation_count": 8,
        "oos_observation_count": 4,
    }
    too_thin_gate = evaluate_oos_replay_readiness(
        lane_activity_dataset=too_thin_dataset,
        oos_validation=too_thin_validation,
        robustness=optimistic_robustness,
    )
    assert too_thin_gate["ready_for_narrow_replay_design"] is False
    assert "INSUFFICIENT_RESOLVED_HISTORY" in too_thin_gate["blockers"]
    assert "LANE_OOS_TOO_THIN" in too_thin_gate["blockers"]

    for safety in (REPLAY_FEASIBILITY_SAFETY, readiness):
        assert safety["execution_authority"] == "NONE"
        assert safety["wallet_signing_enabled"] is False
        assert safety["live_trading_enabled"] is False
        assert safety["copy_trading_enabled"] is False
        assert safety["real_orders_enabled"] is False
