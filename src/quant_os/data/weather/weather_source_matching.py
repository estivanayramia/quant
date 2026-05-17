from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from quant_os.data.weather.weather_market_capture_artifacts import normalize_utc_timestamp
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

REPORT_ROOT = Path("reports/sequence51/weather_source_matching")


def match_weather_source_to_market(
    market: dict[str, Any],
    series: dict[str, Any] | None = None,
) -> dict[str, Any]:
    series = series or {}
    rules = " ".join(
        str(market.get(key, ""))
        for key in ("title", "rules_primary", "rules_secondary", "subtitle")
    )
    location = _location_from_text(rules)
    variable = _variable_from_text(rules)
    bucket = _bucket_from_market(market, rules)
    blockers = []
    if location is None:
        blockers.append("AMBIGUOUS_LOCATION")
    if variable is None:
        blockers.append("AMBIGUOUS_VARIABLE")
    if bucket is None:
        blockers.append("AMBIGUOUS_BUCKET")
    settlement_sources = list(series.get("settlement_sources", []))
    if not settlement_sources:
        blockers.append("RESOLUTION_SOURCE_MISSING")
    status = "WEATHER_SOURCE_MATCHED" if not blockers else "WEATHER_DATA_CAPTURE_BLOCKED"
    occurrence = str(market.get("occurrence_datetime") or market.get("close_time") or "")
    resolution_time = str(
        market.get("expected_expiration_time")
        or market.get("expiration_time")
        or market.get("close_time")
        or ""
    )
    return {
        "schema_version": "weather_source_matching_v1",
        "sequence": "51",
        "status": status,
        "candidate_id": "pm_weather_forecast_market_mismatch",
        "market_id": market.get("ticker"),
        "event_id": market.get("event_ticker"),
        "location": location,
        "station_or_grid": "Central Park / NWS OKX gridpoint 34,45" if location else None,
        "variable": variable,
        "bucket_range": bucket,
        "forecast_source": "nws_api",
        "forecast_api_url": "https://api.weather.gov/gridpoints/OKX/34,45/forecast/hourly",
        "resolution_source": settlement_sources[0] if settlement_sources else None,
        "forecast_issue_time_policy": "use NWS generatedAt/updateTime normalized to UTC",
        "forecast_valid_time": occurrence,
        "resolution_time": resolution_time,
        "known_at_ts_policy": "forecast_ts <= known_at_ts <= orderbook_ts",
        "blockers": blockers,
        "proof_mapping_ready": not blockers,
        "read_only": True,
        "public_read_only_only": True,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
        **SOCIAL_INTAKE_SAFETY,
    }


def normalized_market_datetime(value: str) -> str:
    return normalize_utc_timestamp(value)


def write_weather_source_matching_report(
    *,
    output_root: str | Path = ".",
    market: dict[str, Any] | None = None,
    series: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if market is None or series is None:
        from quant_os.data.weather.weather_market_discovery import (
            default_kalshi_markets_fixture,
            default_kalshi_series_fixture,
        )

        series = default_kalshi_series_fixture()["series"]
        market = default_kalshi_markets_fixture()["markets"][0]
    payload = match_weather_source_to_market(market, series)
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _location_from_text(text: str) -> str | None:
    lowered = text.lower()
    if "central park" in lowered and ("new york" in lowered or "nyc" in lowered):
        return "Central Park, New York"
    return None


def _variable_from_text(text: str) -> str | None:
    lowered = text.lower()
    if "highest temperature" in lowered or "high temp" in lowered:
        return "temperature_max_f"
    return None


def _bucket_from_market(market: dict[str, Any], text: str) -> str | None:
    strike_type = str(market.get("strike_type", "")).lower()
    if strike_type == "between" and market.get("floor_strike") is not None:
        return "{floor}_to_{cap}_f_inclusive".format(
            floor=_clean_number(market.get("floor_strike")),
            cap=_clean_number(market.get("cap_strike")),
        )
    if strike_type == "greater" and market.get("floor_strike") is not None:
        return "greater_than_{floor}_f".format(floor=_clean_number(market.get("floor_strike")))
    if strike_type == "less" and market.get("cap_strike") is not None:
        return "less_than_{cap}_f".format(cap=_clean_number(market.get("cap_strike")))
    between = re.search(r"between\s+(\d+)\s*-\s*(\d+)", text, flags=re.IGNORECASE)
    if between:
        return f"{between.group(1)}_to_{between.group(2)}_f_inclusive"
    greater = re.search(r"greater than\s+(\d+)", text, flags=re.IGNORECASE)
    if greater:
        return f"greater_than_{greater.group(1)}_f"
    less = re.search(r"less than\s+(\d+)", text, flags=re.IGNORECASE)
    if less:
        return f"less_than_{less.group(1)}_f"
    return None


def _clean_number(value: Any) -> str:
    number = float(value)
    if number.is_integer():
        return str(int(number))
    return str(number).replace(".", "_")


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_weather_source_matching.json"
    md_path = root / "latest_weather_source_matching.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 51 Weather Source Matching",
        "",
        "Maps the selected public market to public weather forecast and resolution sources.",
        "",
        f"Status: {payload['status']}",
        f"Market: {payload['market_id']}",
        f"Location: {payload['location']}",
        f"Variable: {payload['variable']}",
        f"Bucket: {payload['bucket_range']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        f"Execution authority: {payload['execution_authority']}",
        "",
        "## Blockers",
    ]
    lines.extend(f"- {item}" for item in payload["blockers"] or ["None"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
