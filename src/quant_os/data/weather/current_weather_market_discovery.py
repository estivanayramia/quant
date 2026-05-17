from __future__ import annotations

import hashlib
import json
import re
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quant_os.readiness.canary_readiness_common import (
    safety_payload,
    utc_now,
    write_json_markdown_report,
)

REPORT_DIR = Path("reports/first_dollar_preflight/current_market_discovery")
KALSHI_PUBLIC_BASE_URL = "https://external-api.kalshi.com/trade-api/v2"
DEFAULT_SERIES_TICKERS = ["KXHIGHNY", "KXHIGHAUS", "KXHIGHCHI", "KXHIGHMIA", "KXHIGHLAX"]


def evaluate_current_weather_market_discovery(
    *,
    output_root: str | Path = ".",
    markets_payload: dict[str, Any] | None = None,
    series_payload: dict[str, Any] | None = None,
    orderbook_payloads: dict[str, dict[str, Any]] | None = None,
    captured_at: str | None = None,
    public_network_ok: bool = False,
    series_tickers: list[str] | None = None,
) -> dict[str, Any]:
    captured_at = captured_at or utc_now()
    source_urls: list[str] = []
    discovery_blocked = False
    if public_network_ok and markets_payload is None:
        try:
            series_payload, markets_payload, orderbook_payloads, source_urls = (
                fetch_public_kalshi_current_weather_payloads(
                    series_tickers=series_tickers or DEFAULT_SERIES_TICKERS
                )
            )
        except OSError:
            markets_payload = {"markets": []}
            orderbook_payloads = {}
            discovery_blocked = True
    markets = list((markets_payload or {}).get("markets", []))
    orderbook_payloads = orderbook_payloads or {}
    series = _series_by_ticker(series_payload)
    candidates = [
        _candidate_from_market(
            market,
            series=series.get(str(market.get("series_ticker") or ""))
            or series.get(str(market.get("event_ticker") or "").split("-")[0])
            or {},
            orderbook=orderbook_payloads.get(str(market.get("ticker")), {}),
            captured_at=captured_at,
        )
        for market in markets
    ]
    candidates = [candidate for candidate in candidates if candidate["candidate_rule_match"]]
    candidates.sort(key=lambda item: _candidate_sort_key(item, captured_at))
    selected = candidates[0] if candidates else None
    status = "CURRENT_MARKET_FOUND" if selected else "NO_CURRENT_ELIGIBLE_MARKET"
    blockers = [] if selected else ["NO_CURRENT_PUBLIC_WEATHER_MARKET_FOUND"]
    if discovery_blocked:
        status = "CURRENT_MARKET_DISCOVERY_BLOCKED"
        blockers = ["PUBLIC_MARKET_DISCOVERY_FAILED"]
    payload = safety_payload(
        schema_version="current_weather_market_discovery_v1",
        status=status,
        allowed_statuses=[
            "CURRENT_MARKET_FOUND",
            "NO_CURRENT_ELIGIBLE_MARKET",
            "CURRENT_MARKET_DISCOVERY_BLOCKED",
        ],
        candidate_id="pm_weather_forecast_market_mismatch",
        venue="kalshi",
        captured_at=captured_at,
        selected_market=selected,
        candidates=candidates,
        market_count=len(markets),
        candidate_count=len(candidates),
        public_read_only=True,
        request_methods=["GET"],
        authenticated_endpoint_called=False,
        checked_account_balance=False,
        checked_portfolio=False,
        source_urls=source_urls or _default_source_urls(candidates),
        blockers=blockers,
        api_keys_loaded=False,
        private_keys_loaded=False,
        next_action="Run public forecast matching."
        if selected
        else "Keep the data-only current-market watcher active.",
    )
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_current_market_discovery.json",
        md_name="latest_current_market_discovery.md",
        title="Current Weather Market Discovery",
        summary="Public unauthenticated Kalshi weather-market discovery. No cookies, credentials, auth, orders, or cancels.",
    )
    return payload


def write_current_weather_market_discovery_report(
    *,
    output_root: str | Path = ".",
    public_network_ok: bool = False,
) -> dict[str, Any]:
    return evaluate_current_weather_market_discovery(
        output_root=output_root,
        public_network_ok=public_network_ok,
    )


def fetch_public_kalshi_current_weather_payloads(
    *,
    series_tickers: list[str],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, Any]], list[str]]:
    all_series: list[dict[str, Any]] = []
    all_markets: list[dict[str, Any]] = []
    orderbooks: dict[str, dict[str, Any]] = {}
    urls: list[str] = []
    for series_ticker in series_tickers:
        series_url = f"{KALSHI_PUBLIC_BASE_URL}/series/{series_ticker}"
        series_payload = _fetch_json(series_url)
        urls.append(series_url)
        all_series.append(series_payload.get("series", series_payload))
        query = urllib.parse.urlencode(
            {"series_ticker": series_ticker, "status": "open", "limit": 100}
        )
        markets_url = f"{KALSHI_PUBLIC_BASE_URL}/markets?{query}"
        markets_payload = _fetch_json(markets_url)
        urls.append(markets_url)
        for market in markets_payload.get("markets", []):
            market["series_ticker"] = series_ticker
            all_markets.append(market)
    for market in all_markets[:25]:
        ticker = str(market.get("ticker") or "")
        if not ticker:
            continue
        orderbook_url = f"{KALSHI_PUBLIC_BASE_URL}/markets/{ticker}/orderbook"
        orderbooks[ticker] = _fetch_json(orderbook_url)
        urls.append(orderbook_url)
    return {"series": all_series}, {"markets": all_markets}, orderbooks, urls


def _candidate_from_market(
    market: dict[str, Any],
    *,
    series: dict[str, Any],
    orderbook: dict[str, Any],
    captured_at: str,
) -> dict[str, Any]:
    title = str(market.get("title") or "")
    location = _location_from_title(title)
    weather_variable = "temperature_max_f" if "high temp" in title.lower() else None
    yes_bid = _float(market.get("yes_bid_dollars", market.get("yes_bid")))
    yes_ask = _float(market.get("yes_ask_dollars", market.get("yes_ask")))
    no_bid = _float(market.get("no_bid_dollars", market.get("no_bid")))
    no_ask = _float(market.get("no_ask_dollars", market.get("no_ask")))
    bid_size = _float(market.get("yes_bid_size_fp", market.get("yes_bid_size")))
    ask_size = _float(market.get("yes_ask_size_fp", market.get("yes_ask_size")))
    floor = market.get("floor_strike")
    cap = market.get("cap_strike")
    bucket = _bucket_from_market(market)
    ticker = market.get("ticker")
    orderbook_url = f"{KALSHI_PUBLIC_BASE_URL}/markets/{ticker}/orderbook" if ticker else None
    market_url = (
        f"{KALSHI_PUBLIC_BASE_URL}/markets?series_ticker={market.get('series_ticker')}&status=open"
    )
    spread = max(yes_ask - yes_bid, 0.0) if yes_ask else 0.0
    orderbook_liquidity = _orderbook_liquidity(orderbook)
    liquidity = orderbook_liquidity or bid_size + ask_size
    evidence_hash = _hash_json({"market": market, "orderbook": orderbook})
    return {
        "candidate_id": "pm_weather_forecast_market_mismatch",
        "venue": "kalshi",
        "ticker": ticker,
        "event_ticker": market.get("event_ticker"),
        "series_ticker": market.get("series_ticker") or series.get("ticker"),
        "title": title,
        "status": market.get("status"),
        "open_time": market.get("open_time"),
        "close_time": market.get("close_time"),
        "resolution_ts": market.get("expected_expiration_time")
        or market.get("expiration_time")
        or market.get("close_time"),
        "settlement_rules": market.get("rules_primary")
        or series.get("settlement_sources")
        or "Public Kalshi/NWS weather market rules.",
        "location": location,
        "weather_variable": weather_variable,
        "threshold_bucket": bucket,
        "floor_strike": floor,
        "cap_strike": cap,
        "strike_type": market.get("strike_type"),
        "yes_bid": yes_bid,
        "yes_ask": yes_ask,
        "no_bid": no_bid,
        "no_ask": no_ask,
        "spread": round(spread, 6),
        "liquidity": liquidity,
        "volume": _float(market.get("volume_fp", market.get("volume"))),
        "orderbook_available": bool(orderbook),
        "orderbook_ts": captured_at,
        "source_url": market_url,
        "orderbook_url": orderbook_url,
        "source_provenance": "kalshi_public_market_data",
        "market_evidence_hash": evidence_hash,
        "candidate_rule_match": bool(ticker and location and weather_variable and bucket),
    }


def _series_by_ticker(series_payload: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    raw = (series_payload or {}).get("series", [])
    if isinstance(raw, dict):
        raw = [raw]
    return {str(item.get("ticker") or ""): item for item in raw}


def _candidate_sort_key(candidate: dict[str, Any], captured_at: str) -> tuple[int, str, float, str]:
    occurrence_date = _date_from_ticker(str(candidate.get("ticker") or ""))
    captured_date = _parse_ts(captured_at).date()
    future_rank = 0 if occurrence_date and occurrence_date > captured_date else 1
    return (
        future_rank,
        str(occurrence_date or captured_date),
        -float(candidate.get("volume") or 0),
        str(candidate.get("ticker") or ""),
    )


def _location_from_title(title: str) -> str | None:
    lowered = title.lower()
    if "nyc" in lowered or "new york" in lowered:
        return "Central Park, New York"
    if "austin" in lowered:
        return "Austin, Texas"
    if "chicago" in lowered:
        return "Chicago, Illinois"
    if "miami" in lowered:
        return "Miami, Florida"
    if " la" in f" {lowered}" or "los angeles" in lowered:
        return "Los Angeles, California"
    return None


def _bucket_from_market(market: dict[str, Any]) -> str | None:
    strike_type = str(market.get("strike_type") or "").lower()
    floor = market.get("floor_strike")
    cap = market.get("cap_strike")
    if strike_type == "between" and floor is not None and cap is not None:
        return f"{_clean_number(floor)}_to_{_clean_number(cap)}_f_inclusive"
    if strike_type == "greater" and floor is not None:
        return f"greater_than_{_clean_number(floor)}_f"
    if strike_type == "less" and cap is not None:
        return f"less_than_{_clean_number(cap)}_f"
    return None


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


def _orderbook_liquidity(orderbook: dict[str, Any]) -> float:
    book = orderbook.get("orderbook_fp", orderbook)
    total = 0.0
    for side in ("yes", "yes_dollars", "no", "no_dollars"):
        for level in book.get(side, []) or []:
            if len(level) >= 2:
                total += _float(level[1])
    return total


def _default_source_urls(candidates: list[dict[str, Any]]) -> list[str]:
    urls = []
    for candidate in candidates:
        for key in ("source_url", "orderbook_url"):
            if candidate.get(key):
                urls.append(str(candidate[key]))
    return urls


def _fetch_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "quant-os-current-weather-readonly estivanayramia@example.com"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _hash_json(payload: dict[str, Any]) -> str:
    text = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


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
