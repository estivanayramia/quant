from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

SAFETY_FLAGS: dict[str, Any] = {
    "live_trading_enabled": False,
    "execution_authority": "NONE",
    "order_transmission_enabled": False,
    "authenticated_requests_enabled": False,
    "actual_order_count": 0,
    "actual_cancel_count": 0,
    "manual_approval_required": True,
    "evidence_only": True,
}

FORBIDDEN_ACTIONS = [
    "live order placement",
    "order cancellation",
    "order routing",
    "wallet signing",
    "Kalshi credential usage",
    "authenticated trading requests",
    "quote acceptance",
    "anti-bot evasion",
]

STATE_JSON = Path("reports/canary_readiness/state/latest_state.json")
STATE_MD = Path("reports/canary_readiness/state/latest_state.md")


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def decimal_value(value: Any) -> Decimal:
    try:
        return Decimal(str(value if value is not None else "0"))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def load_json(path: str | Path, *, output_root: str | Path = ".") -> dict[str, Any] | None:
    resolved = Path(output_root) / Path(path)
    if not resolved.exists():
        return None
    return json.loads(resolved.read_text(encoding="utf-8"))


def load_rows(*, output_root: str | Path = ".") -> list[dict[str, Any]]:
    dataset = load_json(
        "reports/sequence52/weather_resolved_dataset/latest_weather_resolved_dataset.json",
        output_root=output_root,
    )
    if not dataset:
        return []
    return list(dataset.get("rows", []))


def load_paper_payload(*, output_root: str | Path = ".") -> dict[str, Any] | None:
    return load_json(
        "reports/sequence52/weather_batch_paper_proving/latest_weather_batch_paper_proving.json",
        output_root=output_root,
    )


def load_profit_payload(*, output_root: str | Path = ".") -> dict[str, Any] | None:
    return load_json("reports/profit_campaign/latest_profit_campaign.json", output_root=output_root)


def load_dataset_payload(*, output_root: str | Path = ".") -> dict[str, Any] | None:
    return load_json(
        "reports/sequence52/weather_resolved_dataset/latest_weather_resolved_dataset.json",
        output_root=output_root,
    )


def load_gate_payload(
    report_path: str | Path,
    *,
    output_root: str | Path = ".",
) -> dict[str, Any] | None:
    return load_json(report_path, output_root=output_root)


def write_json_markdown_report(
    payload: dict[str, Any],
    *,
    output_root: str | Path,
    report_dir: str | Path,
    json_name: str,
    md_name: str,
    title: str,
    summary: str,
) -> dict[str, str]:
    root = Path(output_root) / Path(report_dir)
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / json_name
    md_path = root / md_name
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        f"# {title}",
        "",
        summary,
        "",
        f"Status: {payload.get('status')}",
        f"Live trading enabled: {payload.get('live_trading_enabled', False)}",
        f"Execution authority: {payload.get('execution_authority', 'NONE')}",
        f"Order transmission enabled: {payload.get('order_transmission_enabled', False)}",
        "",
        "## Blockers",
    ]
    lines.extend(f"- {item}" for item in payload.get("blockers", []) or ["None"])
    if payload.get("next_action"):
        lines.extend(["", "## Next Action", f"- {payload['next_action']}"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def update_canary_state(
    *,
    output_root: str | Path,
    gate: str,
    gate_status: str,
    evidence_paths: dict[str, str],
    gates_passed: list[str] | None = None,
    gates_failed: list[str] | None = None,
    blocker: str | None = None,
    next_action: str = "Run the next canary readiness gate.",
    validation_status: str = "NOT_RUN",
) -> dict[str, Any]:
    root = Path(output_root)
    path = root / STATE_JSON
    existing: dict[str, Any] = {}
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
    passed = list(dict.fromkeys([*(existing.get("gates_passed", []) or []), *(gates_passed or [])]))
    failed = list(dict.fromkeys([*(existing.get("gates_failed", []) or []), *(gates_failed or [])]))
    state = {
        "schema_version": "canary_readiness_state_v1",
        "updated_at": utc_now(),
        "current_branch": existing.get("current_branch", "phase-55-tiny-canary-readiness-gates"),
        "candidate_id": existing.get("candidate_id", "pm_weather_forecast_market_mismatch"),
        "current_gate": gate,
        "current_gate_status": gate_status,
        "evidence_paths": {**(existing.get("evidence_paths", {}) or {}), gate: evidence_paths},
        "gates_passed": passed,
        "gates_failed": failed,
        "current_blocker": blocker,
        "next_action": next_action,
        "validation_status": validation_status,
        "exact_resume_command": "python -m quant_os.cli readiness tiny-canary-readiness",
        "safety_constraints": dict(SAFETY_FLAGS),
        "forbidden_actions": FORBIDDEN_ACTIONS,
    }
    state_path = root / STATE_JSON
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    md_path = root / STATE_MD
    md_lines = [
        "# Canary Readiness State",
        "",
        f"Status: {gate_status}",
        f"Candidate: {state['candidate_id']}",
        f"Current gate: {gate}",
        f"Current blocker: {blocker or 'None'}",
        f"Next action: {next_action}",
        f"Resume: `{state['exact_resume_command']}`",
        f"Live trading enabled: {state['safety_constraints']['live_trading_enabled']}",
        f"Execution authority: {state['safety_constraints']['execution_authority']}",
    ]
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return state


def safety_payload(**overrides: Any) -> dict[str, Any]:
    payload = dict(SAFETY_FLAGS)
    payload.update(overrides)
    return payload


def relative_status(status: str, passed: str) -> tuple[list[str], list[str]]:
    if status == passed:
        return [passed], []
    return [], [status]
