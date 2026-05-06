from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.data.prediction_markets.activity_capture import build_activity_dataset_from_capture
from quant_os.research.prediction_markets.ablation import evaluate_venue_signal_ablation
from quant_os.research.prediction_markets.venue_signals import evaluate_venue_signal_oos

REPORT_ROOT = Path("reports/sequence27/lane_decision")
LANE_DECISION_SAFETY = {
    "execution_authority": "NONE",
    "wallet_signing_enabled": False,
    "live_trading_enabled": False,
    "copy_trading_enabled": False,
    "real_orders_enabled": False,
}


def evaluate_lane_decision(
    *,
    dataset: dict[str, Any],
    venue_evaluation: dict[str, Any],
    ablation: dict[str, Any],
) -> dict[str, Any]:
    blockers = _blockers(venue_evaluation=venue_evaluation, ablation=ablation)
    ready = not blockers
    if ready:
        status = "READY_FOR_MINIMAL_REPLAY_SPEC"
        action = "WRITE_MINIMAL_REPLAY_SPEC"
    elif "REFERENCE_CONTEXT_INSUFFICIENT" in blockers:
        status = "REFERENCE_CONTEXT_INSUFFICIENT"
        action = "COLLECT_REFERENCE_CONTEXT"
    elif "MARKET_QUALITY_DISQUALIFIED" in blockers:
        status = "MARKET_QUALITY_DISQUALIFIED"
        action = "IMPROVE_MARKET_QUALITY_FILTERS"
    elif "NO_CREDIBLE_SIGNAL_FAMILY" in blockers and "BASELINES_NOT_BEATEN" in blockers:
        status = "LANE_RETIRE_CANDIDATE"
        action = "DEPRIORITIZE_SHORT_DATED_CLEAN_BINARY"
    else:
        status = "LANE_IMPROVED_BUT_REPLAY_NOT_READY"
        action = "CONTINUE_RESEARCH_ONLY"
    return {
        "sequence": "27",
        "source": dataset["source"],
        "source_mode": dataset["source_mode"],
        "lane_id": dataset["lane_id"],
        "dataset_id": dataset["dataset_id"],
        "dataset_hash": dataset["dataset_hash"],
        "lane_decision_status": status,
        "recommended_action": action,
        "ready_for_minimal_replay_spec": ready,
        "blockers": blockers,
        "best_candidate_lane": {
            "lane_id": dataset["lane_id"],
            "lane_name": "Short-Dated Clean Binary",
            "venue_signal_status": venue_evaluation["venue_signal_status"],
            "ablation_status": ablation["ablation_status"],
            "resolved_observation_count": venue_evaluation["resolved_observation_count"],
            "oos_observation_count": venue_evaluation["oos_observation_count"],
        },
        "observed_facts": [
            "Lane decision uses venue-signal OOS evidence and ablation diagnostics only.",
        ],
        "inferred_patterns": [
            "The lane can be deprioritized when venue-specific signals still fail strong baselines.",
        ],
        "unknowns": [
            "Lane retirement is a research prioritization outcome, not a live trading decision.",
        ],
        **LANE_DECISION_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_lane_decision_report(
    *,
    fixture_path: str | Path,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    dataset = build_activity_dataset_from_capture(fixture_path)
    venue = evaluate_venue_signal_oos(dataset)
    ablation = evaluate_venue_signal_ablation(dataset=dataset, venue_evaluation=venue)
    payload = evaluate_lane_decision(dataset=dataset, venue_evaluation=venue, ablation=ablation)
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _blockers(*, venue_evaluation: dict[str, Any], ablation: dict[str, Any]) -> list[str]:
    blockers = []
    if venue_evaluation.get("reference_quality_status") == "REFERENCE_CONTEXT_INSUFFICIENT":
        blockers.append("REFERENCE_CONTEXT_INSUFFICIENT")
    if venue_evaluation.get("quality_filtered_observation_count", 0) < 10:
        blockers.append("MARKET_QUALITY_DISQUALIFIED")
    if not venue_evaluation["candidate_signal_survives_oos"]:
        blockers.append("NO_CREDIBLE_SIGNAL_FAMILY")
    if venue_evaluation["venue_signal_status"] == "BASELINES_NOT_BEATEN":
        blockers.append("BASELINES_NOT_BEATEN")
        blockers.append("SIGNAL_WEAK")
    if ablation["ablation_status"] != "NO_ABLATION_BEATS_MARKET_BASELINE_OOS":
        blockers.append("DIRECTIONAL_IMPROVEMENT_ONLY")
    return _dedupe(blockers)


def _dedupe(items: list[str]) -> list[str]:
    seen = set()
    deduped = []
    for item in items:
        if item not in seen:
            deduped.append(item)
            seen.add(item)
    return deduped


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_lane_decision.json"
    md_path = root / "latest_lane_decision.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 27 Lane Decision",
        "",
        "Research-only lane decision report. No execution authority.",
        "",
        f"Lane: {payload['lane_id']}",
        f"Decision: {payload['lane_decision_status']}",
        f"Recommended action: {payload['recommended_action']}",
        f"Ready for minimal replay spec: {payload['ready_for_minimal_replay_spec']}",
        f"Live promotion: {payload['live_promotion_status']}",
        "",
        "## Observed facts",
    ]
    lines.extend(f"- {item}" for item in payload["observed_facts"])
    lines.extend(["", "## Inferred patterns"])
    lines.extend(f"- {item}" for item in payload["inferred_patterns"])
    lines.extend(["", "## Unknowns"])
    lines.extend(f"- {item}" for item in payload["unknowns"])
    lines.extend(["", "## Blockers"])
    lines.extend(f"- {item}" for item in (payload["blockers"] or ["None"]))
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
