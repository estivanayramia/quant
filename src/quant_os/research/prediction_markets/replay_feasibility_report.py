from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.data.prediction_markets.resolution_dataset import build_resolution_aware_dataset
from quant_os.research.prediction_markets.candidate_predictions import (
    evaluate_prediction_candidate_signals,
)
from quant_os.research.prediction_markets.evaluation import evaluate_lanes
from quant_os.research.prediction_markets.replay_feasibility import (
    evaluate_replay_feasibility,
    evaluate_replay_preconditions,
)

REPORT_ROOT = Path("reports/sequence22/replay_feasibility")
SEQUENCE23_REPORT_ROOT = Path("reports/sequence23/replay_preconditions")


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
