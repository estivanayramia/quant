from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_dry_run_proving_report(
    payload: dict[str, Any],
    *,
    output_root: str | Path = ".",
) -> dict[str, str]:
    root = Path(output_root) / "reports" / "sequence2" / "proving"
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_proving_summary.json"
    md_path = root / "latest_proving_summary.md"
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    lines = [
        "# Sequence 2 Dry-Run Proving",
        "",
        "Deterministic simulation and dry-run evidence only. No live trading.",
        "",
        f"Status: {payload['status']}",
        f"Allowed actions: {payload['allowed_action_count']}",
        f"Blocked actions: {payload['blocked_action_count']}",
        f"Replay/dry-run drift bps: {payload['replay_to_dry_run_drift_bps']:.4f}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        "",
        "## Block Reasons",
    ]
    lines.extend(f"- {item}" for item in (payload.get("block_reasons") or ["None"]))
    lines.extend(["", "## Warnings"])
    lines.extend(f"- {item}" for item in (payload.get("warnings") or ["None"]))
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
