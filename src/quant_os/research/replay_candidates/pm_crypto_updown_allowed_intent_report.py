from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.research.replay_candidates.pm_crypto_updown_allowed_intent_diagnostics import (
    evaluate_pm_crypto_updown_allowed_intent_diagnostics,
)

REPORT_ROOT = Path("reports/sequence44/allowed_intent_diagnostics")


def write_pm_crypto_updown_allowed_intent_diagnostics_report(
    *,
    rows: list[dict[str, Any]] | None = None,
    signal_report: dict[str, Any] | None = None,
    fixture_root: str | Path | None = None,
    real_cached_artifact_roots: list[str | Path] | None = None,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    payload = evaluate_pm_crypto_updown_allowed_intent_diagnostics(
        rows=rows,
        signal_report=signal_report,
        fixture_root=fixture_root,
        real_cached_artifact_roots=real_cached_artifact_roots,
    )
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_allowed_intent_diagnostics.json"
    md_path = root / "latest_allowed_intent_diagnostics.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 44 Allowed Intent Diagnostics",
        "",
        "Allowed primary shadow intents only. Synthetic rows remain diagnostic.",
        "",
        f"Active blocker: {payload['active_blocker']}",
        f"Allowed primary intents: {payload['allowed_primary_intent_count']}",
        f"Allowed real-cached intents: {payload['allowed_real_cached_intent_count']}",
        f"Allowed synthetic diagnostic intents: {payload['allowed_synthetic_diagnostic_intent_count']}",
        f"Cost/fill adjusted result: {payload['cost_fill_adjusted_result']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        "",
        "## Blocker Causes",
    ]
    lines.extend(
        f"- {name}: {active}" for name, active in payload["blocker_causes"].items()
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
