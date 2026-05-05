from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.data.prediction_markets.resolution_dataset import build_resolution_aware_dataset
from quant_os.research.prediction_markets.baselines import evaluate_prediction_baselines
from quant_os.research.prediction_markets.features import build_prediction_features

REPORT_ROOT = Path("reports/sequence21/prediction_candidates")
PREDICTION_CANDIDATE_SAFETY = {
    "execution_authority": "NONE",
    "wallet_signing_enabled": False,
    "live_trading_enabled": False,
    "copy_trading_enabled": False,
    "real_orders_enabled": False,
}


def write_prediction_feature_report(
    *,
    fixture_path: str | Path,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    dataset = build_resolution_aware_dataset(fixture_path)
    features = build_prediction_features(dataset)
    payload = {
        "sequence": "21",
        "source": "polymarket",
        "source_mode": dataset["source_mode"],
        "feature_count": len(features),
        "features": features,
        "observed_facts": [
            "Features are deterministic, interpretable market-state fields from saved snapshots.",
        ],
        "inferred_patterns": [
            "Feature values are candidates for later research, not trading signals.",
        ],
        "unknowns": [
            "Feature stability and calibration value are unproven with this narrow sample.",
        ],
        **PREDICTION_CANDIDATE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }
    payload["report_paths"] = _write_feature_report(payload, output_root=output_root)
    return payload


def write_prediction_candidate_report(
    *,
    fixture_path: str | Path,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    dataset = build_resolution_aware_dataset(fixture_path)
    features = build_prediction_features(dataset)
    metrics = evaluate_prediction_baselines(features)
    status, blockers = _candidate_readiness(dataset=dataset, metrics=metrics)
    current = metrics["baselines"]["current_market_probability"]
    heuristic = metrics["baselines"]["simple_calibrated_heuristic"]
    payload = {
        "sequence": "21",
        "source": "polymarket",
        "source_mode": dataset["source_mode"],
        "research_readiness_status": status,
        "ready_for_replay_design": status == "READY_FOR_REPLAY_DESIGN",
        "dataset_summary": {
            "dataset_id": dataset["dataset_id"],
            "market_count": dataset["market_count"],
            "included_market_count": dataset["included_market_count"],
            "snapshot_count": dataset["snapshot_count"],
            "resolution_summary": dataset["resolution_summary"],
        },
        "feature_count": len(features),
        "metrics": metrics,
        "candidate_results": {
            "simple_calibrated_heuristic": {
                "brier_score": heuristic["brier_score"],
                "accuracy": heuristic["accuracy"],
                "baseline_brier_score": current["brier_score"],
                "beats_current_market_probability": _beats(heuristic, current),
                "opaque_model": False,
            }
        },
        "blockers": blockers,
        "observed_facts": [
            "Only resolved markets are scored; unresolved markets remain unscored research rows.",
            "Current-market, no-skill, and simple heuristic baselines are evaluated with Brier score.",
        ],
        "inferred_patterns": [
            "The simple heuristic does not beat the current market probability baseline.",
            "Replay design is not justified from this narrow sample.",
        ],
        "unknowns": [
            "Historical sample size, calibration stability, wallet causality, and replay realism remain unknown.",
        ],
        **PREDICTION_CANDIDATE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }
    payload["report_paths"] = _write_candidate_report(payload, output_root=output_root)
    return payload


def _candidate_readiness(
    *,
    dataset: dict[str, Any],
    metrics: dict[str, Any],
) -> tuple[str, list[str]]:
    blockers = []
    if metrics["resolved_observation_count"] < 5:
        blockers.append("INSUFFICIENT_RESOLVED_HISTORY")
    if dataset["included_market_count"] < 5:
        blockers.append("DATASET_TOO_THIN")
    current = metrics["baselines"]["current_market_probability"]
    heuristic = metrics["baselines"]["simple_calibrated_heuristic"]
    if not _beats(heuristic, current):
        blockers.append("BASELINES_NOT_BEATEN")
    if "DATASET_TOO_THIN" in blockers:
        return "DATASET_TOO_THIN", blockers
    if "INSUFFICIENT_RESOLVED_HISTORY" in blockers:
        return "INSUFFICIENT_HISTORY", blockers
    if "BASELINES_NOT_BEATEN" in blockers:
        return "BASELINES_NOT_BEATEN", blockers
    return "READY_FOR_REPLAY_DESIGN", []


def _beats(candidate: dict[str, Any], baseline: dict[str, Any]) -> bool:
    if candidate["brier_score"] is None or baseline["brier_score"] is None:
        return False
    return float(candidate["brier_score"]) < float(baseline["brier_score"])


def _write_feature_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / Path("reports/sequence21/features")
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_prediction_features.json"
    md_path = root / "latest_prediction_features.md"
    return _write_report(payload, json_path=json_path, md_path=md_path, title="Sequence 21 Features")


def _write_candidate_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_prediction_candidates.json"
    md_path = root / "latest_prediction_candidates.md"
    return _write_report(
        payload,
        json_path=json_path,
        md_path=md_path,
        title="Sequence 21 Prediction Candidates",
    )


def _write_report(
    payload: dict[str, Any],
    *,
    json_path: Path,
    md_path: Path,
    title: str,
) -> dict[str, str]:
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    lines = [
        f"# {title}",
        "",
        "Research-only prediction candidate report. No execution authority.",
        "",
        f"Readiness: {payload.get('research_readiness_status', 'RESEARCH_ONLY')}",
        f"Live promotion: {payload['live_promotion_status']}",
        "",
        "## Observed facts",
    ]
    lines.extend(f"- {item}" for item in payload["observed_facts"])
    lines.extend(["", "## Inferred patterns"])
    lines.extend(f"- {item}" for item in payload["inferred_patterns"])
    lines.extend(["", "## Unknowns"])
    lines.extend(f"- {item}" for item in payload["unknowns"])
    if "blockers" in payload:
        lines.extend(["", "## Blockers"])
        lines.extend(f"- {item}" for item in (payload["blockers"] or ["None"]))
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
