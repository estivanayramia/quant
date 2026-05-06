from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.data.prediction_markets.activity_capture import build_activity_dataset_from_capture
from quant_os.research.prediction_markets.market_quality_filters import (
    evaluate_market_quality_filters,
)

REPORT_ROOT = Path("reports/sequence27/manipulation_flags")
MANIPULATION_FLAG_SAFETY = {
    "execution_authority": "NONE",
    "wallet_signing_enabled": False,
    "live_trading_enabled": False,
    "copy_trading_enabled": False,
    "real_orders_enabled": False,
}


def evaluate_manipulation_flags(dataset: dict[str, Any]) -> dict[str, Any]:
    quality = evaluate_market_quality_filters(dataset)
    flagged = [
        row
        for row in quality["market_quality"]
        if set(row["quality_flags"])
        & {
            "JUMP_WITHOUT_SUPPORTING_LIQUIDITY",
            "CONCENTRATION_SPIKE",
            "SUSPICIOUS_THINNESS",
            "MISSING_REFERENCE_CONTEXT",
        }
    ]
    return {
        "sequence": "27",
        "source": dataset["source"],
        "source_mode": dataset["source_mode"],
        "lane_id": dataset["lane_id"],
        "dataset_id": dataset["dataset_id"],
        "dataset_hash": dataset["dataset_hash"],
        "manipulation_flag_status": "HEURISTIC_FLAGS_RESEARCH_ONLY",
        "summary": {
            "market_count": quality["summary"]["market_count"],
            "flagged_market_count": quality["summary"]["flagged_market_count"],
            "manipulation_or_fake_quality_flag_count": len(flagged),
        },
        "flag_counts": quality["flag_counts"],
        "flagged_markets": flagged,
        "observed_facts": [
            "Manipulation flags are heuristic diagnostics, not certainty labels.",
        ],
        "inferred_patterns": [
            "Suspicious activity can disqualify markets from signal testing without implying fraud.",
        ],
        "unknowns": [
            "Wallet identities and participant intent are not known from this read-only artifact.",
        ],
        **MANIPULATION_FLAG_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_manipulation_flags_report(
    *,
    fixture_path: str | Path,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    dataset = build_activity_dataset_from_capture(fixture_path)
    payload = evaluate_manipulation_flags(dataset)
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_manipulation_flags.json"
    md_path = root / "latest_manipulation_flags.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 27 Manipulation Flags",
        "",
        "Research-only manipulation/fake-quality report. No execution authority.",
        "",
        f"Lane: {payload['lane_id']}",
        f"Flag status: {payload['manipulation_flag_status']}",
        f"Flagged markets: {payload['summary']['flagged_market_count']}",
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
