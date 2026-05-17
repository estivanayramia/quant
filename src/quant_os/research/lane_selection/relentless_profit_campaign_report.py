from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPORT_ROOT = Path("reports/profit_campaign")


def write_profit_campaign_report(
    payload: dict[str, Any],
    *,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_profit_campaign.json"
    md_path = root / "latest_profit_campaign.md"
    payload = dict(payload)
    payload["report_paths"] = {"json": str(json_path), "markdown": str(md_path)}
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(_render_markdown(payload), encoding="utf-8")
    return payload


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Relentless Profit Campaign",
        "",
        "Bounded deterministic campaign run. No live orders, canary readiness, or unsupported profit claim.",
        "",
        f"Status: {payload['campaign_status']}",
        f"Paper status: {payload['paper_profit_status']}",
        f"Profit guard: {payload['profit_claim_guard_status']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        f"Execution authority: {payload['execution_authority']}",
        "",
        "## Lanes Attempted This Run",
    ]
    attempts = payload.get("attempts", [])
    if attempts:
        lines.extend(
            "- {lane_id}: {status} ({blockers})".format(
                lane_id=attempt["lane_id"],
                status=attempt["status"],
                blockers=", ".join(attempt.get("blockers", []) or ["None"]),
            )
            for attempt in attempts
        )
    else:
        lines.append("- None")
    lines.extend(["", "## Next Action", payload["next_action"]])
    return "\n".join(lines) + "\n"
