from __future__ import annotations

from pathlib import Path

PHASE21_HISTORY_FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "prediction_markets"
    / "history"
    / "polymarket_resolution_history_sample.json"
)
SIGNAL_DISCOVERY_FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "prediction_markets"
    / "history"
    / "polymarket_signal_discovery_sample.json"
)


def test_signal_discovery_dataset_and_market_strata_are_deterministic(
    local_project: Path,
) -> None:
    from quant_os.data.prediction_markets.resolution_dataset import (
        build_resolution_aware_dataset,
    )
    from quant_os.research.prediction_markets.historical_dataset import (
        write_signal_discovery_dataset_report,
    )
    from quant_os.research.prediction_markets.market_strata import (
        build_market_strata,
        write_market_strata_report,
    )

    first = build_resolution_aware_dataset(SIGNAL_DISCOVERY_FIXTURE)
    second = build_resolution_aware_dataset(SIGNAL_DISCOVERY_FIXTURE)
    strata = build_market_strata(first)
    repeated_strata = build_market_strata(second)

    assert first["dataset_id"] == second["dataset_id"]
    assert first["dataset_hash"] == second["dataset_hash"]
    assert first["sequence"] == "23"
    assert first["market_count"] == 16
    assert first["included_market_count"] == 14
    assert first["snapshot_count"] == 44
    assert first["resolution_summary"]["resolved_count"] == 14
    assert first["resolution_summary"]["unresolved_count"] == 1
    assert first["resolution_summary"]["ambiguous_count"] == 1
    assert first["resolution_summary"]["excluded_count"] == 2
    assert strata == repeated_strata
    assert strata["summary"]["market_count"] == 16
    assert strata["summary"]["cleanliness_bucket_counts"]["LOW_QUALITY"] >= 1

    by_market = {item["market_id"]: item for item in strata["markets"]}
    weather = by_market["pm-signal-weather-no-1"]
    assert weather["time_to_resolution_bucket"] == "SHORT"
    assert weather["liquidity_bucket"] == "DEEP"
    assert weather["concentration_bucket"] == "LOW"
    assert weather["cleanliness_bucket"] == "CLEAN"
    assert weather["usable_for_lane_research"] is True

    thin = by_market["pm-signal-thin-excluded-1"]
    assert thin["usable_for_lane_research"] is False
    assert thin["cleanliness_bucket"] == "LOW_QUALITY"
    assert thin["exclusion_reason"] == "LOW_PRIORITY"

    dataset_report = write_signal_discovery_dataset_report(
        fixture_path=SIGNAL_DISCOVERY_FIXTURE,
        output_root=local_project,
    )
    strata_report = write_market_strata_report(
        fixture_path=SIGNAL_DISCOVERY_FIXTURE,
        output_root=local_project,
    )
    for payload in (dataset_report, strata_report):
        assert Path(payload["report_paths"]["json"]).exists()
        markdown = Path(payload["report_paths"]["markdown"]).read_text("utf-8")
        assert "Research-only" in markdown
        assert "No execution authority" in markdown


def test_lane_selection_is_narrow_deterministic_and_rejects_broad_lanes(
    local_project: Path,
) -> None:
    from quant_os.data.prediction_markets.resolution_dataset import (
        build_resolution_aware_dataset,
    )
    from quant_os.research.prediction_markets.lane_selection import (
        select_prediction_lanes,
        write_lane_selection_report,
    )
    from quant_os.research.prediction_markets.market_strata import build_market_strata

    dataset = build_resolution_aware_dataset(SIGNAL_DISCOVERY_FIXTURE)
    strata = build_market_strata(dataset)
    first = select_prediction_lanes(dataset=dataset, strata=strata)
    second = select_prediction_lanes(dataset=dataset, strata=strata)

    assert first == second
    lane_ids = [lane["lane_id"] for lane in first["lanes"]]
    assert lane_ids[0] == "short_dated_clean_binary"
    assert "weather_science_resolution_clear" in lane_ids
    assert lane_ids[-1] == "all_researchable_markets"
    assert first["best_lane"]["lane_id"] == "short_dated_clean_binary"

    short_lane = first["best_lane"]
    assert short_lane["sample_size"] >= 8
    assert short_lane["resolved_label_count"] >= 8
    assert short_lane["research_status"] == "RESEARCH_WORTHY"
    assert short_lane["inclusion_rules"]
    assert short_lane["excluded_market_types"]
    assert short_lane["key_risks"]

    broad_lane = next(item for item in first["lanes"] if item["lane_id"] == "all_researchable_markets")
    assert broad_lane["research_status"] == "REJECTED_BROAD_LANE"
    assert broad_lane["research_worthiness_score"] < short_lane["research_worthiness_score"]

    report = write_lane_selection_report(
        fixture_path=SIGNAL_DISCOVERY_FIXTURE,
        output_root=local_project,
    )
    assert report["best_lane"]["lane_id"] == "short_dated_clean_binary"
    assert Path(report["report_paths"]["json"]).exists()
    markdown = Path(report["report_paths"]["markdown"]).read_text("utf-8")
    assert "Research-only" in markdown
    assert "No execution authority" in markdown


def test_signal_families_are_interpretable_and_evaluated_against_required_baselines(
    local_project: Path,
) -> None:
    from quant_os.data.prediction_markets.resolution_dataset import (
        build_resolution_aware_dataset,
    )
    from quant_os.research.prediction_markets.evaluation import (
        evaluate_lanes,
        write_lane_evaluation_report,
    )
    from quant_os.research.prediction_markets.features import build_prediction_features
    from quant_os.research.prediction_markets.signal_families import (
        SIGNAL_FAMILIES,
        apply_signal_families,
        write_signal_family_report,
    )

    dataset = build_resolution_aware_dataset(SIGNAL_DISCOVERY_FIXTURE)
    features = apply_signal_families(build_prediction_features(dataset))

    assert len(SIGNAL_FAMILIES) == 4
    for family in SIGNAL_FAMILIES:
        assert family["signal_family_id"]
        assert family["plain_english_explanation"]
        assert family["feature_list"]
        assert family["failure_mode_notes"]
        assert family["why_it_might_work"]
        assert family["why_it_might_fail"]
        assert family["opaque_model"] is False
        assert family["probability_key"] in features[0]

    evaluation = evaluate_lanes(dataset)
    best_lane = evaluation["best_lane_evaluation"]
    assert evaluation["lane_evaluation_status"] == "NO_CREDIBLE_SIGNAL_FAMILY"
    assert best_lane["lane_id"] == "short_dated_clean_binary"
    assert set(best_lane["baselines"]) >= {
        "naive_50_50",
        "current_market_probability",
        "simple_calibrated_heuristic",
    }
    for result in best_lane["candidate_results"].values():
        assert "baseline_comparisons" in result
        assert "current_market_probability" in result["baseline_comparisons"]
        assert result["beats_current_market_probability"] is False
        assert result["opaque_model"] is False

    assert any(lane["lane_status"] == "LANE_TOO_THIN" for lane in evaluation["lane_evaluations"])

    signal_report = write_signal_family_report(output_root=local_project)
    lane_report = write_lane_evaluation_report(
        fixture_path=SIGNAL_DISCOVERY_FIXTURE,
        output_root=local_project,
    )
    for payload in (signal_report, lane_report):
        assert Path(payload["report_paths"]["json"]).exists()
        markdown = Path(payload["report_paths"]["markdown"]).read_text("utf-8")
        assert "Research-only" in markdown
        assert "Observed facts" in markdown
        assert "Inferred patterns" in markdown
        assert "Unknowns" in markdown


def test_phase23_replay_preconditions_remain_blocked_without_credible_signal_family(
    local_project: Path,
) -> None:
    from quant_os.data.prediction_markets.resolution_dataset import (
        build_resolution_aware_dataset,
    )
    from quant_os.research.prediction_markets.evaluation import evaluate_lanes
    from quant_os.research.prediction_markets.replay_feasibility import (
        evaluate_replay_preconditions,
    )
    from quant_os.research.prediction_markets.replay_feasibility_report import (
        write_replay_precondition_report,
    )

    dataset = build_resolution_aware_dataset(SIGNAL_DISCOVERY_FIXTURE)
    lane_evaluation = evaluate_lanes(dataset)
    gate = evaluate_replay_preconditions(dataset=dataset, lane_evaluation=lane_evaluation)

    assert gate["replay_precondition_status"] == "LANE_IDENTIFIED_BUT_REPLAY_NOT_READY"
    assert gate["ready_for_narrow_replay_design"] is False
    assert "NO_CREDIBLE_SIGNAL_FAMILY" in gate["blockers"]
    assert "BASELINES_NOT_BEATEN" in gate["blockers"]
    assert "SIGNAL_WEAK" in gate["blockers"]
    assert gate["best_candidate_lane"]["lane_id"] == "short_dated_clean_binary"

    thin_dataset = build_resolution_aware_dataset(PHASE21_HISTORY_FIXTURE)
    thin_gate = evaluate_replay_preconditions(
        dataset=thin_dataset,
        lane_evaluation=evaluate_lanes(thin_dataset),
    )
    assert thin_gate["replay_precondition_status"] == "DATASET_TOO_THIN"
    assert "INSUFFICIENT_RESOLVED_HISTORY" in thin_gate["blockers"]
    assert thin_gate["ready_for_narrow_replay_design"] is False

    report = write_replay_precondition_report(
        fixture_path=SIGNAL_DISCOVERY_FIXTURE,
        output_root=local_project,
    )
    assert report["replay_precondition_status"] == "LANE_IDENTIFIED_BUT_REPLAY_NOT_READY"
    assert report["live_trading_enabled"] is False
    assert report["execution_authority"] == "NONE"
    assert Path(report["report_paths"]["json"]).exists()
    markdown = Path(report["report_paths"]["markdown"]).read_text("utf-8")
    assert "Research-only" in markdown
    assert "No execution authority" in markdown


def test_sequence23_adds_no_prediction_market_execution_or_signing_authority() -> None:
    from quant_os.research.prediction_markets.evaluation import LANE_EVALUATION_SAFETY
    from quant_os.research.prediction_markets.replay_feasibility import (
        REPLAY_FEASIBILITY_SAFETY,
    )
    from quant_os.research.prediction_markets.signal_families import SIGNAL_FAMILY_SAFETY

    for safety in (SIGNAL_FAMILY_SAFETY, LANE_EVALUATION_SAFETY, REPLAY_FEASIBILITY_SAFETY):
        assert safety["execution_authority"] == "NONE"
        assert safety["wallet_signing_enabled"] is False
        assert safety["live_trading_enabled"] is False
        assert safety["copy_trading_enabled"] is False
        assert safety["real_orders_enabled"] is False
