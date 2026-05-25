from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.readiness.canary_readiness_common import safety_payload, write_json_markdown_report

REPORT_DIR = Path("reports/autonomous_live_fire_drill/risk")


def evaluate_fire_drill_risk(
    *,
    fake_orders: list[dict[str, Any]] | None = None,
    live_trading_enabled: bool = False,
    order_transmission_enabled: bool = False,
    authenticated_requests_enabled: bool = False,
    max_fake_orders: int = 1,
    max_fake_contracts: int = 1,
    max_fake_notional: float = 1.0,
    max_fake_loss: float = 1.0,
) -> dict[str, Any]:
    fake_orders = fake_orders or []
    blockers: list[str] = []
    if len(fake_orders) > max_fake_orders:
        blockers.append("ONE_SHOT_LIMIT_EXCEEDED")
    client_ids = [order.get("client_order_id_preview") for order in fake_orders]
    if len(client_ids) != len(set(client_ids)):
        blockers.append("DUPLICATE_CLIENT_ORDER_ID")
    total_contracts = sum(int(order.get("max_contracts") or 0) for order in fake_orders)
    total_notional = sum(float(order.get("max_nominal_exposure") or 0.0) for order in fake_orders)
    total_loss = sum(float(order.get("max_total_loss") or 0.0) for order in fake_orders)
    if total_contracts > max_fake_contracts:
        blockers.append("MAX_FAKE_CONTRACTS_EXCEEDED")
    if total_notional > max_fake_notional:
        blockers.append("MAX_FAKE_NOTIONAL_EXCEEDED")
    if total_loss > max_fake_loss:
        blockers.append("MAX_FAKE_LOSS_EXCEEDED")
    if live_trading_enabled:
        blockers.append("LIVE_TRADING_FLAG_TRUE")
    if order_transmission_enabled:
        blockers.append("ORDER_TRANSMISSION_FLAG_TRUE")
    if authenticated_requests_enabled:
        blockers.append("AUTHENTICATED_REQUESTS_FLAG_TRUE")
    return safety_payload(
        schema_version="autonomous_fire_drill_risk_v1",
        status="FIRE_DRILL_RISK_BLOCKED" if blockers else "FIRE_DRILL_RISK_PASSED",
        allowed_statuses=["FIRE_DRILL_RISK_PASSED", "FIRE_DRILL_RISK_BLOCKED"],
        max_fake_orders=max_fake_orders,
        max_fake_contracts=max_fake_contracts,
        max_fake_notional=max_fake_notional,
        max_fake_loss=max_fake_loss,
        total_fake_orders=len(fake_orders),
        total_fake_contracts=total_contracts,
        total_fake_notional=total_notional,
        total_fake_loss=total_loss,
        no_retry_loop=True,
        no_averaging_down=True,
        one_shot_limit_enforced=True,
        blockers=blockers,
        request_signing_enabled=False,
        api_keys_loaded=False,
        private_keys_loaded=False,
        next_action="Run kill switch proof." if not blockers else "Self-disable until risk blockers clear.",
    )


def write_fire_drill_risk_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    from quant_os.risk.autonomous_fire_drill_kill_switch import evaluate_fire_drill_kill_switch

    risk = evaluate_fire_drill_risk(fake_orders=[])
    kill = evaluate_fire_drill_kill_switch()
    payload = {**risk, "kill_switch_status": kill["status"], "kill_switch": kill}
    if kill["status"] != "FIRE_DRILL_KILL_SWITCH_PASSED":
        payload["status"] = "FIRE_DRILL_RISK_BLOCKED"
        payload["blockers"] = list(dict.fromkeys([*payload["blockers"], *kill["blockers"]]))
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_risk.json",
        md_name="latest_risk.md",
        title="Autonomous Fire-Drill Risk",
        summary="Fake-money risk and kill-switch gates. Live flags must remain false.",
    )
    return payload
