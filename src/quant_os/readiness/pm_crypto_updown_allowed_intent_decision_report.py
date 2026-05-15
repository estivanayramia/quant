from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.readiness.autonomy_milestone_report import (
    write_sequence45_autonomy_milestone_report,
)
from quant_os.readiness.pm_crypto_updown_allowed_intent_decision import (
    evaluate_pm_crypto_updown_allowed_intent_decision,
)

REPORT_ROOT = Path("reports/sequence45/candidate_decision")


def write_pm_crypto_updown_allowed_intent_decision_report(
    *,
    rows: list[dict[str, Any]] | None = None,
    signal_report: dict[str, Any] | None = None,
    fixture_root: str | Path | None = None,
    real_cached_artifact_roots: list[str | Path] | None = None,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    payload = evaluate_pm_crypto_updown_allowed_intent_decision(
        rows=rows,
        signal_report=signal_report,
        fixture_root=fixture_root,
        real_cached_artifact_roots=real_cached_artifact_roots,
    )
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    autonomy = write_sequence45_autonomy_milestone_report(
        candidate_decision=payload,
        output_root=output_root,
    )
    payload["autonomy_milestone_report_paths"] = autonomy["report_paths"]
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_pm_crypto_updown_candidate_decision.json"
    md_path = root / "latest_pm_crypto_updown_candidate_decision.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 45 PM Crypto UP/DOWN Candidate Decision",
        "",
        "Allowed-intent evidence expansion gate. This is not live or canary readiness.",
        "",
        f"Decision status: {payload['decision_status']}",
        f"Ready for bounded shadow rehearsal: {payload['ready_for_bounded_shadow_rehearsal']}",
        f"Primary rows: {payload['primary_evidence_row_count']} / {payload['minimum_primary_rows_for_bounded_shadow']}",
        f"Allowed primary intents: {payload['allowed_primary_intent_count']} / {payload['minimum_allowed_primary_intents']}",
        f"Allowed real-cached intents: {payload['allowed_real_cached_intent_count']} / {payload['minimum_allowed_real_cached_intents']}",
        f"Precise next action: {payload['precise_next_action']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        f"Execution authority: {payload['execution_authority']}",
        "",
        "## Blockers",
    ]
    lines.extend(f"- {item}" for item in payload["blockers"] or ["None"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
