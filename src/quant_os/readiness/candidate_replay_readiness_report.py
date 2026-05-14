from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.readiness.autonomy_milestone_report import (
    write_sequence37_autonomy_milestone_report,
)
from quant_os.readiness.candidate_replay_readiness import evaluate_candidate_replay_readiness

REPORT_ROOT = Path("reports/sequence37/replay_readiness")


def write_candidate_replay_readiness_report(
    *,
    evaluation_report: dict[str, Any],
    output_root: str | Path = ".",
) -> dict[str, Any]:
    payload = evaluate_candidate_replay_readiness(evaluation_report=evaluation_report)
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    autonomy = write_sequence37_autonomy_milestone_report(
        candidate_replay_readiness=payload,
        output_root=output_root,
    )
    payload["autonomy_milestone_report_paths"] = autonomy["report_paths"]
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_candidate_replay_readiness.json"
    md_path = root / "latest_candidate_replay_readiness.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 37 Candidate Replay Readiness",
        "",
        "Strict gate for expanded offline shadow replay only. Live and canary remain blocked.",
        "",
        f"Status: {payload['readiness_status']}",
        f"Ready for expanded shadow replay: {payload['ready_for_expanded_shadow_replay']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        f"Canary readiness claimed: {payload['canary_readiness_claimed']}",
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
