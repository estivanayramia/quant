from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.data.historical_manifest import build_historical_manifest
from quant_os.data.historical_quality import run_historical_quality
from quant_os.data.provider_check import check_historical_providers
from quant_os.research.historical_evidence import (
    build_historical_splits,
    calculate_historical_evidence_score,
    run_historical_leakage_check,
)
from quant_os.research.leaderboard import build_strategy_leaderboard


def write_historical_research_report() -> dict[str, Any]:
    providers = check_historical_providers()
    manifest = build_historical_manifest()
    quality = run_historical_quality()
    splits = build_historical_splits()
    leakage = run_historical_leakage_check(splits_payload=splits)
    evidence = calculate_historical_evidence_score()
    leaderboard = build_strategy_leaderboard()
    payload = {
        "generated_at": evidence["generated_at"],
        "source_type": manifest["source_type"],
        "source_name": manifest["source_name"],
        "dataset_mode": "historical_local_cache",
        "provider_status": providers["providers"],
        "manifest_summary": {
            "dataset_id": manifest["dataset_id"],
            "rows": manifest["rows"],
            "symbols": manifest["symbols"],
            "timeframes": manifest["timeframes"],
        },
        "quality_summary": {
            "status": quality["status"],
            "failures": quality["failures"],
            "warnings": quality["warnings"],
        },
        "split_summary": {"status": splits["status"], "items": len(splits["items"])},
        "leakage_summary": {
            "status": leakage["status"],
            "target_leakage": leakage["target_leakage"],
        },
        "strategy_leaderboard_summary": {
            "top_strategy": leaderboard["top_strategy"],
            "data_source_type": leaderboard.get("data_source_type"),
        },
        "evidence_score": evidence,
        "blockers": evidence["blockers"],
        "warnings": evidence["warnings"],
        "live_promotion_status": "LIVE_BLOCKED",
        "next_commands": [
            "make.cmd historical-quality",
            "make.cmd historical-splits",
            "make.cmd historical-evidence-score",
            "make.cmd strategy-leaderboard",
        ],
    }
    _write_report(payload)
    return payload


def _write_report(payload: dict[str, Any]) -> None:
    root = Path("reports/historical/evidence")
    root.mkdir(parents=True, exist_ok=True)
    (root / "latest_historical_research_report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8"
    )
    lines = [
        "# Historical Research Evidence Report",
        "",
        "Local/cache-first historical research report. No live trading.",
        "",
        f"Source: {payload['source_name']} ({payload['source_type']})",
        f"Rows: {payload['manifest_summary']['rows']}",
        f"Quality: {payload['quality_summary']['status']}",
        f"Leakage: {payload['leakage_summary']['status']}",
        f"Evidence: {payload['evidence_score']['final_evidence_status']}",
        f"Live promotion: {payload['live_promotion_status']}",
        "",
        "## Blockers",
    ]
    lines.extend(f"- {blocker}" for blocker in payload["blockers"])
    lines.extend(["", "## Warnings"])
    lines.extend(f"- {warning}" for warning in (payload["warnings"] or ["None"]))
    lines.extend(["", "## Next Commands"])
    lines.extend(f"- `{command}`" for command in payload["next_commands"])
    (root / "latest_historical_research_report.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
