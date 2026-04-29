from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.proving.incident_log import summarize_incidents
from quant_os.proving.readiness import evaluate_proving_readiness
from quant_os.proving.run_history import build_status, load_proving_history

REPORT_JSON = Path("reports/proving/latest_proving_report.json")
REPORT_MD = Path("reports/proving/latest_proving_report.md")


def write_proving_report() -> dict[str, Any]:
    history = load_proving_history()
    status = build_status(history)
    incidents = summarize_incidents()
    readiness = evaluate_proving_readiness(history)
    payload = {
        "status": readiness["readiness_status"],
        "dry_run_only": True,
        "live_trading_enabled": False,
        "history_records_count": len(history),
        "readiness_status": readiness["readiness_status"],
        "blockers": readiness["blockers"],
        "warnings": readiness["warnings"],
        "unresolved_incidents": incidents["unresolved_count"],
        "streaks": status["streaks"],
        "stability_summary": readiness["stability"],
        "freshness_summary": readiness["freshness"],
        "live_promotion_status": "LIVE_BLOCKED",
        "next_commands": [
            "make.cmd proving-run-once",
            "make.cmd proving-status",
            "make.cmd proving-readiness",
        ],
    }
    _write_report(payload)
    return payload


def _write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8"
    )
    lines = [
        "# Proving Mode Report",
        "",
        "Autonomous proving evidence for simulation/dry-run modes only. No live trading.",
        "",
        f"Readiness: {payload['readiness_status']}",
        f"History records: {payload['history_records_count']}",
        f"Unresolved incidents: {payload['unresolved_incidents']}",
        f"Current success streak: {payload['streaks']['current_success_streak']}",
        f"Current failure streak: {payload['streaks']['current_failure_streak']}",
        f"Live promotion: {payload['live_promotion_status']}",
        "",
        "## Blockers",
    ]
    lines.extend(f"- {item}" for item in (payload["blockers"] or ["None"]))
    lines.extend(["", "## Next Commands"])
    lines.extend(f"- `{command}`" for command in payload["next_commands"])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
