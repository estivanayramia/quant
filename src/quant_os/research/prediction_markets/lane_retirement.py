from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.research.prediction_markets.lane_decision import write_lane_decision_report

REPORT_ROOT = Path("reports/sequence28/lane_retirement")
LANE_RETIREMENT_SAFETY = {
    "execution_authority": "NONE",
    "wallet_signing_enabled": False,
    "live_trading_enabled": False,
    "copy_trading_enabled": False,
    "real_orders_enabled": False,
    "prediction_market_execution_authority_added": False,
}


def write_lane_retirement_report(
    *,
    fixture_path: str | Path,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    lane_decision = write_lane_decision_report(
        fixture_path=fixture_path,
        output_root=output_root,
    )
    payload = build_lane_retirement_record(lane_decision)
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def build_lane_retirement_record(lane_decision: dict[str, Any]) -> dict[str, Any]:
    retire = lane_decision["lane_decision_status"] == "LANE_RETIRE_CANDIDATE"
    status = "LANE_DEPRIORITIZED" if retire else "LANE_RETAINS_RESEARCH_PRIORITY"
    recommended_action = (
        "DEPRIORITIZE_SHORT_DATED_CLEAN_BINARY"
        if retire
        else lane_decision["recommended_action"]
    )
    return {
        "sequence": "28",
        "lane_id": lane_decision["lane_id"],
        "dataset_id": lane_decision["dataset_id"],
        "dataset_hash": lane_decision["dataset_hash"],
        "lane_retirement_status": status,
        "recommended_action": recommended_action,
        "replay_ready": False,
        "ready_for_minimal_replay_spec": False,
        "ready_for_narrow_replay_design": False,
        "blockers": lane_decision["blockers"],
        "why_the_lane_failed": [
            "Venue-specific signals did not beat the market baseline out of sample.",
            "Ablation did not identify a component that survives the market baseline.",
            "The lane evidence is negative enough to stop forcing replay design around it.",
        ],
        "why_not_replay_ready": [
            "No credible signal family survived the Sequence 27 evidence checks.",
            "Replay mechanics, fills, queue position, fees, and latency are intentionally unmodeled.",
            "A replay design would risk giving structure to a lane that has not earned it.",
        ],
        "why_merging_improves_honesty": [
            "Retirement records preserve negative evidence instead of hiding it in stale branches.",
            "Future work can shift to replay inputs or another lane without re-litigating weak evidence.",
            "The repo remains profit-first by refusing to promote unsupported research toward live.",
        ],
        **LANE_RETIREMENT_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_lane_retirement.json"
    md_path = root / "latest_lane_retirement.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 28 Lane Retirement",
        "",
        "Research-only lane retirement report. No execution authority.",
        "",
        f"Lane: {payload['lane_id']}",
        f"Status: {payload['lane_retirement_status']}",
        f"Recommended action: {payload['recommended_action']}",
        f"Replay ready: {payload['replay_ready']}",
        f"Live promotion: {payload['live_promotion_status']}",
        "",
        "## Why The Lane Failed",
    ]
    lines.extend(f"- {item}" for item in payload["why_the_lane_failed"])
    lines.extend(["", "## Why Not Replay Ready"])
    lines.extend(f"- {item}" for item in payload["why_not_replay_ready"])
    lines.extend(["", "## Why Merging Improves Honesty"])
    lines.extend(f"- {item}" for item in payload["why_merging_improves_honesty"])
    lines.extend(["", "## Blockers"])
    lines.extend(f"- {item}" for item in (payload["blockers"] or ["None"]))
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
