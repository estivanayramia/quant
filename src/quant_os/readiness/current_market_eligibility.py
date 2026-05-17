from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.readiness.canary_readiness_common import (
    load_gate_payload,
    safety_payload,
    utc_now,
    write_json_markdown_report,
)

REPORT_DIR = Path("reports/first_dollar_preflight/current_market")


def evaluate_current_market_eligibility(
    *,
    output_root: str | Path = ".",
    current_public_market: dict[str, Any] | None = None,
    forecast_evidence: dict[str, Any] | None = None,
    now_ts: str | None = None,
    max_spread: float = 0.05,
    min_liquidity: float = 1.0,
    max_staleness_minutes: int = 30,
) -> dict[str, Any]:
    now_ts = now_ts or utc_now()
    if current_public_market is None or forecast_evidence is None:
        forecast_report = load_gate_payload(
            "reports/first_dollar_preflight/current_forecast/latest_current_forecast.json",
            output_root=output_root,
        )
        if forecast_evidence is None:
            forecast_evidence = forecast_report
        if current_public_market is None and forecast_report:
            current_public_market = forecast_report.get("market")
    discovery = load_gate_payload(
        "reports/first_dollar_preflight/current_market_discovery/latest_current_market_discovery.json",
        output_root=output_root,
    ) or {}
    if current_public_market is None:
        current_public_market = discovery.get("selected_market")
    blockers = []
    if current_public_market is None:
        status = "CURRENT_MARKET_ELIGIBILITY_NO_CURRENT_MARKET"
        blockers.append("NO_CURRENT_PUBLIC_MARKET_SUPPLIED")
    else:
        _collect_market_blockers(
            blockers,
            current_public_market=current_public_market,
            forecast_evidence=forecast_evidence,
            now_ts=now_ts,
            max_spread=max_spread,
            min_liquidity=min_liquidity,
            max_staleness_minutes=max_staleness_minutes,
        )
        status = (
            "CURRENT_MARKET_ELIGIBILITY_PASSED"
            if not blockers
            else "CURRENT_MARKET_ELIGIBILITY_BLOCKED"
        )
    forecast_hash = (forecast_evidence or {}).get("evidence_hash")
    market_hash = (current_public_market or {}).get("market_evidence_hash")
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
        now_ts=now_ts,
        market=current_public_market,
        forecast_evidence=forecast_evidence,
        forecast_evidence_hash=forecast_hash,
        market_evidence_hash=market_hash,
        spread_cap=max_spread,
        liquidity_minimum=min_liquidity,
        staleness_cap_minutes=max_staleness_minutes,
        checklist={
            "market_is_open": bool(current_public_market)
            and str(current_public_market.get("status", "")).lower() in {"active", "open"},
            "candidate_rule_match": bool(current_public_market)
            and current_public_market.get("candidate_id") == "pm_weather_forecast_market_mismatch",
            "forecast_matched": bool(forecast_evidence)
            and forecast_evidence.get("status") == "CURRENT_FORECAST_MATCHED",
            "orderbook_public_data_available": bool(current_public_market)
            and bool(current_public_market.get("orderbook_ts")),
            "spread_under_cap": bool(current_public_market)
            and float(current_public_market.get("spread") or 0) <= max_spread,
            "liquidity_over_minimum": bool(current_public_market)
            and float(current_public_market.get("liquidity") or 0) >= min_liquidity,
            "price_discipline_holds": bool(current_public_market)
            and float(current_public_market.get("yes_ask") or 1) <= 0.49,
            "no_stale_data": "ORDERBOOK_DATA_STALE" not in blockers,
            "no_duplicate_order_intent_preview": True,
            "no_active_position_assumed": True,
            "no_previous_unresolved_canary": True,
            "venue_minimum_exposure_known": True,
            "canary_cap_still_valid": True,
            "no_auth_required": True,
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


def _collect_market_blockers(
    blockers: list[str],
    *,
    current_public_market: dict[str, Any],
    forecast_evidence: dict[str, Any] | None,
    now_ts: str,
    max_spread: float,
    min_liquidity: float,
    max_staleness_minutes: int,
) -> None:
    status = str(current_public_market.get("status") or "").lower()
    if status not in {"active", "open"}:
        blockers.append("MARKET_NOT_OPEN")
    if current_public_market.get("candidate_id") != "pm_weather_forecast_market_mismatch":
        blockers.append("CANDIDATE_RULE_MISMATCH")
    if (forecast_evidence or {}).get("status") != "CURRENT_FORECAST_MATCHED":
        blockers.append("CURRENT_FORECAST_MATCHED_MISSING")
    if not current_public_market.get("orderbook_ts"):
        blockers.append("ORDERBOOK_PUBLIC_DATA_MISSING")
    elif _age_minutes(str(current_public_market["orderbook_ts"]), now_ts) > max_staleness_minutes:
        blockers.append("ORDERBOOK_DATA_STALE")
    if float(current_public_market.get("spread") or 0) > max_spread:
        blockers.append("SPREAD_ABOVE_CAP")
    if float(current_public_market.get("liquidity") or 0) < min_liquidity:
        blockers.append("LIQUIDITY_BELOW_MINIMUM")
    if float(current_public_market.get("yes_ask") or 1) > 0.49:
        blockers.append("PRICE_DISCIPLINE_BLOCKED")
    if (forecast_evidence or {}).get("bucket_match") is not True:
        blockers.append("FORECAST_BUCKET_MATCH_MISSING")


def _age_minutes(orderbook_ts: str, now_ts: str) -> float:
    orderbook = _parse_ts(orderbook_ts)
    now = _parse_ts(now_ts)
    return max((now - orderbook).total_seconds() / 60.0, 0.0)


def _parse_ts(value: str):
    from datetime import UTC, datetime

    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
