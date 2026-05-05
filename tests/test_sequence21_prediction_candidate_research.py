from __future__ import annotations

from pathlib import Path

HISTORY_FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "prediction_markets"
    / "history"
    / "polymarket_resolution_history_sample.json"
)


def test_resolution_aware_history_dataset_builds_deterministically_and_preserves_provenance() -> None:
    from quant_os.data.prediction_markets.resolution_dataset import (
        build_resolution_aware_dataset,
    )

    first = build_resolution_aware_dataset(HISTORY_FIXTURE)
    second = build_resolution_aware_dataset(HISTORY_FIXTURE)

    assert first["dataset_id"] == second["dataset_id"]
    assert first["source_mode"] == "fixture"
    assert first["sequence"] == "21"
    assert first["market_count"] == 4
    assert first["snapshot_count"] == 9
    assert first["resolution_summary"]["resolved_count"] == 2
    assert first["resolution_summary"]["unresolved_count"] == 1
    assert first["resolution_summary"]["ambiguous_count"] == 1
    assert first["source_sha256"] == second["source_sha256"]
    assert first["live_trading_enabled"] is False

    by_market = {market["market_id"]: market for market in first["markets"]}
    assert by_market["pm-history-yes-1"]["resolution"]["winning_outcome"] == "YES"
    assert by_market["pm-history-no-1"]["resolution"]["winning_outcome"] == "NO"
    assert by_market["pm-history-unresolved-1"]["resolution"]["status"] == "UNRESOLVED"
    assert by_market["pm-history-ambiguous-1"]["exclusion_reason"] == "AMBIGUOUS_MARKET_STRUCTURE"
    assert by_market["pm-history-yes-1"]["provenance"]["source_path"].endswith(
        "polymarket_resolution_history_sample.json"
    )


def test_reference_context_and_resolution_labels_attach_truth_without_network() -> None:
    from quant_os.data.prediction_markets.resolution_dataset import (
        build_resolution_aware_dataset,
    )
    from quant_os.research.prediction_markets.reference_context import (
        attach_offline_reference_context,
    )
    from quant_os.research.prediction_markets.resolution_labels import (
        build_resolution_truth_labels,
    )

    dataset = build_resolution_aware_dataset(HISTORY_FIXTURE)
    references = attach_offline_reference_context(dataset)
    labels = build_resolution_truth_labels(dataset)

    yes_reference = next(item for item in references if item["market_id"] == "pm-history-yes-1")
    assert yes_reference["internet_required"] is False
    assert yes_reference["reference_status"] == "ATTACHED_OFFLINE"
    assert yes_reference["observed_market_data"] is True
    assert yes_reference["attached_resolution_truth"] is True

    unresolved = next(item for item in labels if item["market_id"] == "pm-history-unresolved-1")
    assert unresolved["label_ready"] is False
    assert unresolved["resolution_status"] == "UNRESOLVED"
    assert unresolved["uncertainty"] == "UNKNOWN"

    ambiguous = next(item for item in labels if item["market_id"] == "pm-history-ambiguous-1")
    assert ambiguous["label_ready"] is False
    assert ambiguous["uncertainty"] == "AMBIGUOUS"


def test_prediction_features_and_baselines_are_deterministic_and_interpretable() -> None:
    from quant_os.data.prediction_markets.resolution_dataset import (
        build_resolution_aware_dataset,
    )
    from quant_os.research.prediction_markets.baselines import evaluate_prediction_baselines
    from quant_os.research.prediction_markets.features import build_prediction_features

    dataset = build_resolution_aware_dataset(HISTORY_FIXTURE)
    first = build_prediction_features(dataset)
    second = build_prediction_features(dataset)

    assert first == second
    assert len(first) == 3
    yes_feature = next(item for item in first if item["market_id"] == "pm-history-yes-1")
    assert yes_feature["prediction_label"] == 1
    assert yes_feature["current_market_probability"] == 0.64
    assert yes_feature["price_drift_from_open"] == 0.26
    assert yes_feature["feature_family"] == "interpretable_market_state_v1"

    metrics = evaluate_prediction_baselines(first)
    assert metrics["resolved_observation_count"] == 2
    assert metrics["baselines"]["current_market_probability"]["brier_score"] < metrics["baselines"][
        "naive_50_50"
    ]["brier_score"]
    assert metrics["baselines"]["simple_calibrated_heuristic"]["opaque_model"] is False


def test_prediction_candidate_report_rejects_replay_design_when_history_is_too_thin(
    local_project: Path,
) -> None:
    from quant_os.research.prediction_markets.candidate_predictions import (
        write_prediction_candidate_report,
    )
    from quant_os.research.prediction_markets.historical_dataset import (
        write_historical_dataset_report,
    )

    dataset_report = write_historical_dataset_report(
        fixture_path=HISTORY_FIXTURE,
        output_root=local_project,
    )
    candidate_report = write_prediction_candidate_report(
        fixture_path=HISTORY_FIXTURE,
        output_root=local_project,
    )

    assert dataset_report["research_readiness_status"] == "DATASET_TOO_THIN"
    assert candidate_report["research_readiness_status"] == "DATASET_TOO_THIN"
    assert "INSUFFICIENT_RESOLVED_HISTORY" in candidate_report["blockers"]
    assert "BASELINES_NOT_BEATEN" in candidate_report["blockers"]
    assert candidate_report["candidate_results"]["simple_calibrated_heuristic"][
        "beats_current_market_probability"
    ] is False
    assert candidate_report["ready_for_replay_design"] is False
    assert candidate_report["live_trading_enabled"] is False

    for payload in (dataset_report, candidate_report):
        assert Path(payload["report_paths"]["json"]).exists()
        markdown = Path(payload["report_paths"]["markdown"]).read_text("utf-8")
        assert "Research-only" in markdown
        assert "Observed facts" in markdown
        assert "Inferred patterns" in markdown
        assert "Unknowns" in markdown
        assert "No execution authority" in markdown


def test_prediction_candidate_spine_exposes_no_execution_or_signing_paths() -> None:
    from quant_os.research.prediction_markets.candidate_predictions import (
        PREDICTION_CANDIDATE_SAFETY,
    )

    assert PREDICTION_CANDIDATE_SAFETY["execution_authority"] == "NONE"
    assert PREDICTION_CANDIDATE_SAFETY["wallet_signing_enabled"] is False
    assert PREDICTION_CANDIDATE_SAFETY["live_trading_enabled"] is False
    assert PREDICTION_CANDIDATE_SAFETY["copy_trading_enabled"] is False
