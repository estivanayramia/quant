from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.data.prediction_markets.activity_capture import build_activity_dataset_from_capture
from quant_os.data.prediction_markets.activity_history import build_lane_activity_history

REPORT_ROOT = Path("reports/sequence25/dataset")


def write_activity_dataset_growth_report(
    *,
    previous_fixture_path: str | Path,
    expanded_fixture_path: str | Path,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    previous = build_lane_activity_history(previous_fixture_path)
    expanded = build_activity_dataset_from_capture(expanded_fixture_path)
    payload = {
        "sequence": "25",
        "source": expanded["source"],
        "source_mode": expanded["source_mode"],
        "lane_id": expanded["lane_id"],
        "previous_dataset_id": previous["dataset_id"],
        "expanded_dataset_id": expanded["dataset_id"],
        "previous_dataset_hash": previous["dataset_hash"],
        "expanded_dataset_hash": expanded["dataset_hash"],
        "market_delta": expanded["market_count"] - previous["market_count"],
        "resolved_delta": expanded["resolved_market_count"] - previous["resolved_market_count"],
        "activity_observation_delta": (
            expanded["activity_observation_count"] - previous["activity_observation_count"]
        ),
        "previous_summary": _summary(previous),
        "expanded_summary": _summary(expanded),
        "observed_facts": [
            "Sequence 25 compares saved Phase 24 fixture-like activity to real-cached activity.",
        ],
        "inferred_patterns": [
            "Dataset growth improves research evidence only if quality and baseline tests also improve.",
        ],
        "unknowns": [
            "More activity observations do not imply edge or replay readiness.",
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
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _summary(dataset: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_mode": dataset["source_mode"],
        "market_count": dataset["market_count"],
        "included_market_count": dataset["included_market_count"],
        "resolved_market_count": dataset["resolved_market_count"],
        "activity_observation_count": dataset["activity_observation_count"],
    }


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_activity_growth.json"
    md_path = root / "latest_activity_growth.md"
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    lines = [
        "# Sequence 25 Activity Dataset Growth",
        "",
        "Research-only activity growth report. No execution authority.",
        "",
        f"Lane: {payload['lane_id']}",
        f"Market delta: {payload['market_delta']}",
        f"Resolved delta: {payload['resolved_delta']}",
        f"Activity observation delta: {payload['activity_observation_delta']}",
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
