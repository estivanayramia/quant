from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.data.prediction_markets.resolution_dataset import build_resolution_aware_dataset

REPORT_ROOT = Path("reports/sequence22/dataset")
DATASET_GROWTH_SAFETY = {
    "execution_authority": "NONE",
    "wallet_signing_enabled": False,
    "live_trading_enabled": False,
    "copy_trading_enabled": False,
    "real_orders_enabled": False,
}


def build_dataset_growth(
    *,
    previous_fixture_path: str | Path,
    expanded_fixture_path: str | Path,
) -> dict[str, Any]:
    previous = build_resolution_aware_dataset(previous_fixture_path)
    expanded = build_resolution_aware_dataset(expanded_fixture_path)
    return {
        "sequence": "22",
        "source": "polymarket",
        "source_mode": expanded["source_mode"],
        "previous_dataset": _dataset_summary(previous),
        "expanded_dataset": _dataset_summary(expanded),
        "market_delta": expanded["market_count"] - previous["market_count"],
        "included_market_delta": expanded["included_market_count"]
        - previous["included_market_count"],
        "resolved_delta": expanded["resolution_summary"]["resolved_count"]
        - previous["resolution_summary"]["resolved_count"],
        "snapshot_delta": expanded["snapshot_count"] - previous["snapshot_count"],
        "observed_facts": [
            "Growth is measured from saved offline fixtures only.",
            "Expanded history preserves market identifiers, resolution state, snapshots, and provenance.",
        ],
        "inferred_patterns": [
            "Expanded coverage makes candidate evaluation less toy-like but still research-only.",
        ],
        "unknowns": [
            "Fixture growth is not evidence of alpha, calibration quality, or execution readiness.",
        ],
        **DATASET_GROWTH_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_dataset_growth_report(
    *,
    previous_fixture_path: str | Path,
    expanded_fixture_path: str | Path,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    payload = build_dataset_growth(
        previous_fixture_path=previous_fixture_path,
        expanded_fixture_path=expanded_fixture_path,
    )
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _dataset_summary(dataset: dict[str, Any]) -> dict[str, Any]:
    return {
        "dataset_id": dataset["dataset_id"],
        "dataset_hash": dataset["dataset_hash"],
        "sequence": dataset["sequence"],
        "market_count": dataset["market_count"],
        "included_market_count": dataset["included_market_count"],
        "snapshot_count": dataset["snapshot_count"],
        "resolution_summary": dataset["resolution_summary"],
        "source_path": dataset["source_path"],
    }


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_dataset_growth.json"
    md_path = root / "latest_dataset_growth.md"
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    lines = [
        "# Sequence 22 Dataset Growth",
        "",
        "Research-only dataset growth report. No execution authority.",
        "",
        f"Market delta: {payload['market_delta']}",
        f"Resolved delta: {payload['resolved_delta']}",
        f"Snapshot delta: {payload['snapshot_delta']}",
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
