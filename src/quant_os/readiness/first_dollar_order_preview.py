from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.readiness.canary_readiness_common import (
    load_gate_payload,
    safety_payload,
    write_json_markdown_report,
)

REPORT_DIR = Path("reports/first_dollar_preflight/order_preview")


def build_first_dollar_order_preview(
    *,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    dry_run = load_gate_payload(
        "reports/canary_readiness/dry_run_parity/latest_dry_run_parity.json",
        output_root=output_root,
    ) or {}
    tiny = load_gate_payload(
        "reports/canary_readiness/final/latest_tiny_canary_readiness.json",
        output_root=output_root,
    ) or {}
    eligibility = load_gate_payload(
        "reports/first_dollar_preflight/current_market/latest_current_market_eligibility.json",
        output_root=output_root,
    ) or {}
    previews = dry_run.get("order_intent_previews", []) or []
    blockers = []
    if eligibility.get("status") != "CURRENT_MARKET_ELIGIBILITY_PASSED":
        blockers.append("CURRENT_MARKET_ELIGIBILITY_PASSED_MISSING")
    current_market = eligibility.get("market") or {}
    forecast_evidence = eligibility.get("forecast_evidence") or {}
    if tiny and tiny.get("status") != "TINY_CANARY_READY_FOR_MANUAL_ARMING":
        blockers.append("TINY_CANARY_READY_FOR_MANUAL_ARMING_MISSING")
    if not previews and not current_market:
        blockers.append("DRY_RUN_PREVIEW_MISSING")
    preview = previews[0] if previews else {}
    status = "NO_TRANSMIT_ORDER_PREVIEW_READY" if not blockers else "NO_TRANSMIT_ORDER_PREVIEW_BLOCKED"
    market_ticker = current_market.get("ticker") or preview.get("market_ticker")
    side = "yes" if current_market else preview.get("side")
    action = "buy" if current_market else preview.get("action")
    limit_price = current_market.get("yes_ask") or preview.get("limit_price")
    market_hash = eligibility.get("market_evidence_hash") or current_market.get("market_evidence_hash")
    forecast_hash = eligibility.get("forecast_evidence_hash") or forecast_evidence.get("evidence_hash")
    payload = safety_payload(
        schema_version="first_dollar_order_preview_v1",
        status=status,
        allowed_statuses=[
            "NO_TRANSMIT_ORDER_PREVIEW_READY",
            "NO_TRANSMIT_ORDER_PREVIEW_BLOCKED",
        ],
        candidate_id="pm_weather_forecast_market_mismatch",
        market_ticker=market_ticker,
        side=side,
        action=action,
        limit_price=limit_price,
        max_contracts=preview.get("max_contracts", 1),
        max_nominal_exposure=preview.get("max_nominal_exposure", 1.0),
        max_total_loss=1.0,
        forecast_evidence_hash=forecast_hash,
        market_evidence_hash=market_hash,
        reason_code=preview.get("reason_code") or "CURRENT_FORECAST_BUCKET_MISMATCH_EDGE",
        client_order_id_preview=preview.get("client_order_id_preview")
        or f"preview_{str(market_ticker or 'no_market').lower()}_dry_run_only",
        dry_run_only=True,
        no_send=True,
        contains_signed_headers=False,
        contains_private_key_path=False,
        contains_executable_submission_code=False,
        api_keys_loaded=False,
        private_keys_loaded=False,
        authenticated_requests_enabled=False,
        order_transmission_enabled=False,
        blockers=blockers,
        next_action="Prepare human review checklist."
        if not blockers
        else "Regenerate dry-run parity before preview.",
    )
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_order_preview.json",
        md_name="latest_order_preview.md",
        title="First-Dollar No-Transmit Order Preview",
        summary="Unsigned dry-run-only order-intent preview. This report cannot submit an order.",
    )
    return payload


def write_first_dollar_order_preview_report(
    *,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    return build_first_dollar_order_preview(output_root=output_root)
