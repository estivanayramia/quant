from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.readiness.canary_readiness_common import (
    load_paper_payload,
    load_rows,
    safety_payload,
    update_canary_state,
    write_json_markdown_report,
)

REPORT_DIR = Path("reports/canary_readiness/shadow_rehearsal")


def run_bounded_shadow_rehearsal(
    *,
    rows: list[dict[str, Any]] | None = None,
    paper_payload: dict[str, Any] | None = None,
    output_root: str | Path = ".",
    max_hypothetical_exposure: float = 100.0,
    max_intents_per_day: int = 100,
) -> dict[str, Any]:
    rows = rows if rows is not None else load_rows(output_root=output_root)
    paper_payload = paper_payload or load_paper_payload(output_root=output_root) or {}
    decisions = {item.get("market_id"): item for item in paper_payload.get("paper_intents", []) or []}
    exposure = 0.0
    daily_counts: dict[str, int] = {}
    blockers: list[str] = []
    ledger = []
    for row in sorted(rows, key=lambda item: str(item.get("orderbook_ts", ""))):
        decision = decisions.get(row.get("market_id"), {"intent": "NO_TRADE"})
        day = str(row.get("orderbook_ts", ""))[:10]
        intent = str(decision.get("intent"))
        blocked = []
        if intent != "NO_TRADE":
            daily_counts[day] = daily_counts.get(day, 0) + 1
            if daily_counts[day] > max_intents_per_day:
                blocked.append("MAX_INTENTS_PER_DAY")
            if exposure + 1.0 > max_hypothetical_exposure:
                blocked.append("MAX_HYPOTHETICAL_EXPOSURE")
            if not blocked:
                exposure += 1.0
        ledger.append(
            {
                "event_type": "shadow_intent",
                "market_id": row.get("market_id"),
                "expected_replay_decision": intent,
                "actual_shadow_decision": "BLOCKED" if blocked else intent,
                "blocked_reasons": blocked,
                "offline_only": True,
                "no_send": True,
            }
        )
    if any(event["blocked_reasons"] for event in ledger):
        blockers.append("SHADOW_INTENT_BLOCKED_BY_BOUNDS")
    status = "BOUNDED_SHADOW_REHEARSAL_PASSED" if not blockers else "BOUNDED_SHADOW_REHEARSAL_FAILED"
    payload = safety_payload(
        schema_version="weather_bounded_shadow_rehearsal_v1",
        status=status,
        allowed_statuses=[
            "BOUNDED_SHADOW_REHEARSAL_PASSED",
            "BOUNDED_SHADOW_REHEARSAL_FAILED",
            "SHADOW_REHEARSAL_DIAGNOSTIC_ONLY",
            "SHADOW_REHEARSAL_BLOCKED",
        ],
        candidate_id="pm_weather_forecast_market_mismatch",
        max_hypothetical_exposure=max_hypothetical_exposure,
        max_intents_per_day=max_intents_per_day,
        event_ledger=ledger,
        blocked_intents=[event for event in ledger if event["blocked_reasons"]],
        self_disabled=bool(blockers),
        blockers=blockers,
        next_action="Run dry-run order-intent parity." if status == "BOUNDED_SHADOW_REHEARSAL_PASSED" else "Fix shadow rehearsal bounds or replay mismatch.",
    )
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_shadow_rehearsal.json",
        md_name="latest_shadow_rehearsal.md",
        title="Weather Bounded Shadow Rehearsal",
        summary="Replays offline shadow intents without transmission or signing.",
    )
    update_canary_state(
        output_root=output_root,
        gate="shadow_rehearsal",
        gate_status=status,
        evidence_paths=payload["report_paths"],
        gates_passed=["shadow_rehearsal"] if status == "BOUNDED_SHADOW_REHEARSAL_PASSED" else [],
        gates_failed=[] if status == "BOUNDED_SHADOW_REHEARSAL_PASSED" else ["shadow_rehearsal"],
        blocker=blockers[0] if blockers else None,
        next_action=payload["next_action"],
    )
    return payload


def write_weather_bounded_shadow_rehearsal_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    return run_bounded_shadow_rehearsal(output_root=output_root)
