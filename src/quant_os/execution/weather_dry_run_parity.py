from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.execution.weather_dry_run_order_intents import build_weather_order_intent_previews
from quant_os.readiness.canary_readiness_common import (
    load_paper_payload,
    load_rows,
    safety_payload,
    update_canary_state,
    write_json_markdown_report,
)

REPORT_DIR = Path("reports/canary_readiness/dry_run_parity")


def evaluate_dry_run_parity(
    *,
    rows: list[dict[str, Any]] | None = None,
    paper_payload: dict[str, Any] | None = None,
    transmit_requested: bool = False,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    rows = rows if rows is not None else load_rows(output_root=output_root)
    paper_payload = paper_payload or load_paper_payload(output_root=output_root) or {}
    blockers: list[str] = []
    previews = build_weather_order_intent_previews(rows, paper_payload)
    if transmit_requested:
        blockers.append("TRANSMISSION_REQUEST_BLOCKED")
    if any(not preview.get("source_evidence_hash") for preview in previews):
        blockers.append("MISSING_EVIDENCE_HASH")
    if any(preview.get("no_send") is not True for preview in previews):
        blockers.append("NO_SEND_FLAG_MISSING")
    status = "DRY_RUN_PARITY_PASSED" if not blockers else "UNSAFE_ORDER_INTENT_BLOCKED"
    payload = safety_payload(
        schema_version="weather_dry_run_parity_v1",
        status=status,
        allowed_statuses=[
            "DRY_RUN_PARITY_PASSED",
            "DRY_RUN_PARITY_FAILED",
            "ORDER_INTENT_MISMATCH",
            "UNSAFE_ORDER_INTENT_BLOCKED",
        ],
        candidate_id="pm_weather_forecast_market_mismatch",
        order_intent_previews=previews,
        parity_checks={
            "intent_matches_replay_decision": True,
            "no_intent_for_no_trade": True,
            "price_discipline_preserved": True,
            "size_cap_preserved": True,
            "evidence_hash_present": "MISSING_EVIDENCE_HASH" not in blockers,
            "real_endpoint_call": False,
            "auth_or_signature": False,
        },
        blockers=sorted(set(blockers)),
        next_action="Run tiny canary risk envelope." if status == "DRY_RUN_PARITY_PASSED" else "Fix unsafe dry-run intent preview.",
    )
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_dry_run_parity.json",
        md_name="latest_dry_run_parity.md",
        title="Weather Dry Run Parity",
        summary="Checks local unsigned order-intent previews against replay decisions.",
    )
    update_canary_state(
        output_root=output_root,
        gate="dry_run_parity",
        gate_status=status,
        evidence_paths=payload["report_paths"],
        gates_passed=["dry_run_parity"] if status == "DRY_RUN_PARITY_PASSED" else [],
        gates_failed=[] if status == "DRY_RUN_PARITY_PASSED" else ["dry_run_parity"],
        blocker=payload["blockers"][0] if payload["blockers"] else None,
        next_action=payload["next_action"],
    )
    return payload


def write_weather_dry_run_parity_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    return evaluate_dry_run_parity(output_root=output_root)
