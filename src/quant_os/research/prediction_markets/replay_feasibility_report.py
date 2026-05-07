from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.data.prediction_markets.activity_capture import build_activity_dataset_from_capture
from quant_os.data.prediction_markets.activity_history import build_lane_activity_history
from quant_os.data.prediction_markets.resolution_dataset import build_resolution_aware_dataset
from quant_os.research.prediction_markets.ablation import evaluate_venue_signal_ablation
from quant_os.research.prediction_markets.candidate_predictions import (
    evaluate_prediction_candidate_signals,
)
from quant_os.research.prediction_markets.evaluation import (
    evaluate_lane_activity_signals,
    evaluate_lanes,
    evaluate_real_activity_signals,
)
from quant_os.research.prediction_markets.lane_decision import evaluate_lane_decision
from quant_os.research.prediction_markets.oos_validation import evaluate_lane_oos_validation
from quant_os.research.prediction_markets.replay_feasibility import (
    evaluate_lane_replay_readiness,
    evaluate_oos_replay_readiness,
    evaluate_real_activity_replay_readiness,
    evaluate_replay_feasibility,
    evaluate_replay_preconditions,
    evaluate_venue_replay_readiness,
)
from quant_os.research.prediction_markets.robustness import evaluate_lane_robustness
from quant_os.research.prediction_markets.venue_signals import evaluate_venue_signal_oos

REPORT_ROOT = Path("reports/sequence22/replay_feasibility")
SEQUENCE23_REPORT_ROOT = Path("reports/sequence23/replay_preconditions")
SEQUENCE24_REPORT_ROOT = Path("reports/sequence24/replay_readiness")
SEQUENCE25_REPORT_ROOT = Path("reports/sequence25/replay_readiness")
SEQUENCE26_REPORT_ROOT = Path("reports/sequence26/replay_readiness")
SEQUENCE27_REPORT_ROOT = Path("reports/sequence27/replay_readiness")


def write_replay_feasibility_report(
    *,
    fixture_path: str | Path,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    dataset = build_resolution_aware_dataset(fixture_path)
    candidate_evaluation = evaluate_prediction_candidate_signals(dataset)
    payload = evaluate_replay_feasibility(dataset=dataset, candidate_evaluation=candidate_evaluation)
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def write_replay_precondition_report(
    *,
    fixture_path: str | Path,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    dataset = build_resolution_aware_dataset(fixture_path)
    lane_evaluation = evaluate_lanes(dataset)
    payload = evaluate_replay_preconditions(dataset=dataset, lane_evaluation=lane_evaluation)
    payload["report_paths"] = _write_precondition_report(payload, output_root=output_root)
    return payload


def write_lane_replay_readiness_report(
    *,
    fixture_path: str | Path,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    dataset = build_lane_activity_history(fixture_path)
    lane_evaluation = evaluate_lane_activity_signals(dataset)
    payload = evaluate_lane_replay_readiness(
        lane_activity_dataset=dataset,
        lane_evaluation=lane_evaluation,
    )
    payload["report_paths"] = _write_lane_readiness_report(payload, output_root=output_root)
    return payload


def write_real_activity_replay_readiness_report(
    *,
    fixture_path: str | Path,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    dataset = build_activity_dataset_from_capture(fixture_path)
    lane_evaluation = evaluate_real_activity_signals(dataset)
    payload = evaluate_real_activity_replay_readiness(
        lane_activity_dataset=dataset,
        lane_evaluation=lane_evaluation,
    )
    payload["report_paths"] = _write_real_activity_readiness_report(
        payload,
        output_root=output_root,
    )
    return payload


def write_oos_replay_readiness_report(
    *,
    fixture_path: str | Path,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    dataset = build_activity_dataset_from_capture(fixture_path)
    validation = evaluate_lane_oos_validation(dataset)
    robustness = evaluate_lane_robustness(oos_validation=validation)
    payload = evaluate_oos_replay_readiness(
        lane_activity_dataset=dataset,
        oos_validation=validation,
        robustness=robustness,
    )
    payload["report_paths"] = _write_oos_readiness_report(payload, output_root=output_root)
    return payload


def write_venue_replay_readiness_report(
    *,
    fixture_path: str | Path,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    dataset = build_activity_dataset_from_capture(fixture_path)
    venue = evaluate_venue_signal_oos(dataset)
    ablation = evaluate_venue_signal_ablation(dataset=dataset, venue_evaluation=venue)
    decision = evaluate_lane_decision(dataset=dataset, venue_evaluation=venue, ablation=ablation)
    payload = evaluate_venue_replay_readiness(
        lane_activity_dataset=dataset,
        venue_evaluation=venue,
        ablation=ablation,
        lane_decision=decision,
    )
    payload["report_paths"] = _write_venue_readiness_report(payload, output_root=output_root)
    return payload


def _write_precondition_report(
    payload: dict[str, Any],
    *,
    output_root: str | Path,
) -> dict[str, str]:
    root = Path(output_root) / SEQUENCE23_REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_replay_preconditions.json"
    md_path = root / "latest_replay_preconditions.md"
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    lines = [
        "# Sequence 23 Replay Preconditions",
        "",
        "Research-only replay precondition report. No execution authority.",
        "",
        f"Replay precondition status: {payload['replay_precondition_status']}",
        f"Ready for narrow replay design: {payload['ready_for_narrow_replay_design']}",
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


def _write_lane_readiness_report(
    payload: dict[str, Any],
    *,
    output_root: str | Path,
) -> dict[str, str]:
    root = Path(output_root) / SEQUENCE24_REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_replay_readiness.json"
    md_path = root / "latest_replay_readiness.md"
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    lines = [
        "# Sequence 24 Lane Replay Readiness",
        "",
        "Research-only replay readiness report. No execution authority.",
        "",
        f"Lane: {payload['lane_id']}",
        f"Replay readiness: {payload['replay_readiness_status']}",
        f"Ready for narrow replay design: {payload['ready_for_narrow_replay_design']}",
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


def _write_real_activity_readiness_report(
    payload: dict[str, Any],
    *,
    output_root: str | Path,
) -> dict[str, str]:
    root = Path(output_root) / SEQUENCE25_REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_replay_readiness.json"
    md_path = root / "latest_replay_readiness.md"
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    lines = [
        "# Sequence 25 Real Activity Replay Readiness",
        "",
        "Research-only replay readiness report. No execution authority.",
        "",
        f"Lane: {payload['lane_id']}",
        f"Source mode: {payload['source_mode']}",
        f"Replay readiness: {payload['replay_readiness_status']}",
        f"Ready for narrow replay design: {payload['ready_for_narrow_replay_design']}",
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


def _write_oos_readiness_report(
    payload: dict[str, Any],
    *,
    output_root: str | Path,
) -> dict[str, str]:
    root = Path(output_root) / SEQUENCE26_REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_replay_readiness.json"
    md_path = root / "latest_replay_readiness.md"
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    lines = [
        "# Sequence 26 OOS Replay Readiness",
        "",
        "Research-only replay readiness report. No execution authority.",
        "",
        f"Lane: {payload['lane_id']}",
        f"Source mode: {payload['source_mode']}",
        f"Replay readiness: {payload['replay_readiness_status']}",
        f"Ready for narrow replay design: {payload['ready_for_narrow_replay_design']}",
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


def _write_venue_readiness_report(
    payload: dict[str, Any],
    *,
    output_root: str | Path,
) -> dict[str, str]:
    root = Path(output_root) / SEQUENCE27_REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_replay_readiness.json"
    md_path = root / "latest_replay_readiness.md"
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    lines = [
        "# Sequence 27 Venue-Signal Replay Readiness",
        "",
        "Research-only replay readiness report. No execution authority.",
        "",
        f"Lane: {payload['lane_id']}",
        f"Source mode: {payload['source_mode']}",
        f"Replay readiness: {payload['replay_readiness_status']}",
        f"Ready for minimal replay spec: {payload['ready_for_minimal_replay_spec']}",
        f"Ready for narrow replay design: {payload['ready_for_narrow_replay_design']}",
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


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_replay_feasibility.json"
    md_path = root / "latest_replay_feasibility.md"
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    lines = [
        "# Sequence 22 Replay Feasibility",
        "",
        "Research-only replay feasibility report. No execution authority.",
        "",
        f"Replay feasibility: {payload['replay_feasibility_status']}",
        f"Ready for narrow replay design: {payload['ready_for_narrow_replay_design']}",
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
