from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.data.prediction_markets.resolution_dataset import build_resolution_aware_dataset

REPORT_ROOT = Path("reports/sequence21/dataset")
SEQUENCE22_REPORT_ROOT = Path("reports/sequence22/dataset")


def write_historical_dataset_report(
    *,
    fixture_path: str | Path,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    dataset = build_resolution_aware_dataset(fixture_path)
    status, blockers = _dataset_readiness(dataset)
    payload = {
        **dataset,
        "research_readiness_status": status,
        "ready_for_replay_design": status == "READY_FOR_REPLAY_DESIGN",
        "blockers": blockers,
    }
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def write_expanded_historical_dataset_report(
    *,
    fixture_path: str | Path,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    dataset = build_resolution_aware_dataset(fixture_path)
    payload = {
        **dataset,
        "research_dataset_status": "EXPANDED_HISTORY_RESEARCH_ONLY",
        "replay_feasibility_status": "NOT_EVALUATED_IN_DATASET_REPORT",
        "ready_for_narrow_replay_design": False,
        "observed_facts": [
            *dataset["observed_facts"],
            "Sequence 22 expands resolved and unresolved prediction-market history from fixtures.",
        ],
        "inferred_patterns": [
            *dataset["inferred_patterns"],
            "Dataset growth enables less toy candidate evaluation but not execution readiness.",
        ],
        "unknowns": [
            *dataset["unknowns"],
            "Replay feasibility depends on candidate metrics and conservative gates outside this dataset summary.",
        ],
    }
    payload["report_paths"] = _write_expanded_report(payload, output_root=output_root)
    return payload


def _dataset_readiness(dataset: dict[str, Any]) -> tuple[str, list[str]]:
    blockers = []
    if dataset["resolution_summary"]["resolved_count"] < 5:
        blockers.append("INSUFFICIENT_RESOLVED_HISTORY")
    if dataset["included_market_count"] < 5:
        blockers.append("DATASET_TOO_THIN")
    if blockers:
        return "DATASET_TOO_THIN", blockers
    return "READY_FOR_REPLAY_DESIGN", []


def _write_expanded_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / SEQUENCE22_REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_dataset_summary.json"
    md_path = root / "latest_dataset_summary.md"
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    lines = [
        "# Sequence 22 Expanded Resolution History",
        "",
        "Research-only expanded historical dataset summary. No execution authority.",
        "",
        f"Dataset status: {payload['research_dataset_status']}",
        f"Markets: {payload['market_count']}",
        f"Included markets: {payload['included_market_count']}",
        f"Resolved: {payload['resolution_summary']['resolved_count']}",
        f"Excluded: {payload['resolution_summary']['excluded_count']}",
        f"Live promotion: {payload['live_promotion_status']}",
        "",
        "## Observed facts",
    ]
    lines.extend(f"- {item}" for item in payload["observed_facts"])
    lines.extend(["", "## Inferred patterns"])
    lines.extend(f"- {item}" for item in payload["inferred_patterns"])
    lines.extend(["", "## Unknowns"])
    lines.extend(f"- {item}" for item in payload["unknowns"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_dataset_summary.json"
    md_path = root / "latest_dataset_summary.md"
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    lines = [
        "# Sequence 21 Resolution-Aware Dataset",
        "",
        "Research-only historical dataset summary. No execution authority.",
        "",
        f"Readiness: {payload['research_readiness_status']}",
        f"Markets: {payload['market_count']}",
        f"Resolved: {payload['resolution_summary']['resolved_count']}",
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
