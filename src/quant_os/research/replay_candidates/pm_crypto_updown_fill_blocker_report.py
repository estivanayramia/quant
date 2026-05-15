from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.research.replay_candidates.pm_crypto_updown_fill_blocker_attribution import (
    evaluate_pm_crypto_updown_fill_blocker_attribution,
)

REPORT_ROOT = Path("reports/sequence43/fill_blockers")


def write_pm_crypto_updown_fill_blocker_attribution_report(
    *,
    rows: list[dict[str, Any]],
    signal_report: dict[str, Any] | None = None,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    payload = evaluate_pm_crypto_updown_fill_blocker_attribution(
        rows=rows,
        signal_report=signal_report,
    )
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_fill_blocker_attribution.json"
    md_path = root / "latest_fill_blocker_attribution.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 43 Fill Blocker Attribution",
        "",
        "Deterministic attribution for COST_FILL_BLOCKED under conservative offline execution assumptions.",
        "",
        f"Rows: {payload['row_count']}",
        f"Blocked rows: {payload['blocked_row_count']}",
        "Potentially tradeable rows: "
        f"{payload['rows_still_potentially_tradeable_under_conservative_assumptions']}",
        f"Execution authority: {payload['execution_authority']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        "",
        "## Primary Blockers",
    ]
    counts = payload["blocked_counts_by_reason"]
    if not counts:
        lines.append("- None")
    else:
        lines.extend(f"- {reason}: {count}" for reason, count in counts.items())
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
