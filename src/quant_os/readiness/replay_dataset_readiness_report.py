from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.readiness.replay_dataset_readiness import evaluate_replay_dataset_readiness

REPORT_ROOT = Path("reports/sequence36/replay_dataset_readiness")


def write_replay_dataset_readiness_report(
    *,
    dataset_report: dict[str, Any],
    output_root: str | Path = ".",
) -> dict[str, Any]:
    payload = evaluate_replay_dataset_readiness(dataset_report=dataset_report)
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_replay_dataset_readiness.json"
    md_path = root / "latest_replay_dataset_readiness.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 36 Replay Dataset Readiness",
        "",
        "Conservative readiness gate for candidate replay testing only.",
        "",
        f"Status: {payload['readiness_status']}",
        f"Ready for Phase 37 candidate replay: {payload['ready_for_phase37_candidate_replay']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        "",
        "## Blockers",
    ]
    lines.extend(f"- {item}" for item in (payload["blockers"] or ["None"]))
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
