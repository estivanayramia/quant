from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from quant_os.execution.shadow_execution_policy import generate_shadow_order_intents
from quant_os.execution.shadow_risk import evaluate_shadow_risk
from quant_os.replay.fill_model import evaluate_conservative_fill
from quant_os.replay.prediction_market_replay_design import write_replay_design_report
from quant_os.replay.prediction_market_replay_inputs import normalize_replay_inputs

REPORT_ROOT = Path("reports/sequence31/shadow_execution")
SHADOW_EXECUTION_SAFETY = {
    "execution_authority": "NONE",
    "wallet_signing_enabled": False,
    "live_trading_enabled": False,
    "copy_trading_enabled": False,
    "real_orders_enabled": False,
    "prediction_market_execution_authority_added": False,
}


def write_shadow_execution_report(
    *,
    output_root: str | Path = ".",
    polymarket_snapshot_path: str | Path | None = None,
    pmxt_manifest_path: str | Path | None = None,
    reference_datasets_manifest_path: str | Path | None = None,
) -> dict[str, Any]:
    design = write_replay_design_report(
        output_root=output_root,
        polymarket_snapshot_path=polymarket_snapshot_path,
        pmxt_manifest_path=pmxt_manifest_path,
        reference_datasets_manifest_path=reference_datasets_manifest_path,
    )
    events = normalize_replay_inputs(
        polymarket_snapshot_path=polymarket_snapshot_path,
        pmxt_manifest_path=pmxt_manifest_path,
        reference_datasets_manifest_path=reference_datasets_manifest_path,
    )
    payload = evaluate_shadow_execution(design=design, replay_events=events)
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def evaluate_shadow_execution(*, design: dict[str, Any], replay_events: list[Any]) -> dict[str, Any]:
    orderbook_by_key = {
        (event.market_id, event.token_id): event
        for event in replay_events
        if event.event_type == "orderbook_snapshot"
    }
    replay_inputs_sufficient = design["replay_design_status"] == "READY_FOR_NARROW_REPLAY_DESIGN"
    intents = generate_shadow_order_intents(replay_design=design)
    intent_reports = []
    fill_reports = []
    risk_reports = []
    for intent in intents:
        risk = evaluate_shadow_risk(
            intent=intent,
            current_intent_count=0,
            current_market_exposure="0",
            replay_inputs_sufficient=replay_inputs_sufficient,
        )
        risk_reports.append(risk)
        fill = {"fill_status": "NO_FILL_CONSERVATIVE", "filled_size": "0"}
        if intent.status != "BLOCKED" and risk["risk_status"] != "RISK_BLOCKED":
            orderbook = orderbook_by_key.get((intent.market_id, intent.token_id))
            if orderbook is not None:
                fill = evaluate_conservative_fill(intent=intent, orderbook_event=orderbook)
        fill_reports.append(fill)
        intent_reports.append(intent.to_report_dict())
    metrics = _metrics(intent_reports, fill_reports)
    blockers = _blockers(
        design=design,
        intent_reports=intent_reports,
        risk_reports=risk_reports,
        metrics=metrics,
    )
    status = _status_from_blockers(blockers)
    return {
        "sequence": "31",
        "shadow_execution_status": status,
        "selected_lane_id": design["selected_lane_id"],
        "allowed_statuses": [
            "SHADOW_EXECUTION_NOT_JUSTIFIED",
            "REPLAY_DESIGN_PARTIAL",
            "FILL_MODEL_TOO_OPTIMISTIC",
            "INTENTS_TOO_THIN",
            "RISK_BLOCKS_SHADOW_AUTONOMY",
            "READY_FOR_BOUNDED_SHADOW_AUTONOMY",
        ],
        "blockers": blockers,
        "metrics": metrics,
        "intents": intent_reports,
        "risk_results": risk_reports,
        "fill_results": fill_reports,
        "observed_facts": [
            "Shadow decisions are produced from normalized replay inputs only.",
            "The sample has one visible orderbook snapshot and one trade.",
        ],
        "deterministic_assumptions": [
            "No live routing, signing, posting, cancellation, or wallet authority is available.",
            "Risk is evaluated before any offline fill model is considered.",
            "Blocked intents remain records, not executable orders.",
        ],
        "unknowns": [
            "Queue position, fill priority, hidden liquidity, and latency distribution remain unknown.",
            "No profitable edge signal has been established for this lane.",
        ],
        **SHADOW_EXECUTION_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _metrics(intent_reports: list[dict[str, Any]], fill_reports: list[dict[str, Any]]) -> dict[str, str | int]:
    intent_count = len(intent_reports)
    blocked_count = sum(1 for intent in intent_reports if intent["status"] == "BLOCKED")
    filled_count = sum(1 for fill in fill_reports if fill["fill_status"] != "NO_FILL_CONSERVATIVE")
    no_fill_count = len(fill_reports) - filled_count
    fill_rate = Decimal(filled_count) / Decimal(intent_count or 1)
    no_fill_rate = Decimal(no_fill_count) / Decimal(intent_count or 1)
    return {
        "intent_count": intent_count,
        "blocked_trade_count": blocked_count,
        "filled_count": filled_count,
        "no_fill_count": no_fill_count,
        "fill_rate": _render_decimal(fill_rate),
        "no_fill_rate": _render_decimal(no_fill_rate),
        "spread_cross_cost_burden": "unearned_due_to_blocked_intents",
        "latency_penalty_sensitivity": "blocks_shadow_autonomy_until_more_depth",
        "stale_book_penalty_sensitivity": "blocks_shadow_autonomy_until_more_depth",
        "expectancy_under_conservative_assumptions": "not_estimated_no_edge",
    }


def _blockers(
    *,
    design: dict[str, Any],
    intent_reports: list[dict[str, Any]],
    risk_reports: list[dict[str, Any]],
    metrics: dict[str, str | int],
) -> list[str]:
    blockers = []
    if design["replay_design_status"] != "READY_FOR_NARROW_REPLAY_DESIGN":
        blockers.append("REPLAY_DESIGN_PARTIAL")
    if metrics["intent_count"] < 10:
        blockers.append("INTENTS_TOO_THIN")
    if metrics["blocked_trade_count"] == metrics["intent_count"]:
        blockers.append("SHADOW_EXECUTION_NOT_JUSTIFIED")
    if any(risk["risk_status"] == "RISK_BLOCKED" for risk in risk_reports):
        blockers.append("RISK_BLOCKS_SHADOW_AUTONOMY")
    if any("CONFIDENCE_TOO_WEAK" in intent["blocking_reasons"] for intent in intent_reports):
        blockers.append("WEAK_SIGNAL_BLOCKS_SHADOW_AUTONOMY")
    return _dedupe(blockers)


def _status_from_blockers(blockers: list[str]) -> str:
    if "SHADOW_EXECUTION_NOT_JUSTIFIED" in blockers:
        return "SHADOW_EXECUTION_NOT_JUSTIFIED"
    if "RISK_BLOCKS_SHADOW_AUTONOMY" in blockers:
        return "RISK_BLOCKS_SHADOW_AUTONOMY"
    if "INTENTS_TOO_THIN" in blockers:
        return "INTENTS_TOO_THIN"
    if "REPLAY_DESIGN_PARTIAL" in blockers:
        return "REPLAY_DESIGN_PARTIAL"
    return "READY_FOR_BOUNDED_SHADOW_AUTONOMY"


def _render_decimal(value: Decimal) -> str:
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered or "0"


def _dedupe(items: list[str]) -> list[str]:
    seen = set()
    deduped = []
    for item in items:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_shadow_execution.json"
    md_path = root / "latest_shadow_execution.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 31 Shadow Execution",
        "",
        "Offline shadow execution evaluation. No execution authority.",
        "",
        f"Status: {payload['shadow_execution_status']}",
        f"Selected lane: {payload['selected_lane_id']}",
        f"Live promotion: {payload['live_promotion_status']}",
        "",
        "## Metrics",
    ]
    lines.extend(f"- {key}: {value}" for key, value in payload["metrics"].items())
    lines.extend(["", "## Blockers"])
    lines.extend(f"- {item}" for item in payload["blockers"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
