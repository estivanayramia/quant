from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from quant_os.data.weather.weather_market_discovery import (
    KALSHI_BASE_URL,
    default_kalshi_series_fixture,
)
from quant_os.data.weather.weather_source_matching import match_weather_source_to_market
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

REPORT_ROOT = Path("reports/sequence52/weather_resolved_discovery")
USER_AGENT = "quant-os-phase52-readonly estivanayramia@example.com"


def default_resolved_markets_fixture() -> dict[str, Any]:
    markets = []
    for day, result, value, low, high in [
        (12, "YES", "73", 73, 74),
        (13, "NO", "68", 72, 73),
        (14, "YES", "80", 80, 81),
    ]:
        markets.append(
            {
                "ticker": f"KXHIGHNY-26MAY{day}-B{low}.5",
                "event_ticker": f"KXHIGHNY-26MAY{day}",
                "title": f"Will the high temp in NYC be {low}-{high} deg on May {day}, 2026?",
                "status": "settled",
                "market_type": "binary",
                "strike_type": "between",
                "floor_strike": low,
                "cap_strike": high,
                "yes_bid_dollars": "0.8600",
                "yes_ask_dollars": "0.8800",
                "yes_bid_size_fp": "140.00",
                "yes_ask_size_fp": "160.00",
                "volume_fp": str(1000 + day),
                "open_interest_fp": str(800 + day),
                "open_time": f"2026-05-{day - 1:02d}T14:00:00Z",
                "close_time": f"2026-05-{day + 1:02d}T04:59:00Z",
                "expected_expiration_time": f"2026-05-{day + 1:02d}T14:00:00Z",
                "occurrence_datetime": f"2026-05-{day:02d}T14:00:00Z",
                "expiration_value": value,
                "result": result,
                "rules_primary": (
                    f"If the highest temperature recorded in Central Park, New York for May {day}, "
                    "2026 as reported by the National Weather Service's Climatological Report "
                    f"(Daily), is between {low}-{high} deg, then the market resolves to Yes."
                ),
            }
        )
    markets.append(
        {
            "ticker": "KXHIGHNY-26MAY15-T65",
            "event_ticker": "KXHIGHNY-26MAY15",
            "title": "Will the high temp in NYC be <65 deg on May 15, 2026?",
            "status": "closed",
            "market_type": "binary",
            "strike_type": "less",
            "cap_strike": 65,
            "yes_bid_dollars": "0.1200",
            "yes_ask_dollars": "0.1400",
            "yes_bid_size_fp": "55.00",
            "yes_ask_size_fp": "67.00",
            "volume_fp": "211.00",
            "open_interest_fp": "188.00",
            "open_time": "2026-05-14T14:00:00Z",
            "close_time": "2026-05-16T04:59:00Z",
            "expected_expiration_time": "2026-05-16T14:00:00Z",
            "occurrence_datetime": "2026-05-15T14:00:00Z",
            "expiration_value": "",
            "result": "",
            "rules_primary": (
                "If the highest temperature recorded in Central Park, New York for May 15, "
                "2026 as reported by the National Weather Service's Climatological Report "
                "(Daily), is less than 65 deg, then the market resolves to Yes."
            ),
        }
    )
    return {"markets": markets}


def discover_resolved_weather_markets(
    *,
    series_payload: dict[str, Any] | None = None,
    markets_payload: dict[str, Any] | None = None,
    captured_at: str | None = None,
) -> dict[str, Any]:
    series_payload = series_payload or default_kalshi_series_fixture()
    markets_payload = markets_payload or default_resolved_markets_fixture()
    series = series_payload.get("series", series_payload)
    markets = list(markets_payload.get("markets", []))
    candidates = [_candidate_from_market(market, series=series) for market in markets]
    candidates = [candidate for candidate in candidates if candidate["discovery_valid"]]
    candidates.sort(
        key=lambda item: (
            0 if item["proof_label_available"] else 1,
            str(item.get("event_date") or ""),
            item["ticker"],
        )
    )
    resolved = [item for item in candidates if item["proof_label_available"]]
    pending = [item for item in candidates if not item["proof_label_available"]]
    if resolved:
        status = "RESOLVED_WEATHER_BATCH_READY"
        blockers: list[str] = []
    elif candidates:
        status = "RESOLUTION_LABELS_MISSING"
        blockers = ["NO_RESOLVED_WEATHER_MARKET_LABELS"]
    else:
        status = "WEATHER_MARKET_BACKFILL_BLOCKED"
        blockers = ["NO_SOURCE_POLICY_APPROVED_RESOLVED_WEATHER_MARKETS"]
    return {
        "schema_version": "weather_resolved_market_discovery_v1",
        "sequence": "52",
        "status": status,
        "candidate_id": "pm_weather_forecast_market_mismatch",
        "venue": "kalshi",
        "series_ticker": series.get("ticker"),
        "series_title": series.get("title"),
        "captured_at": captured_at,
        "market_count": len(markets),
        "candidate_count": len(candidates),
        "resolved_market_count": len(resolved),
        "pending_market_count": len(pending),
        "markets": candidates,
        "pending_markets": pending,
        "blockers": blockers,
        "source_policy_verdict": "PUBLIC_READ_ONLY_ALLOWED",
        "public_market_metadata": bool(candidates),
        "public_price_orderbook_path_known": bool(candidates),
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


def write_weather_resolved_discovery_report(
    *,
    output_root: str | Path = ".",
    series_payload: dict[str, Any] | None = None,
    markets_payload: dict[str, Any] | None = None,
    captured_at: str | None = None,
    public_network_ok: bool = False,
    series_ticker: str = "KXHIGHNY",
) -> dict[str, Any]:
    network_fetch_attempted = False
    if public_network_ok and (series_payload is None or markets_payload is None):
        series_payload, markets_payload = fetch_public_kalshi_resolved_weather_payloads(
            series_ticker=series_ticker
        )
        network_fetch_attempted = True
    payload = discover_resolved_weather_markets(
        series_payload=series_payload,
        markets_payload=markets_payload,
        captured_at=captured_at,
    )
    payload["network_fetch_attempted"] = network_fetch_attempted
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def fetch_public_kalshi_resolved_weather_payloads(
    *,
    series_ticker: str = "KXHIGHNY",
) -> tuple[dict[str, Any], dict[str, Any]]:
    series_payload = _fetch_json(f"{KALSHI_BASE_URL}/series/{series_ticker}")
    all_markets: list[dict[str, Any]] = []
    for status in ("settled", "closed"):
        cursor = ""
        for _page in range(5):
            query = {"series_ticker": series_ticker, "status": status, "limit": 100}
            if cursor:
                query["cursor"] = cursor
            payload = _fetch_json(f"{KALSHI_BASE_URL}/markets?{urllib.parse.urlencode(query)}")
            all_markets.extend(payload.get("markets", []))
            cursor = str(payload.get("cursor") or "")
            if not cursor:
                break
    return series_payload, {"markets": all_markets}


def _candidate_from_market(market: dict[str, Any], *, series: dict[str, Any]) -> dict[str, Any]:
    source_match = match_weather_source_to_market(market, series)
    yes_bid = _float(market.get("yes_bid_dollars"))
    yes_ask = _float(market.get("yes_ask_dollars"))
    status = str(market.get("status") or "").lower()
    result = str(market.get("result") or "").upper()
    value_present = market.get("expiration_value") not in {None, ""}
    return {
        "ticker": market.get("ticker"),
        "event_id": market.get("event_ticker"),
        "title": market.get("title"),
        "status": market.get("status"),
        "location": source_match["location"],
        "variable": source_match["variable"],
        "bucket_range": source_match["bucket_range"],
        "yes_no_outcome_meaning": "YES means observed weather value is inside the market bucket",
        "yes_bid": yes_bid,
        "yes_ask": yes_ask,
        "market_mid": round((yes_bid + yes_ask) / 2.0, 6),
        "spread": round(max(yes_ask - yes_bid, 0.0), 6),
        "liquidity": _float(market.get("yes_bid_size_fp")) + _float(market.get("yes_ask_size_fp")),
        "volume": _float(market.get("volume_fp")),
        "open_interest": _float(market.get("open_interest_fp")),
        "open_time": market.get("open_time"),
        "close_time": market.get("close_time"),
        "expected_expiration_time": market.get("expected_expiration_time"),
        "occurrence_datetime": market.get("occurrence_datetime"),
        "event_date": str(market.get("occurrence_datetime") or "")[:10],
        "rules_primary": market.get("rules_primary"),
        "resolution_source": source_match["resolution_source"],
        "source_urls": [
            item.get("url")
            for item in (series.get("settlement_sources") or [])
            if item.get("url")
        ],
        "resolution_value": market.get("expiration_value") or None,
        "exchange_result": result,
        "proof_label_available": result in {"YES", "NO"} or value_present,
        "source_matching_status": source_match["status"],
        "discovery_valid": (
            status in {"closed", "settled", "finalized"}
            and source_match["proof_mapping_ready"]
            and yes_ask >= 0.0
        ),
    }


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _fetch_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT}, method="GET")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_weather_resolved_discovery.json"
    md_path = root / "latest_weather_resolved_discovery.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 52 Weather Resolved Discovery",
        "",
        "Public read-only resolved weather market discovery. No execution authority.",
        "",
        f"Status: {payload['status']}",
        f"Resolved markets: {payload['resolved_market_count']}",
        f"Pending markets: {payload['pending_market_count']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        f"Execution authority: {payload['execution_authority']}",
        "",
        "## Blockers",
    ]
    lines.extend(f"- {item}" for item in payload["blockers"] or ["None"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
