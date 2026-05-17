from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.readiness.canary_readiness_common import (
    load_gate_payload,
    safety_payload,
    write_json_markdown_report,
)

REPORT_DIR = Path("reports/autonomous_live_fire_drill/decision")


def build_autonomous_decision_engine(
    *,
    output_root: str | Path = ".",
    watcher_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    watcher_payload = watcher_payload or load_gate_payload(
        "reports/autonomous_live_fire_drill/watcher/latest_watcher.json",
        output_root=output_root,
    ) or {}
    blockers = list(watcher_payload.get("blockers", []) or [])
    market = watcher_payload.get("market") or {}
    forecast = watcher_payload.get("forecast_evidence") or {}
    if watcher_payload.get("status") != "AUTONOMOUS_WATCHER_READY":
        status = "AUTONOMOUS_DECISION_NO_TRADE"
        decision = "NO_TRADE"
    elif not watcher_payload.get("market_evidence_hash") or not watcher_payload.get("forecast_evidence_hash"):
        status = "AUTONOMOUS_DECISION_BLOCKED"
        decision = "BLOCKED"
        blockers.append("MISSING_EVIDENCE_HASH")
    elif float(market.get("spread") or 0.0) > 0.05:
        status = "AUTONOMOUS_DECISION_NO_TRADE"
        decision = "NO_TRADE"
        blockers.append("SPREAD_TOO_WIDE")
    elif float(market.get("liquidity") or 0.0) < 5.0:
        status = "AUTONOMOUS_DECISION_NO_TRADE"
        decision = "NO_TRADE"
        blockers.append("LIQUIDITY_TOO_THIN")
    elif not forecast.get("bucket_match", True):
        status = "AUTONOMOUS_DECISION_NO_TRADE"
        decision = "NO_TRADE"
        blockers.append("PRICE_DISCIPLINE_BLOCKED")
    else:
        status = "AUTONOMOUS_DECISION_READY"
        decision = "PAPER_ORDER_INTENT"
    return safety_payload(
        schema_version="autonomous_decision_engine_v1",
        status=status,
        allowed_statuses=[
            "AUTONOMOUS_DECISION_READY",
            "AUTONOMOUS_DECISION_NO_TRADE",
            "AUTONOMOUS_DECISION_BLOCKED",
        ],
        decision=decision,
        candidate_id=market.get("candidate_id") or "pm_weather_forecast_market_mismatch",
        market_ticker=market.get("ticker"),
        side="yes",
        action="buy",
        limit_price=float(market.get("yes_ask") or 0.0),
        max_contracts=1,
        max_nominal_exposure=1.0,
        max_total_loss=1.0,
        reason_code="ELIGIBLE_FIRE_DRILL_MARKET" if decision == "PAPER_ORDER_INTENT" else "NO_TRADE_GATE",
        forecast_evidence_hash=watcher_payload.get("forecast_evidence_hash"),
        market_evidence_hash=watcher_payload.get("market_evidence_hash"),
        client_order_id_preview=f"fd_{str(market.get('ticker') or 'no_market').lower().replace('-', '_')[:24]}",
        no_lookahead_enforced=True,
        one_shot_canary_rule_enforced=True,
        blockers=list(dict.fromkeys(blockers)),
        request_signing_enabled=False,
        api_keys_loaded=False,
        private_keys_loaded=False,
        next_action="Build no-transmit fake-money intent."
        if decision == "PAPER_ORDER_INTENT"
        else "Record no-trade and continue monitoring.",
    )


def write_autonomous_decision_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_autonomous_decision_engine(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_decision.json",
        md_name="latest_decision.md",
        title="Autonomous Live Fire-Drill Decision",
        summary="Deterministic fake-money decision. This stage cannot route, sign, or submit orders.",
    )
    return payload
