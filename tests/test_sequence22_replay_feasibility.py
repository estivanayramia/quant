from __future__ import annotations

from pathlib import Path

PHASE21_HISTORY_FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "prediction_markets"
    / "history"
    / "polymarket_resolution_history_sample.json"
)
EXPANDED_HISTORY_FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "prediction_markets"
    / "history"
    / "polymarket_resolution_history_expanded_sample.json"
)


def test_expanded_history_dataset_preserves_statuses_hashes_and_exclusions() -> None:
    from quant_os.data.prediction_markets.resolution_dataset import (
        build_resolution_aware_dataset,
    )

    first = build_resolution_aware_dataset(EXPANDED_HISTORY_FIXTURE)
    second = build_resolution_aware_dataset(EXPANDED_HISTORY_FIXTURE)

    assert first["dataset_id"] == second["dataset_id"]
    assert first["dataset_hash"] == second["dataset_hash"]
    assert first["source_sha256"] == second["source_sha256"]
    assert first["sequence"] == "22"
    assert first["market_count"] == 11
    assert first["included_market_count"] == 9
    assert first["snapshot_count"] == 29
    assert first["resolution_summary"]["resolved_count"] == 9
    assert first["resolution_summary"]["unresolved_count"] == 1
    assert first["resolution_summary"]["ambiguous_count"] == 1
    assert first["resolution_summary"]["excluded_count"] == 2
    assert first["live_trading_enabled"] is False
    assert first["execution_authority"] == "NONE"

    by_market = {market["market_id"]: market for market in first["markets"]}
    unresolved = by_market["pm-expanded-unresolved-1"]
    assert unresolved["resolution"]["status"] == "UNRESOLVED"
    assert unresolved["included_in_candidate_research"] is True
    assert unresolved["candidate_research_status"] == "INCLUDED_UNSCORED"

    ambiguous = by_market["pm-expanded-ambiguous-excluded-1"]
    assert ambiguous["candidate_research_status"] == "EXCLUDED"
    assert ambiguous["exclusion_reason"] == "AMBIGUOUS_MARKET_STRUCTURE"

    thin = by_market["pm-expanded-thin-excluded-1"]
    assert thin["candidate_research_status"] == "EXCLUDED"
    assert thin["exclusion_reason"] == "LOW_PRIORITY"


def test_dataset_growth_report_compares_phase21_and_expanded_fixtures(
    local_project: Path,
) -> None:
    from quant_os.research.prediction_markets.dataset_growth import (
        write_dataset_growth_report,
    )
    from quant_os.research.prediction_markets.historical_dataset import (
        write_expanded_historical_dataset_report,
    )

    dataset_report = write_expanded_historical_dataset_report(
        fixture_path=EXPANDED_HISTORY_FIXTURE,
        output_root=local_project,
    )
    growth_report = write_dataset_growth_report(
        previous_fixture_path=PHASE21_HISTORY_FIXTURE,
        expanded_fixture_path=EXPANDED_HISTORY_FIXTURE,
        output_root=local_project,
    )

    assert dataset_report["sequence"] == "22"
    assert dataset_report["market_count"] == 11
    assert dataset_report["research_dataset_status"] == "EXPANDED_HISTORY_RESEARCH_ONLY"
    assert growth_report["market_delta"] == 7
    assert growth_report["resolved_delta"] == 7
    assert growth_report["included_market_delta"] == 6
    assert growth_report["expanded_dataset"]["dataset_hash"] == dataset_report["dataset_hash"]
    assert growth_report["live_trading_enabled"] is False

    for payload in (dataset_report, growth_report):
        assert Path(payload["report_paths"]["json"]).exists()
        markdown = Path(payload["report_paths"]["markdown"]).read_text("utf-8")
        assert "Research-only" in markdown
        assert "No execution authority" in markdown


def test_candidate_evaluation_metrics_reject_weak_candidates_honestly(
    local_project: Path,
) -> None:
    from quant_os.data.prediction_markets.resolution_dataset import (
        build_resolution_aware_dataset,
    )
    from quant_os.research.prediction_markets.candidate_predictions import (
        write_prediction_candidate_evaluation_report,
    )
    from quant_os.research.prediction_markets.features import build_prediction_features
    from quant_os.research.prediction_markets.metrics import evaluate_candidate_forecasts

    dataset = build_resolution_aware_dataset(EXPANDED_HISTORY_FIXTURE)
    features = build_prediction_features(dataset)
    metrics = evaluate_candidate_forecasts(features)
    report = write_prediction_candidate_evaluation_report(
        fixture_path=EXPANDED_HISTORY_FIXTURE,
        output_root=local_project,
    )

    assert len(features) == 9
    assert metrics["resolved_observation_count"] == 8
    assert metrics["baselines"]["naive_50_50"]["brier_score"] == 0.25
    assert metrics["baselines"]["current_market_probability"]["log_loss"] is not None
    assert (
        metrics["candidates"]["quality_adjusted_candidate"]["brier_score"]
        > metrics["baselines"]["current_market_probability"]["brier_score"]
    )
    assert report["candidate_results"]["quality_adjusted_candidate"][
        "beats_current_market_probability"
    ] is False
    assert report["candidate_evaluation_status"] == "BASELINES_NOT_BEATEN"
    assert "market baseline is not beaten" in " ".join(report["unknowns"])
    assert report["execution_authority"] == "NONE"
    assert Path(report["report_paths"]["json"]).exists()


def test_replay_feasibility_blocks_replay_without_history_and_baseline_evidence(
    local_project: Path,
) -> None:
    from quant_os.data.prediction_markets.resolution_dataset import (
        build_resolution_aware_dataset,
    )
    from quant_os.research.prediction_markets.candidate_predictions import (
        evaluate_prediction_candidate_signals,
    )
    from quant_os.research.prediction_markets.replay_feasibility import (
        evaluate_replay_feasibility,
    )
    from quant_os.research.prediction_markets.replay_feasibility_report import (
        write_replay_feasibility_report,
    )

    expanded = build_resolution_aware_dataset(EXPANDED_HISTORY_FIXTURE)
    expanded_eval = evaluate_prediction_candidate_signals(expanded)
    expanded_gate = evaluate_replay_feasibility(dataset=expanded, candidate_evaluation=expanded_eval)

    assert expanded_gate["replay_feasibility_status"] == "REPLAY_NOT_JUSTIFIED"
    assert "BASELINES_NOT_BEATEN" in expanded_gate["blockers"]
    assert "SIGNAL_WEAK" in expanded_gate["blockers"]
    assert expanded_gate["ready_for_narrow_replay_design"] is False

    thin = build_resolution_aware_dataset(PHASE21_HISTORY_FIXTURE)
    thin_eval = evaluate_prediction_candidate_signals(thin)
    thin_gate = evaluate_replay_feasibility(dataset=thin, candidate_evaluation=thin_eval)

    assert thin_gate["replay_feasibility_status"] == "DATASET_TOO_THIN"
    assert "INSUFFICIENT_RESOLVED_HISTORY" in thin_gate["blockers"]
    assert thin_gate["ready_for_narrow_replay_design"] is False

    report = write_replay_feasibility_report(
        fixture_path=EXPANDED_HISTORY_FIXTURE,
        output_root=local_project,
    )
    assert report["replay_feasibility_status"] == "REPLAY_NOT_JUSTIFIED"
    assert report["ready_for_narrow_replay_design"] is False
    assert report["live_trading_enabled"] is False
    assert Path(report["report_paths"]["json"]).exists()
    markdown = Path(report["report_paths"]["markdown"]).read_text("utf-8")
    assert "Research-only" in markdown
    assert "No execution authority" in markdown


def test_sequence22_prediction_research_adds_no_execution_or_signing_authority() -> None:
    from quant_os.research.prediction_markets.candidate_predictions import (
        PREDICTION_CANDIDATE_SAFETY,
    )
    from quant_os.research.prediction_markets.replay_feasibility import (
        REPLAY_FEASIBILITY_SAFETY,
    )

    for safety in (PREDICTION_CANDIDATE_SAFETY, REPLAY_FEASIBILITY_SAFETY):
        assert safety["execution_authority"] == "NONE"
        assert safety["wallet_signing_enabled"] is False
        assert safety["live_trading_enabled"] is False
        assert safety["copy_trading_enabled"] is False
        assert safety["real_orders_enabled"] is False
