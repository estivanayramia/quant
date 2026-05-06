from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.data.prediction_markets.activity_capture import build_activity_dataset_from_capture

REPORT_ROOT = Path("reports/sequence25/dataset")


def evaluate_lane_activity_quality(dataset: dict[str, Any]) -> dict[str, Any]:
    included = [market for market in dataset["markets"] if market["included_in_lane_activity_research"]]
    usable_counts = [market["activity_density"]["usable_event_count"] for market in included]
    warnings = []
    if dataset["source_mode"] != "real_cached":
        warnings.append("INSUFFICIENT_REAL_ACTIVITY")
    if min(usable_counts or [0]) < 5:
        warnings.append("ACTIVITY_DATA_TOO_THIN")
    if dataset.get("malformed_event_count", 0) > 0:
        warnings.append("MALFORMED_EVENTS_PRESENT_BUT_EXCLUDED")
    warnings.append("REPLAY_INPUTS_NOT_FULL_ORDER_BOOK_OR_FILL_MODEL")
    status = (
        "REAL_CACHED_ACTIVITY_USABLE_BUT_REPLAY_LIMITED"
        if dataset["source_mode"] == "real_cached" and min(usable_counts or [0]) >= 5
        else "ACTIVITY_DATA_TOO_THIN"
    )
    return {
        "sequence": "25",
        "source": dataset["source"],
        "source_mode": dataset["source_mode"],
        "lane_id": dataset["lane_id"],
        "dataset_id": dataset["dataset_id"],
        "dataset_hash": dataset["dataset_hash"],
        "activity_quality_status": status,
        "summary": {
            "included_market_count": len(included),
            "resolved_market_count": dataset["resolved_market_count"],
            "activity_observation_count": dataset["activity_observation_count"],
            "raw_event_count": dataset.get("raw_event_count", dataset["activity_observation_count"]),
            "usable_event_count": dataset.get("usable_event_count", dataset["activity_observation_count"]),
            "malformed_event_count": dataset.get("malformed_event_count", 0),
            "min_events_per_included_market": min(usable_counts or [0]),
            "max_events_per_included_market": max(usable_counts or [0]),
        },
        "warnings": warnings,
        "observed_facts": [
            "Activity quality uses saved normalized event counts and lane inclusion status.",
        ],
        "inferred_patterns": [
            "Real-cached activity is usable for research but still incomplete for replay mechanics.",
        ],
        "unknowns": [
            "Queue position, fees, fill mechanics, and full order-book depth remain unknown.",
        ],
        "execution_authority": "NONE",
        "wallet_signing_enabled": False,
        "live_trading_enabled": False,
        "copy_trading_enabled": False,
        "real_orders_enabled": False,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_lane_activity_quality_report(
    *,
    fixture_path: str | Path,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    dataset = build_activity_dataset_from_capture(fixture_path)
    payload = evaluate_lane_activity_quality(dataset)
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_activity_quality.json"
    md_path = root / "latest_activity_quality.md"
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    lines = [
        "# Sequence 25 Activity Quality",
        "",
        "Research-only activity quality report. No execution authority.",
        "",
        f"Lane: {payload['lane_id']}",
        f"Quality status: {payload['activity_quality_status']}",
        f"Warnings: {', '.join(payload['warnings'])}",
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
