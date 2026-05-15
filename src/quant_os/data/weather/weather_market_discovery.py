from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from quant_os.data.weather.weather_source_matching import match_weather_source_to_market
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

REPORT_ROOT = Path("reports/sequence51/weather_market_discovery")
KALSHI_BASE_URL = "https://external-api.kalshi.com/trade-api/v2"


def default_kalshi_series_fixture() -> dict[str, Any]:
    return {
        "series": {
            "ticker": "KXHIGHNY",
            "title": "Highest temperature in NYC",
            "category": "Climate and Weather",
            "frequency": "daily",
            "settlement_sources": [
                {
                    "name": "NWS Climatological Report",
                    "url": "https://forecast.weather.gov/product.php?site=OKX&product=CLI&issuedby=NYC",
                }
            ],
        }
    }


def default_kalshi_markets_fixture() -> dict[str, Any]:
    return {
        "markets": [
            {
                "ticker": "KXHIGHNY-26MAY16-B78.5",
                "event_ticker": "KXHIGHNY-26MAY16",
                "title": "Will the high temp in NYC be 78-79 deg on May 16, 2026?",
                "status": "active",
                "market_type": "binary",
                "strike_type": "between",
                "floor_strike": 78,
                "cap_strike": 79,
                "yes_bid_dollars": "0.3800",
                "yes_ask_dollars": "0.4100",
                "yes_bid_size_fp": "1.00",
                "yes_ask_size_fp": "6.00",
                "volume_fp": "1701.64",
                "open_interest_fp": "1288.65",
                "open_time": "2026-05-15T14:00:00Z",
                "close_time": "2026-05-17T04:59:00Z",
                "expected_expiration_time": "2026-05-17T14:00:00Z",
                "occurrence_datetime": "2026-05-16T14:00:00Z",
                "expiration_value": "",
                "result": "",
                "rules_primary": (
                    "If the highest temperature recorded in Central Park, New York for "
                    "May 16, 2026 as reported by the National Weather Service's "
                    "Climatological Report (Daily), is between 78-79 deg, then the "
                    "market resolves to Yes."
                ),
            }
        ]
    }


def discover_weather_markets(
    *,
    series_payload: dict[str, Any] | None = None,
    markets_payload: dict[str, Any] | None = None,
    captured_at: str | None = None,
) -> dict[str, Any]:
    series_payload = series_payload or default_kalshi_series_fixture()
    markets_payload = markets_payload or default_kalshi_markets_fixture()
    series = series_payload.get("series", series_payload)
    markets = list(markets_payload.get("markets", []))
    candidates = [_candidate_from_market(market, series=series) for market in markets]
    candidates = [candidate for candidate in candidates if candidate["discovery_valid"]]
    candidates.sort(
        key=lambda item: (
            -float(item.get("volume") or 0.0),
            -float(item.get("open_interest") or 0.0),
            item["ticker"],
        )
    )
    selected = candidates[0] if candidates else None
    status = "PUBLIC_WEATHER_MARKET_FOUND" if selected else "MARKET_DATA_CAPTURE_BLOCKED"
    blockers = [] if selected else ["NO_SOURCE_POLICY_APPROVED_WEATHER_MARKET_FOUND"]
    return {
        "schema_version": "weather_market_discovery_v1",
        "sequence": "51",
        "status": status,
        "candidate_id": "pm_weather_forecast_market_mismatch",
        "venue": "kalshi",
        "series_ticker": series.get("ticker"),
        "series_title": series.get("title"),
        "captured_at": captured_at,
        "source_policy_verdict": "PUBLIC_READ_ONLY_ALLOWED",
        "market_count": len(markets),
        "candidate_count": len(candidates),
        "selected_market": selected,
        "candidates": candidates,
        "blockers": blockers,
        "public_market_metadata": selected is not None,
        "public_price_orderbook_path_known": selected is not None,
        "resolution_source_known": bool(series.get("settlement_sources")),
        "ci_network_dependency": False,
        "read_only": True,
        "auth_headers_allowed": False,
        "browser_cookies_allowed": False,
        "order_placement_allowed": False,
        "order_cancellation_allowed": False,
        "anti_bot_evasion_allowed": False,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
        **SOCIAL_INTAKE_SAFETY,
    }


def write_weather_market_discovery_report(
    *,
    output_root: str | Path = ".",
    series_payload: dict[str, Any] | None = None,
    markets_payload: dict[str, Any] | None = None,
    captured_at: str | None = None,
    public_network_ok: bool = False,
    series_ticker: str = "KXHIGHNY",
) -> dict[str, Any]:
    if public_network_ok and (series_payload is None or markets_payload is None):
        series_payload, markets_payload = fetch_public_kalshi_weather_payloads(
            series_ticker=series_ticker
        )
    payload = discover_weather_markets(
        series_payload=series_payload,
        markets_payload=markets_payload,
        captured_at=captured_at,
    )
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def fetch_public_kalshi_weather_payloads(
    *,
    series_ticker: str = "KXHIGHNY",
) -> tuple[dict[str, Any], dict[str, Any]]:
    series_payload = _fetch_json(f"{KALSHI_BASE_URL}/series/{series_ticker}")
    query = urllib.parse.urlencode(
        {"series_ticker": series_ticker, "status": "open", "limit": 100}
    )
    markets_payload = _fetch_json(f"{KALSHI_BASE_URL}/markets?{query}")
    return series_payload, markets_payload


def _candidate_from_market(market: dict[str, Any], *, series: dict[str, Any]) -> dict[str, Any]:
    source_match = match_weather_source_to_market(market, series)
    yes_bid = _float(market.get("yes_bid_dollars"))
    yes_ask = _float(market.get("yes_ask_dollars"))
    spread = max(yes_ask - yes_bid, 0.0)
    return {
        "ticker": market.get("ticker"),
        "event_id": market.get("event_ticker"),
        "title": market.get("title"),
        "status": market.get("status"),
        "market_type": market.get("market_type"),
        "location": source_match["location"],
        "variable": source_match["variable"],
        "bucket_range": source_match["bucket_range"],
        "strike_type": market.get("strike_type"),
        "floor_strike": market.get("floor_strike"),
        "cap_strike": market.get("cap_strike"),
        "yes_bid": yes_bid,
        "yes_ask": yes_ask,
        "market_mid": round((yes_bid + yes_ask) / 2.0, 6),
        "spread": round(spread, 6),
        "liquidity": _float(market.get("yes_bid_size_fp")) + _float(market.get("yes_ask_size_fp")),
        "volume": _float(market.get("volume_fp")),
        "open_interest": _float(market.get("open_interest_fp")),
        "open_time": market.get("open_time"),
        "close_time": market.get("close_time"),
        "expected_expiration_time": market.get("expected_expiration_time"),
        "occurrence_datetime": market.get("occurrence_datetime"),
        "rules_primary": market.get("rules_primary"),
        "resolution_source": source_match["resolution_source"],
        "source_matching_status": source_match["status"],
        "discovery_valid": (
            str(market.get("status")) in {"active", "open"}
            and source_match["proof_mapping_ready"]
            and yes_ask > 0.0
            and spread >= 0.0
        ),
    }


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _fetch_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "quant-os-phase51-readonly estivanayramia@example.com"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_weather_market_discovery.json"
    md_path = root / "latest_weather_market_discovery.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    selected = payload.get("selected_market") or {}
    lines = [
        "# Sequence 51 Weather Market Discovery",
        "",
        "Public read-only weather market discovery. No auth, wallet, or execution authority.",
        "",
        f"Status: {payload['status']}",
        f"Selected market: {selected.get('ticker')}",
        f"Location: {selected.get('location')}",
        f"Bucket: {selected.get('bucket_range')}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        f"Execution authority: {payload['execution_authority']}",
        "",
        "## Blockers",
    ]
    lines.extend(f"- {item}" for item in payload["blockers"] or ["None"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
