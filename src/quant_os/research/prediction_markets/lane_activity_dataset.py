from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.data.prediction_markets.activity_capture import build_activity_dataset_from_capture
from quant_os.data.prediction_markets.activity_history import build_lane_activity_history

REPORT_ROOT = Path("reports/sequence24/dataset")
SEQUENCE25_REPORT_ROOT = Path("reports/sequence25/dataset")


def write_lane_activity_dataset_report(
    *,
    fixture_path: str | Path,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    dataset = build_lane_activity_history(fixture_path)
    payload = {
        **dataset,
        "research_dataset_status": "LANE_ACTIVITY_RESEARCH_ONLY",
        "ready_for_narrow_replay_design": False,
        "observed_facts": [
            *dataset["observed_facts"],
            "Sequence 24 focuses only on the best Phase 23 lane.",
        ],
        "inferred_patterns": [
            *dataset["inferred_patterns"],
            "Richer within-market history can support dynamic signal research.",
        ],
        "unknowns": [
            *dataset["unknowns"],
            "This dataset does not prove signal credibility by itself.",
        ],
    }
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def write_sequence25_activity_dataset_report(
    *,
    fixture_path: str | Path,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    dataset = build_activity_dataset_from_capture(fixture_path)
    payload = {
        **dataset,
        "research_dataset_status": "REAL_CACHED_ACTIVITY_RESEARCH_ONLY",
        "ready_for_narrow_replay_design": False,
        "observed_facts": [
            *dataset["observed_facts"],
            "Sequence 25 converts a saved real-cached public Polymarket activity artifact into lane history.",
        ],
        "inferred_patterns": [
            *dataset["inferred_patterns"],
            "Real-cached activity improves evidence quality but does not prove a signal.",
        ],
        "unknowns": [
            *dataset["unknowns"],
            "Saved activity is not yet a full order book, fee, fill, or replay-realism model.",
        ],
    }
    payload["report_paths"] = _write_sequence25_report(payload, output_root=output_root)
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_lane_activity_dataset.json"
    md_path = root / "latest_lane_activity_dataset.md"
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    lines = [
        "# Sequence 24 Lane Activity Dataset",
        "",
        "Research-only lane activity dataset report. No execution authority.",
        "",
        f"Lane: {payload['lane_id']}",
        f"Dataset status: {payload['research_dataset_status']}",
        f"Markets: {payload['market_count']}",
        f"Included markets: {payload['included_market_count']}",
        f"Resolved markets: {payload['resolved_market_count']}",
        f"Activity observations: {payload['activity_observation_count']}",
        f"Activity depth: {payload['activity_depth_status']}",
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


def _write_sequence25_report(
    payload: dict[str, Any],
    *,
    output_root: str | Path,
) -> dict[str, str]:
    root = Path(output_root) / SEQUENCE25_REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_activity_dataset.json"
    md_path = root / "latest_activity_dataset.md"
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    lines = [
        "# Sequence 25 Activity Dataset",
        "",
        "Research-only real-cached activity dataset report. No execution authority.",
        "",
        f"Lane: {payload['lane_id']}",
        f"Dataset status: {payload['research_dataset_status']}",
        f"Source mode: {payload['source_mode']}",
        f"Markets: {payload['market_count']}",
        f"Resolved markets: {payload['resolved_market_count']}",
        f"Activity observations: {payload['activity_observation_count']}",
        f"Malformed events: {payload['malformed_event_count']}",
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
