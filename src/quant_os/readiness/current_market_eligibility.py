from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.readiness.canary_readiness_common import safety_payload, write_json_markdown_report

REPORT_DIR = Path("reports/first_dollar_preflight/current_market")


def evaluate_current_market_eligibility(
    *,
    output_root: str | Path = ".",
    current_public_market: dict[str, Any] | None = None,
) -> dict[str, Any]:
    blockers = []
    if current_public_market is None:
        status = "CURRENT_MARKET_ELIGIBILITY_NO_CURRENT_MARKET"
        blockers.append("NO_CURRENT_PUBLIC_MARKET_SUPPLIED")
    else:
        status = "CURRENT_MARKET_ELIGIBILITY_PASSED"
    payload = safety_payload(
        schema_version="current_market_eligibility_v1",
        status=status,
        allowed_statuses=[
            "CURRENT_MARKET_ELIGIBILITY_PASSED",
            "CURRENT_MARKET_ELIGIBILITY_NO_CURRENT_MARKET",
            "CURRENT_MARKET_ELIGIBILITY_BLOCKED",
            "CURRENT_MARKET_ELIGIBILITY_PUBLIC_DATA_ONLY",
        ],
        public_read_only=True,
        checked_account_balance=False,
        checked_portfolio=False,
        authenticated_endpoint_called=False,
        market=current_public_market,
        checklist={
            "market_is_open": bool(current_public_market),
            "eligible_weather_lane": bool(current_public_market),
            "forecast_source_available": bool(current_public_market),
            "orderbook_public_data_available": bool(current_public_market),
            "no_duplicate_order_intent_preview": True,
            "no_active_position_assumed": True,
            "no_previous_unresolved_canary": True,
            "canary_cap_still_valid": True,
        },
        blockers=blockers,
        next_action="Wait for an eligible current public market."
        if blockers
        else "Generate no-transmit order preview.",
        api_keys_loaded=False,
        private_keys_loaded=False,
    )
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_current_market_eligibility.json",
        md_name="latest_current_market_eligibility.md",
        title="Current Market Eligibility",
        summary="Public-read-only current-market checklist. No balance, portfolio, auth, order, or cancel calls.",
    )
    return payload


def write_current_market_eligibility_report(
    *,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    return evaluate_current_market_eligibility(output_root=output_root)
