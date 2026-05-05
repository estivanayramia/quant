from __future__ import annotations

from pathlib import Path

LANE_ACTIVITY_FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "prediction_markets"
    / "activity"
    / "polymarket_short_dated_lane_activity_sample.json"
)


def test_lane_activity_dataset_and_timeline_are_deterministic(local_project: Path) -> None:
    from quant_os.data.prediction_markets.activity_history import build_lane_activity_history
    from quant_os.research.prediction_markets.lane_activity_dataset import (
        write_lane_activity_dataset_report,
    )
    from quant_os.research.prediction_markets.lane_timeline import (
        summarize_lane_timelines,
        write_lane_timeline_summary_report,
    )

    first = build_lane_activity_history(LANE_ACTIVITY_FIXTURE)
    second = build_lane_activity_history(LANE_ACTIVITY_FIXTURE)
    timeline = summarize_lane_timelines(first)

    assert first["dataset_id"] == second["dataset_id"]
    assert first["dataset_hash"] == second["dataset_hash"]
    assert first["sequence"] == "24"
    assert first["lane_id"] == "short_dated_clean_binary"
    assert first["market_count"] == 10
    assert first["included_market_count"] == 9
    assert first["resolved_market_count"] == 8
    assert first["unresolved_market_count"] == 1
    assert first["ambiguous_market_count"] == 1
    assert first["excluded_market_count"] == 1
    assert first["activity_observation_count"] == 50
    assert first["activity_depth_status"] == "LANE_ACTIVITY_ENRICHED"

    by_market = {market["market_id"]: market for market in first["markets"]}
    assert by_market["pm-activity-weather-yes-1"]["lane_activity_status"] == "INCLUDED_RESOLVED"
    assert by_market["pm-activity-weather-unresolved-1"]["lane_activity_status"] == "INCLUDED_UNSCORED"
    assert by_market["pm-activity-ambiguous-excluded-1"]["lane_activity_status"] == "EXCLUDED"
    assert by_market["pm-activity-ambiguous-excluded-1"]["exclusion_reason"] == "AMBIGUOUS"
    assert by_market["pm-activity-weather-yes-1"]["provenance"]["source_sha256"] == first["dataset_hash"]

    assert timeline["summary"]["market_count"] == 10
    assert timeline["summary"]["included_market_count"] == 9
    assert timeline["summary"]["activity_observation_count"] == 50
    assert timeline["summary"]["min_observations_per_market"] == 5
    assert timeline["summary"]["lifecycle_status_counts"]["NEARING_CLOSE"] == 20
    assert timeline["markets"][0]["activity_points"] == 5

    dataset_report = write_lane_activity_dataset_report(
        fixture_path=LANE_ACTIVITY_FIXTURE,
        output_root=local_project,
    )
    timeline_report = write_lane_timeline_summary_report(
        fixture_path=LANE_ACTIVITY_FIXTURE,
        output_root=local_project,
    )
    for payload in (dataset_report, timeline_report):
        assert Path(payload["report_paths"]["json"]).exists()
        markdown = Path(payload["report_paths"]["markdown"]).read_text("utf-8")
        assert "Research-only" in markdown
        assert "No execution authority" in markdown


def test_dynamic_features_and_signal_families_are_interpretable_and_deterministic(
    local_project: Path,
) -> None:
    from quant_os.data.prediction_markets.activity_history import build_lane_activity_history
    from quant_os.research.prediction_markets.lane_dynamics import (
        DYNAMIC_SIGNAL_FAMILIES,
        apply_dynamic_signal_families,
        write_dynamic_signal_report,
    )
    from quant_os.research.prediction_markets.time_series_features import (
        build_time_series_features,
    )

    dataset = build_lane_activity_history(LANE_ACTIVITY_FIXTURE)
    first = apply_dynamic_signal_families(build_time_series_features(dataset))
    second = apply_dynamic_signal_families(build_time_series_features(dataset))

    assert first == second
    assert len(first) == 9
    assert len(DYNAMIC_SIGNAL_FAMILIES) == 4
    feature = next(item for item in first if item["market_id"] == "pm-activity-tech-no-1")
    assert feature["activity_observation_count"] == 5
    assert feature["late_price_slope"] == -0.04
    assert feature["liquidity_change"] == -2200.0
    assert feature["wallet_concentration_change"] == 0.29
    assert feature["max_unsupported_price_jump"] == 0.09
    assert feature["latest_time_to_resolution_bucket"] == "FINAL_HOURS"

    for family in DYNAMIC_SIGNAL_FAMILIES:
        assert family["signal_family_id"]
        assert family["plain_english_explanation"]
        assert family["what_it_measures"]
        assert family["why_it_might_work"]
        assert family["why_it_might_fail"]
        assert family["market_pathology_sensitivity"]
        assert family["failure_mode_notes"]
        assert family["opaque_model"] is False
        assert family["probability_key"] in feature

    report = write_dynamic_signal_report(
        fixture_path=LANE_ACTIVITY_FIXTURE,
        output_root=local_project,
    )
    assert report["signal_family_count"] == 4
    assert report["feature_count"] == 9
    assert Path(report["report_paths"]["json"]).exists()
    markdown = Path(report["report_paths"]["markdown"]).read_text("utf-8")
    assert "Research-only" in markdown
    assert "No execution authority" in markdown


def test_wallet_flow_features_are_read_only_and_separate_heuristics(
    local_project: Path,
) -> None:
    from quant_os.data.prediction_markets.activity_history import build_lane_activity_history
    from quant_os.research.prediction_markets.wallet_flow_features import (
        WALLET_FLOW_SAFETY,
        build_wallet_flow_features,
        write_wallet_flow_report,
    )

    dataset = build_lane_activity_history(LANE_ACTIVITY_FIXTURE)
    payload = build_wallet_flow_features(dataset)

    assert payload["lane_id"] == "short_dated_clean_binary"
    assert payload["market_count"] == 9
    by_market = {item["market_id"]: item for item in payload["markets"]}
    tech = by_market["pm-activity-tech-no-1"]
    assert tech["observed_facts"]["wallet_concentration_change"] == 0.29
    assert tech["observed_facts"]["dominant_wallet_persistence"] == 0.4
    assert "CONCENTRATION_RISING" in {
        item["label"] for item in tech["heuristic_interpretations"]
    }
    assert "ONE_SIDED_PARTICIPATION_SPIKE" not in {
        item["label"] for item in tech["heuristic_interpretations"]
    }

    culture = by_market["pm-activity-culture-yes-1"]
    assert "ONE_SIDED_PARTICIPATION_SPIKE" in {
        item["label"] for item in culture["heuristic_interpretations"]
    }
    assert culture["unknowns"]

    assert WALLET_FLOW_SAFETY["execution_authority"] == "NONE"
    assert WALLET_FLOW_SAFETY["copy_trading_enabled"] is False
    assert WALLET_FLOW_SAFETY["wallet_signing_enabled"] is False

    report = write_wallet_flow_report(
        fixture_path=LANE_ACTIVITY_FIXTURE,
        output_root=local_project,
    )
    assert Path(report["report_paths"]["json"]).exists()
    markdown = Path(report["report_paths"]["markdown"]).read_text("utf-8")
    assert "Observed facts" in markdown
    assert "Heuristic interpretations" in markdown
    assert "Unknowns" in markdown


def test_lane_activity_evaluation_and_replay_readiness_stay_conservative(
    local_project: Path,
) -> None:
    from quant_os.data.prediction_markets.activity_history import build_lane_activity_history
    from quant_os.research.prediction_markets.evaluation import (
        LANE_ACTIVITY_EVALUATION_SAFETY,
        evaluate_lane_activity_signals,
        write_lane_activity_evaluation_report,
    )
    from quant_os.research.prediction_markets.replay_feasibility import (
        evaluate_lane_replay_readiness,
    )
    from quant_os.research.prediction_markets.replay_feasibility_report import (
        write_lane_replay_readiness_report,
    )

    dataset = build_lane_activity_history(LANE_ACTIVITY_FIXTURE)
    evaluation = evaluate_lane_activity_signals(dataset)
    readiness = evaluate_lane_replay_readiness(
        lane_activity_dataset=dataset,
        lane_evaluation=evaluation,
    )

    assert evaluation["sequence"] == "24"
    assert evaluation["lane_id"] == "short_dated_clean_binary"
    assert evaluation["lane_evaluation_status"] == "BASELINES_NOT_BEATEN"
    assert evaluation["resolved_observation_count"] == 8
    assert evaluation["baselines"]["current_market_probability"]["observation_count"] == 8
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

    assert readiness["replay_readiness_status"] == "LANE_IMPROVED_BUT_REPLAY_NOT_READY"
    assert readiness["ready_for_narrow_replay_design"] is False
    assert "LANE_TOO_THIN" in readiness["blockers"]
    assert "NO_CREDIBLE_SIGNAL_FAMILY" in readiness["blockers"]
    assert "BASELINES_NOT_BEATEN" in readiness["blockers"]
    assert "SIGNAL_WEAK" in readiness["blockers"]
    assert readiness["best_candidate_lane"]["lane_id"] == "short_dated_clean_binary"
    assert readiness["live_trading_enabled"] is False
    assert readiness["execution_authority"] == "NONE"

    for safety in (LANE_ACTIVITY_EVALUATION_SAFETY,):
        assert safety["execution_authority"] == "NONE"
        assert safety["wallet_signing_enabled"] is False
        assert safety["live_trading_enabled"] is False
        assert safety["copy_trading_enabled"] is False
        assert safety["real_orders_enabled"] is False

    lane_report = write_lane_activity_evaluation_report(
        fixture_path=LANE_ACTIVITY_FIXTURE,
        output_root=local_project,
    )
    readiness_report = write_lane_replay_readiness_report(
        fixture_path=LANE_ACTIVITY_FIXTURE,
        output_root=local_project,
    )
    for payload in (lane_report, readiness_report):
        assert Path(payload["report_paths"]["json"]).exists()
        markdown = Path(payload["report_paths"]["markdown"]).read_text("utf-8")
        assert "Research-only" in markdown
        assert "No execution authority" in markdown
        assert "Observed facts" in markdown
        assert "Inferred patterns" in markdown
        assert "Unknowns" in markdown


def test_sequence24_adds_no_prediction_market_execution_or_signing_authority() -> None:
    from quant_os.data.prediction_markets.activity_history import LANE_ACTIVITY_SAFETY
    from quant_os.research.prediction_markets.evaluation import LANE_ACTIVITY_EVALUATION_SAFETY
    from quant_os.research.prediction_markets.lane_dynamics import DYNAMIC_SIGNAL_SAFETY
    from quant_os.research.prediction_markets.replay_feasibility import (
        REPLAY_FEASIBILITY_SAFETY,
    )
    from quant_os.research.prediction_markets.wallet_flow_features import WALLET_FLOW_SAFETY

    for safety in (
        LANE_ACTIVITY_SAFETY,
        DYNAMIC_SIGNAL_SAFETY,
        LANE_ACTIVITY_EVALUATION_SAFETY,
        REPLAY_FEASIBILITY_SAFETY,
        WALLET_FLOW_SAFETY,
    ):
        assert safety["execution_authority"] == "NONE"
        assert safety["wallet_signing_enabled"] is False
        assert safety["live_trading_enabled"] is False
        assert safety["copy_trading_enabled"] is False
        assert safety["real_orders_enabled"] is False
