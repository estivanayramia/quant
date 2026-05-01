from __future__ import annotations

import json
from pathlib import Path
from typing import Any

LIVE_CANARY_ROOT = Path("reports/live_canary")


def write_live_canary_report(
    json_path: str | Path,
    md_path: str | Path,
    title: str,
    payload: dict[str, Any],
) -> None:
    json_file = Path(json_path)
    md_file = Path(md_path)
    json_file.parent.mkdir(parents=True, exist_ok=True)
    json_file.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    lines = [
        f"# {title}",
        "",
        "Tiny-live crypto canary lane. Live is default-off, heavily gated, and never autonomous.",
        "",
        f"Status: {payload.get('status', 'UNKNOWN')}",
        f"Real order possible: {payload.get('real_order_possible', False)}",
        f"Real order attempted: {payload.get('real_order_attempted', False)}",
        f"Live promotion: {payload.get('live_promotion_status', 'LIVE_BLOCKED')}",
        f"Mode: {payload.get('mode', 'blocked')}",
        "",
    ]
    blockers = payload.get("blockers") or []
    lines.append("## Blockers")
    lines.extend(f"- {item}" for item in (blockers or ["None"]))
    lines.append("")
    warnings = payload.get("warnings") or []
    lines.append("## Warnings")
    lines.extend(f"- {item}" for item in (warnings or ["None"]))
    lines.append("")
    if "allowed_symbols" in payload:
        lines.append("## Allowed Symbols")
        lines.extend(f"- `{symbol}`" for symbol in payload["allowed_symbols"])
        lines.append("")
    if "max_order_notional_usd" in payload:
        lines.append(f"Max order notional USD: {payload['max_order_notional_usd']}")
        lines.append("")
    next_commands = payload.get("next_commands") or []
    if next_commands:
        lines.append("## Next Commands")
        lines.extend(f"- `{command}`" for command in next_commands)
        lines.append("")
    md_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

