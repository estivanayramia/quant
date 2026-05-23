from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quant_os.readiness.canary_readiness_common import (
    load_gate_payload,
    safety_payload,
    utc_now,
    write_json_markdown_report,
)

REPORT_DIR = Path("reports/first_dollar_preflight/current_forecast")
NWS_HOURLY_URLS_BY_LOCATION = {
    "Central Park, New York": "https://api.weather.gov/gridpoints/OKX/34,45/forecast/hourly",
    "Austin, Texas": "https://api.weather.gov/gridpoints/EWX/156,91/forecast/hourly",
    "Chicago, Illinois": "https://api.weather.gov/gridpoints/LOT/76,73/forecast/hourly",
    "Miami, Florida": "https://api.weather.gov/gridpoints/MFL/110,50/forecast/hourly",
    "Los Angeles, California": "https://api.weather.gov/gridpoints/LOX/155,45/forecast/hourly",
}
NWS_NYC_HOURLY_URL = NWS_HOURLY_URLS_BY_LOCATION["Central Park, New York"]


def evaluate_current_forecast_match(
    *,
    output_root: str | Path = ".",
    market: dict[str, Any] | None = None,
    forecast_payload: dict[str, Any] | None = None,
    forecast_payloads_by_location: dict[str, dict[str, Any]] | None = None,
    known_at_ts: str | None = None,
    orderbook_ts: str | None = None,
    public_network_ok: bool = False,
) -> dict[str, Any]:
    blockers: list[str] = []
    if market is None:
        discovery = load_gate_payload(
            "reports/first_dollar_preflight/current_market_discovery/latest_current_market_discovery.json",
            output_root=output_root,
        ) or {}
        candidates = list(discovery.get("candidates", []) or [])
    else:
        candidates = [market]
    if not candidates:
        blockers.append("NO_CURRENT_PUBLIC_MARKET_SUPPLIED")
    forecast_payloads_by_location = dict(forecast_payloads_by_location or {})
    if public_network_ok and forecast_payload is None:
        forecast_payloads_by_location.update(
            _fetch_forecasts_by_location(candidate.get("location") for candidate in candidates)
        )
    if forecast_payload is None and not forecast_payloads_by_location:
        blockers.append("CURRENT_FORECAST_SOURCE_MISSING")
    matches = []
    for candidate in candidates:
        candidate_forecast = forecast_payload or forecast_payloads_by_location.get(
            str(candidate.get("location") or "")
        )
        result = _match_one(
            candidate,
            forecast_payload=candidate_forecast or {},
            known_at_ts=known_at_ts,
            orderbook_ts=orderbook_ts,
        )
        if result["bucket_match"]:
            matches.append(result)
    matches.sort(key=_match_sort_key)
    selected = matches[0] if matches else None
    if selected:
        status = "CURRENT_FORECAST_MATCHED"
        blockers = []
    elif any("LOOKAHEAD" in item for item in blockers):
        status = "LOOKAHEAD_RISK_BLOCKED"
    elif blockers and not matches:
        status = "CURRENT_FORECAST_BLOCKED"
    else:
        status = "FORECAST_MAPPING_AMBIGUOUS"
        blockers = ["NO_FORECAST_BUCKET_MATCH"]
    if selected is None and candidates and (forecast_payload or forecast_payloads_by_location):
        fallback_forecast = forecast_payload or forecast_payloads_by_location.get(
            str(candidates[0].get("location") or "")
        )
        selected = _match_one(
            candidates[0],
            forecast_payload=fallback_forecast or {},
            known_at_ts=known_at_ts,
            orderbook_ts=orderbook_ts,
        )
        blockers.extend(selected.get("blockers", []))
        if selected.get("lookahead_blocked"):
            status = "LOOKAHEAD_RISK_BLOCKED"
        elif selected.get("source_kind") == "realized_observation":
            status = "CURRENT_FORECAST_BLOCKED"
    payload = safety_payload(
        schema_version="current_weather_forecast_match_v1",
        status=status,
        allowed_statuses=[
            "CURRENT_FORECAST_MATCHED",
            "CURRENT_FORECAST_BLOCKED",
            "FORECAST_MAPPING_AMBIGUOUS",
            "LOOKAHEAD_RISK_BLOCKED",
        ],
        candidate_id="pm_weather_forecast_market_mismatch",
        market=selected.get("market") if selected else None,
        source_id=(selected or {}).get("source_id", "nws_api"),
        source_url=(selected or {}).get("source_url", NWS_NYC_HOURLY_URL),
        source_kind=(selected or {}).get("source_kind"),
        forecast_issue_ts=(selected or {}).get("forecast_issue_ts"),
        forecast_valid_ts=(selected or {}).get("forecast_valid_ts"),
        known_at_ts=(selected or {}).get("known_at_ts"),
        orderbook_ts=(selected or {}).get("orderbook_ts"),
        resolution_ts=(selected or {}).get("resolution_ts"),
        forecast_value=(selected or {}).get("forecast_value"),
        forecast_bucket=(selected or {}).get("forecast_bucket"),
        bucket_match=(selected or {}).get("bucket_match", False),
        match_count=len(matches),
        matched_locations=sorted({str(item.get("market", {}).get("location") or "") for item in matches}),
        evidence_hash=(selected or {}).get("evidence_hash"),
        public_read_only=True,
        realized_weather_used_as_forecast=False,
        authenticated_endpoint_called=False,
        blockers=list(dict.fromkeys(blockers)),
        api_keys_loaded=False,
        private_keys_loaded=False,
        next_action="Run current-market eligibility."
        if status == "CURRENT_FORECAST_MATCHED"
        else "Wait for a forecast source that maps cleanly without lookahead.",
    )
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_current_forecast.json",
        md_name="latest_current_forecast.md",
        title="Current Weather Forecast Match",
        summary="Public forecast-to-market mapping with no-lookahead checks. Realized weather is blocked as a signal.",
    )
    return payload


def write_current_forecast_match_report(
    *,
    output_root: str | Path = ".",
    public_network_ok: bool = False,
) -> dict[str, Any]:
    return evaluate_current_forecast_match(
        output_root=output_root,
        public_network_ok=public_network_ok,
    )


def _match_one(
    market: dict[str, Any],
    *,
    forecast_payload: dict[str, Any],
    known_at_ts: str | None,
    orderbook_ts: str | None,
) -> dict[str, Any]:
    normalized = _normalize_forecast_payload(market, forecast_payload)
    blockers = list(normalized.pop("blockers"))
    if _forecast_url_for_location(str(market.get("location") or "")) is None:
        blockers.append("FORECAST_SOURCE_LOCATION_UNSUPPORTED")
    forecast_ts = normalized.get("forecast_issue_ts")
    known_at = known_at_ts or normalized.get("known_at_ts") or forecast_ts
    orderbook = orderbook_ts or market.get("orderbook_ts") or utc_now()
    resolution = market.get("resolution_ts") or normalized.get("resolution_ts")
    if normalized.get("source_kind") == "realized_observation":
        blockers.append("REALIZED_WEATHER_FORBIDDEN_AS_FORECAST")
    lookahead_blocked = False
    if forecast_ts and known_at and orderbook and _parse_ts(known_at) > _parse_ts(orderbook):
        blockers.append("FORECAST_KNOWN_AFTER_ORDERBOOK")
        lookahead_blocked = True
    if forecast_ts and known_at and _parse_ts(forecast_ts) > _parse_ts(known_at):
        blockers.append("FORECAST_ISSUED_AFTER_KNOWN_AT")
        lookahead_blocked = True
    if resolution and orderbook and _parse_ts(orderbook) >= _parse_ts(resolution):
        blockers.append("ORDERBOOK_NOT_BEFORE_RESOLUTION")
        lookahead_blocked = True
    forecast_bucket = _bucket_for_value(market, normalized.get("forecast_value"))
    bucket_match = (
        not blockers
        and forecast_bucket is not None
        and forecast_bucket == market.get("threshold_bucket")
    )
    evidence_hash = _hash_json({"market": market, "forecast": forecast_payload})
    return {
        **normalized,
        "market": market,
        "known_at_ts": known_at,
        "orderbook_ts": orderbook,
        "resolution_ts": resolution,
        "forecast_bucket": forecast_bucket,
        "bucket_match": bucket_match,
        "lookahead_blocked": lookahead_blocked,
        "blockers": blockers,
        "evidence_hash": evidence_hash,
    }


def _normalize_forecast_payload(
    market: dict[str, Any],
    forecast_payload: dict[str, Any],
) -> dict[str, Any]:
    source_url = _forecast_url_for_location(str(market.get("location") or "")) or NWS_NYC_HOURLY_URL
    if not forecast_payload:
        return {
            "source_id": "nws_api",
            "source_url": source_url,
            "source_kind": "forecast",
            "forecast_issue_ts": "",
            "forecast_valid_ts": None,
            "known_at_ts": "",
            "forecast_value": None,
            "resolution_ts": market.get("resolution_ts"),
            "blockers": ["CURRENT_FORECAST_SOURCE_MISSING"],
        }
    if "forecast_value" in forecast_payload:
        return {
            "source_id": str(forecast_payload.get("source_id") or "nws_api"),
            "source_url": str(forecast_payload.get("source_url") or source_url),
            "source_kind": str(forecast_payload.get("source_kind") or "forecast"),
            "forecast_issue_ts": _normalize_ts(str(forecast_payload.get("forecast_issue_ts"))),
            "forecast_valid_ts": forecast_payload.get("forecast_valid_ts"),
            "known_at_ts": _normalize_ts(
                str(forecast_payload.get("known_at_ts") or forecast_payload.get("forecast_issue_ts"))
            ),
            "forecast_value": forecast_payload.get("forecast_value"),
            "resolution_ts": forecast_payload.get("resolution_ts") or market.get("resolution_ts"),
            "blockers": [],
        }
    props = forecast_payload.get("properties", {})
    periods = list(props.get("periods", []) or [])
    target_date = _date_from_ticker(str(market.get("ticker") or ""))
    matching = [
        period
        for period in periods
        if target_date and str(period.get("startTime") or "").startswith(str(target_date))
    ]
    if not matching:
        return {
            "source_id": "nws_api",
            "source_url": source_url,
            "source_kind": "forecast",
            "forecast_issue_ts": _normalize_ts(str(props.get("generatedAt") or props.get("updateTime"))),
            "forecast_valid_ts": None,
            "known_at_ts": _normalize_ts(str(props.get("generatedAt") or props.get("updateTime"))),
            "forecast_value": None,
            "resolution_ts": market.get("resolution_ts"),
            "blockers": ["FORECAST_VALID_PERIOD_MISSING"],
        }
    peak = max(matching, key=lambda period: _float(period.get("temperature")))
    issue = _normalize_ts(str(props.get("generatedAt") or props.get("updateTime")))
    return {
        "source_id": "nws_api",
        "source_url": source_url,
        "source_kind": "forecast",
        "forecast_issue_ts": issue,
        "forecast_valid_ts": peak.get("startTime"),
        "known_at_ts": issue,
        "forecast_value": _float(peak.get("temperature")),
        "resolution_ts": market.get("resolution_ts"),
        "blockers": [],
    }


def _bucket_for_value(market: dict[str, Any], value: Any) -> str | None:
    if value is None:
        return None
    number = float(value)
    strike_type = str(market.get("strike_type") or "").lower()
    floor = market.get("floor_strike")
    cap = market.get("cap_strike")
    if (
        strike_type == "between"
        and floor is not None
        and cap is not None
        and float(floor) <= number <= float(cap)
    ):
        return f"{_clean_number(floor)}_to_{_clean_number(cap)}_f_inclusive"
    if strike_type == "greater" and floor is not None and number > float(floor):
        return f"greater_than_{_clean_number(floor)}_f"
    if strike_type == "less" and cap is not None and number < float(cap):
        return f"less_than_{_clean_number(cap)}_f"
    return "outside_market_bucket"


def _fetch_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "quant-os-current-weather-readonly estivanayramia@example.com"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _fetch_forecasts_by_location(locations: Any) -> dict[str, dict[str, Any]]:
    forecasts: dict[str, dict[str, Any]] = {}
    for location in sorted({str(item or "") for item in locations}):
        url = _forecast_url_for_location(location)
        if not url:
            continue
        try:
            forecasts[location] = _fetch_json(url)
        except OSError:
            continue
    return forecasts


def _forecast_url_for_location(location: str) -> str | None:
    return NWS_HOURLY_URLS_BY_LOCATION.get(location)


def _match_sort_key(match: dict[str, Any]) -> tuple[int, int, float, float, str]:
    market = match.get("market") or {}
    yes_ask = _float(market.get("yes_ask"))
    no_bid = _float(market.get("no_bid"))
    price_discipline_rank = 0 if yes_ask <= 0.49 else 1
    opposite_certain_rank = 1 if no_bid >= 0.98 and yes_ask <= 0.02 else 0
    expected_net_edge = 0.68 - yes_ask - 0.03
    volume = _float(market.get("volume"))
    return (
        price_discipline_rank,
        opposite_certain_rank,
        -expected_net_edge,
        -volume,
        str(market.get("ticker") or ""),
    )


def _date_from_ticker(ticker: str) -> Any:
    match = re.search(r"-(\d{2})([A-Z]{3})(\d{2})-", ticker)
    if not match:
        return None
    months = {
        "JAN": 1,
        "FEB": 2,
        "MAR": 3,
        "APR": 4,
        "MAY": 5,
        "JUN": 6,
        "JUL": 7,
        "AUG": 8,
        "SEP": 9,
        "OCT": 10,
        "NOV": 11,
        "DEC": 12,
    }
    return datetime(
        2000 + int(match.group(1)),
        months[match.group(2)],
        int(match.group(3)),
        tzinfo=UTC,
    ).date()


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(_normalize_ts(value).replace("Z", "+00:00")).astimezone(UTC)


def _normalize_ts(value: str) -> str:
    if not value or value == "None":
        return ""
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC).isoformat().replace("+00:00", "Z")


def _hash_json(payload: dict[str, Any]) -> str:
    text = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _clean_number(value: Any) -> str:
    number = float(value)
    if number.is_integer():
        return str(int(number))
    return str(number).replace(".", "_")
