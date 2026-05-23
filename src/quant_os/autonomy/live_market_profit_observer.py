from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.autonomy.live_market_sim_common import (
    hash_payload,
    load_state,
    sim_safety_payload,
    write_state,
)
from quant_os.data.weather.current_weather_forecast_match import write_current_forecast_match_report
from quant_os.data.weather.current_weather_market_discovery import (
    write_current_weather_market_discovery_report,
)
from quant_os.readiness.canary_readiness_common import (
    load_gate_payload,
    utc_now,
    write_json_markdown_report,
)
from quant_os.readiness.current_market_eligibility import write_current_market_eligibility_report
from quant_os.readiness.first_dollar_preflight import write_first_dollar_preflight_report

REPORT_DIR = Path("reports/live_market_sim_profitability/observer")


def build_live_market_profit_observer(
    *,
    output_root: str | Path = ".",
    now_ts: str | None = None,
    current_market_payload: dict[str, Any] | None = None,
    preflight_payload: dict[str, Any] | None = None,
    public_network_ok: bool = False,
) -> dict[str, Any]:
    now_ts = now_ts or utc_now()
    if public_network_ok and current_market_payload is None:
        excluded_market_tickers = _existing_exposure_tickers(output_root=output_root)
        write_current_weather_market_discovery_report(
            output_root=output_root,
            public_network_ok=True,
            excluded_market_tickers=excluded_market_tickers,
        )
        write_current_forecast_match_report(output_root=output_root, public_network_ok=True)
        current_market_payload = write_current_market_eligibility_report(output_root=output_root)
        preflight_payload = write_first_dollar_preflight_report(output_root=output_root)
    current_market_payload = current_market_payload or load_gate_payload(
        "reports/first_dollar_preflight/current_market/latest_current_market_eligibility.json",
        output_root=output_root,
    ) or {}
    preflight_payload = preflight_payload or load_gate_payload(
        "reports/first_dollar_preflight/final/latest_first_dollar_preflight.json",
        output_root=output_root,
    ) or {}
    market = current_market_payload.get("market")
    forecast = current_market_payload.get("forecast_evidence") or {}
    blockers = list(current_market_payload.get("blockers", []) or [])
    eligible = current_market_payload.get("status") == "CURRENT_MARKET_ELIGIBILITY_PASSED"
    if eligible:
        status = "LIVE_PROFIT_OBSERVER_READY"
        observation_kind = "ELIGIBLE_LIVE_MARKET"
    elif current_market_payload.get("status") == "CURRENT_MARKET_ELIGIBILITY_NO_CURRENT_MARKET":
        status = "LIVE_PROFIT_OBSERVER_NO_ELIGIBLE_MARKET"
        observation_kind = "NO_CURRENT_MARKET"
        blockers = []
    elif current_market_payload.get("status") == "CURRENT_MARKET_ELIGIBILITY_BLOCKED":
        status = "LIVE_PROFIT_OBSERVER_BLOCKED"
        observation_kind = _blocked_kind(blockers)
    else:
        status = "LIVE_PROFIT_OBSERVER_BLOCKED"
        observation_kind = "MISSING_PUBLIC_MARKET_STATE"
        blockers = blockers or ["CURRENT_MARKET_STATE_MISSING"]
    orderbook_snapshot = {
        "ticker": (market or {}).get("ticker"),
        "yes_bid": (market or {}).get("yes_bid"),
        "yes_ask": (market or {}).get("yes_ask"),
        "no_bid": (market or {}).get("no_bid"),
        "no_ask": (market or {}).get("no_ask"),
        "spread": (market or {}).get("spread"),
        "liquidity": (market or {}).get("liquidity"),
        "orderbook_ts": (market or {}).get("orderbook_ts"),
    }
    observation = {
        "observation_id": _observation_id(now_ts, current_market_payload, orderbook_snapshot),
        "observed_at": now_ts,
        "data_ts": (market or {}).get("orderbook_ts") or forecast.get("known_at_ts") or now_ts,
        "observation_kind": observation_kind,
        "eligible": eligible,
        "eligible_market": eligible,
        "current_market_status": current_market_payload.get("status"),
        "preflight_status": preflight_payload.get("status"),
        "market": market,
        "market_ticker": (market or {}).get("ticker"),
        "market_series": (market or {}).get("series_ticker"),
        "orderbook_snapshot": orderbook_snapshot,
        "forecast_evidence": forecast,
        "market_evidence_hash": current_market_payload.get("market_evidence_hash")
        or (market or {}).get("market_evidence_hash"),
        "forecast_evidence_hash": current_market_payload.get("forecast_evidence_hash")
        or forecast.get("evidence_hash"),
        "resolution_ts": (market or {}).get("resolution_ts"),
        "public_resolution_label": (market or {}).get("public_resolution_label"),
        "blockers": blockers,
    }
    next_action = (
        "Generate fake-money no-transmit live simulated intent."
        if eligible
        else "Continue data-only public observation loop."
    )
    return sim_safety_payload(
        schema_version="live_market_profit_observer_v1",
        status=status,
        allowed_statuses=[
            "LIVE_PROFIT_OBSERVER_READY",
            "LIVE_PROFIT_OBSERVER_NO_ELIGIBLE_MARKET",
            "LIVE_PROFIT_OBSERVER_PENDING_OUTCOME",
            "LIVE_PROFIT_OBSERVER_RESOLVED_OUTCOME",
            "LIVE_PROFIT_OBSERVER_BLOCKED",
        ],
        public_read_only=True,
        public_network_used=public_network_ok,
        request_methods=["GET"],
        observation=observation,
        observation_id=observation["observation_id"],
        market=market,
        forecast_evidence=forecast,
        blockers=blockers,
        next_action=next_action,
    )


def write_live_market_profit_observer_report(
    *,
    output_root: str | Path = ".",
    now_ts: str | None = None,
    current_market_payload: dict[str, Any] | None = None,
    preflight_payload: dict[str, Any] | None = None,
    public_network_ok: bool = False,
) -> dict[str, Any]:
    payload = build_live_market_profit_observer(
        output_root=output_root,
        now_ts=now_ts,
        current_market_payload=current_market_payload,
        preflight_payload=preflight_payload,
        public_network_ok=public_network_ok,
    )
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_observer.json",
        md_name="latest_observer.md",
        title="Live Market Sim Profit Observer",
        summary="Public read-only live-market observation for fake-money profitability simulation.",
    )
    write_state(
        output_root=output_root,
        observations=[payload["observation"]],
        current_blockers=payload.get("blockers", []),
        next_action=payload["next_action"],
    )
    return payload


def _observation_id(now_ts: str, payload: dict[str, Any], book: dict[str, Any]) -> str:
    return f"lmso_{hash_payload({'now_ts': now_ts, 'status': payload.get('status'), 'book': book})}"


def _blocked_kind(blockers: list[str]) -> str:
    if "ORDERBOOK_DATA_STALE" in blockers:
        return "STALE"
    if "CURRENT_FORECAST_MATCHED_MISSING" in blockers:
        return "MISSING_FORECAST"
    if "SPREAD_ABOVE_CAP" in blockers:
        return "SPREAD_TOO_WIDE"
    if "LIQUIDITY_BELOW_MINIMUM" in blockers:
        return "LIQUIDITY_TOO_THIN"
    if "PRICE_DISCIPLINE_BLOCKED" in blockers:
        return "PRICE_DISCIPLINE_BLOCKED"
    return "CLOSED_OR_BLOCKED"


def _existing_exposure_tickers(*, output_root: str | Path) -> list[str]:
    state = load_state(output_root=output_root)
    tickers = set()
    for collection_name in ("intents", "fills", "ledger_entries", "outcomes"):
        for item in state.get(collection_name, []) or []:
            ticker = item.get("market_ticker")
            if ticker:
                tickers.add(str(ticker))
    return sorted(tickers)
