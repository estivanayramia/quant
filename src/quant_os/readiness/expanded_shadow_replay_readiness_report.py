from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.readiness.autonomy_milestone_report import (
    write_sequence38_autonomy_milestone_report,
)
from quant_os.readiness.expanded_shadow_replay_readiness import (
    evaluate_expanded_shadow_replay_readiness,
)

REPORT_ROOT = Path("reports/sequence38/expanded_shadow_replay_readiness")


def write_expanded_shadow_replay_readiness_report(
    *,
    expanded_replay_eval: dict[str, Any],
    output_root: str | Path = ".",
) -> dict[str, Any]:
    payload = evaluate_expanded_shadow_replay_readiness(
        expanded_replay_eval=expanded_replay_eval,
    )
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    autonomy = write_sequence38_autonomy_milestone_report(
        expanded_shadow_readiness=payload,
        output_root=output_root,
    )
    payload["autonomy_milestone_report_paths"] = autonomy["report_paths"]
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_expanded_shadow_replay_readiness.json"
    md_path = root / "latest_expanded_shadow_replay_readiness.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 38 Expanded Shadow Replay Readiness",
        "",
        "Gate for expanded offline shadow replay only. Live and canary remain blocked.",
        "",
        f"Overall status: {payload['overall_status']}",
        f"Readiness status: {payload['readiness_status']}",
        f"Primary evidence rows: {payload['primary_evidence_row_count']}",
        f"Ready for expanded shadow replay: {payload['ready_for_expanded_shadow_replay']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        "",
        "## Blockers",
    ]
    lines.extend(f"- {item}" for item in (payload["blockers"] or ["None"]))
    lines.extend(["", "## Autonomy Movement"])
    lines.extend(
        f"- {key}: {value}" for key, value in payload["autonomy_milestones"].items()
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
