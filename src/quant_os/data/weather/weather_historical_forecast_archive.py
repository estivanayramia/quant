from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from quant_os.data.weather.weather_market_capture_artifacts import (
    normalize_utc_timestamp,
    utc_now_string,
)
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

REPORT_ROOT = Path("reports/sequence52/weather_historical_forecast_archive")
IEM_MOS_ENDPOINT = "https://mesonet.agron.iastate.edu/api/1/mos.json"
USER_AGENT = "quant-os-weather-archive-readonly estivanayramia@example.com"
NYC_TZ = ZoneInfo("America/New_York")


def evaluate_weather_historical_forecast_sources(
    *, campaign_context: str = "profit_campaign"
) -> dict[str, Any]:
    sources = [
        {
            "source_id": "iem_mos_historical_forecast",
            "status": "WEATHER_ARCHIVE_SOURCE_ALLOWED",
            "exact_reason": "PUBLIC_IEM_NWS_DERIVED_MOS_ARCHIVE_NO_AUTH_NO_PAID_ACCESS",
            "auth_required": False,
            "paid_required": False,
            "read_only": True,
            "reference_url": "https://mesonet.agron.iastate.edu/mos/",
        },
        {
            "source_id": "iem_nws_text_archive",
            "status": "WEATHER_ARCHIVE_SOURCE_ALLOWED",
            "exact_reason": "PUBLIC_NWS_TEXT_ARCHIVE_NO_AUTH_NO_PAID_ACCESS_TEXT_PARSING_FALLBACK",
            "auth_required": False,
            "paid_required": False,
            "read_only": True,
            "reference_url": "https://mesonet.agron.iastate.edu/cgi-bin/afos/retrieve.py?help=",
        },
        {
            "source_id": "noaa_ncei_noaaport_nwstg_text",
            "status": "WEATHER_ARCHIVE_SOURCE_ALLOWED",
            "exact_reason": "PUBLIC_NOAA_NCEI_NWSTG_TEXT_ARCHIVE_AUTHORITATIVE_BUT_BULK_ACCESS_HEAVY",
            "auth_required": False,
            "paid_required": False,
            "read_only": True,
            "reference_url": "https://www.ncei.noaa.gov/access/metadata/landing-page/bin/iso?id=gov.noaa.ncdc%3AC00610",
        },
        {
            "source_id": "open_meteo_historical_forecast",
            "status": "WEATHER_ARCHIVE_SOURCE_BLOCKED"
            if campaign_context == "profit_campaign"
            else "WEATHER_ARCHIVE_SOURCE_REVIEW_REQUIRED",
            "exact_reason": "FREE_TIER_NON_COMMERCIAL_ONLY_FOR_PROFIT_CAMPAIGN",
            "auth_required": False,
            "paid_required": False,
            "read_only": True,
            "reference_url": "https://open-meteo.com/en/terms",
        },
    ]
    return {
        "schema_version": "weather_historical_forecast_source_policy_v1",
        "sequence": "52",
        "status": "WEATHER_ARCHIVE_SOURCE_POLICY_EVALUATED",
        "campaign_context": campaign_context,
        "preferred_source_id": "iem_mos_historical_forecast",
        "sources": sources,
        "read_only": True,
        "auth_headers_allowed": False,
        "browser_cookies_allowed": False,
        "paid_api_allowed": False,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
        **SOCIAL_INTAKE_SAFETY,
    }


def build_weather_historical_forecast_archive(
    *,
    markets: list[dict[str, Any]],
    mos_payloads_by_market: dict[str, dict[str, Any]] | None = None,
    public_network_ok: bool = False,
    station: str = "KNYC",
    model: str = "GFS",
    captured_at: str | None = None,
    output_root: str | Path | None = None,
) -> dict[str, Any]:
    captured_at = captured_at or utc_now_string()
    payloads = mos_payloads_by_market or {}
    forecasts: dict[str, dict[str, Any]] = {}
    blockers: list[str] = []
    rejected: list[dict[str, Any]] = []
    fetched_payloads: dict[str, dict[str, Any]] = {}
    for market in markets:
        ticker = str(market.get("ticker"))
        try:
            mos_payload = payloads.get(ticker)
            runtime_ts = _runtime_for_market(market)
            if mos_payload is None:
                if not public_network_ok:
                    raise ValueError("PUBLIC_NETWORK_DISABLED_FOR_IEM_MOS_ARCHIVE")
                cache_key = f"{station}|{model}|{normalize_utc_timestamp(runtime_ts)}"
                if cache_key not in fetched_payloads:
                    fetched_payloads[cache_key] = fetch_iem_mos_payload(
                        station=station,
                        model=model,
                        runtime_ts=runtime_ts,
                    )
                mos_payload = fetched_payloads[cache_key]
            snapshot = iem_mos_payload_to_forecast_snapshot(
                market=market,
                mos_payload=mos_payload,
                captured_at=captured_at,
                station=station,
                model=model,
            )
        except Exception as exc:
            reason = str(exc) or type(exc).__name__
            rejected.append({"market_id": ticker, "blocker": reason})
            blockers.append(reason)
            continue
        forecasts[ticker] = snapshot
    status = (
        "WEATHER_HISTORICAL_FORECASTS_CAPTURED"
        if forecasts
        else "WEATHER_ARCHIVE_SOURCE_BLOCKED"
    )
    payload = {
        "schema_version": "weather_historical_forecast_archive_v1",
        "sequence": "52",
        "status": status,
        "source_policy": evaluate_weather_historical_forecast_sources(),
        "preferred_source_id": "iem_mos_historical_forecast",
        "station": station,
        "model": model,
        "captured_at": normalize_utc_timestamp(captured_at),
        "forecasts_by_market": forecasts,
        "forecast_count": len(forecasts),
        "network_request_count": len(fetched_payloads),
        "rejected_markets": rejected,
        "blockers": sorted(set(blockers)),
        "read_only": True,
        "network_fetch_attempted": public_network_ok and not mos_payloads_by_market,
        "ci_network_dependency": False,
        "auth_headers_allowed": False,
        "browser_cookies_allowed": False,
        "paid_api_allowed": False,
        "order_placement_allowed": False,
        "order_cancellation_allowed": False,
        "anti_bot_evasion_allowed": False,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
        **SOCIAL_INTAKE_SAFETY,
    }
    if output_root is not None:
        payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def fetch_iem_mos_payload(
    *,
    station: str,
    model: str,
    runtime_ts: str,
) -> dict[str, Any]:
    runtime = normalize_utc_timestamp(runtime_ts).replace("T", " ").replace("Z", "")
    if runtime.endswith(":00"):
        runtime = runtime[:-3]
    query = urllib.parse.urlencode(
        {
            "station": station,
            "model": model,
            "runtime": runtime + "Z",
        }
    )
    request = urllib.request.Request(
        f"{IEM_MOS_ENDPOINT}?{query}",
        headers={"User-Agent": USER_AGENT},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def iem_mos_payload_to_forecast_snapshot(
    *,
    market: dict[str, Any],
    mos_payload: dict[str, Any],
    captured_at: str,
    station: str = "KNYC",
    model: str = "GFS",
) -> dict[str, Any]:
    rows = list(mos_payload.get("data", []))
    if not rows:
        raise ValueError("IEM_MOS_ARCHIVE_EMPTY")
    target_date = _target_local_date(market)
    target_rows = [
        row
        for row in rows
        if _parse_iem_ts(str(row.get("ftime_utc"))).astimezone(NYC_TZ).date()
        == target_date
        and row.get("tmp") is not None
    ]
    if not target_rows:
        raise ValueError("IEM_MOS_TARGET_DATE_FORECAST_MISSING")
    runtime_values = {_normalize_iem_timestamp(str(row.get("runtime_utc"))) for row in target_rows}
    if len(runtime_values) != 1:
        raise ValueError("IEM_MOS_MIXED_MODEL_RUNTIMES")
    runtime_ts = next(iter(runtime_values))
    known_at_ts = runtime_ts
    orderbook_ts = normalize_utc_timestamp(str(market.get("close_time")))
    if _parse_utc(runtime_ts) > _parse_utc(known_at_ts):
        raise ValueError("FORECAST_AFTER_KNOWN_AT")
    if _parse_utc(known_at_ts) > _parse_utc(orderbook_ts):
        raise ValueError("KNOWN_AT_AFTER_ORDERBOOK")
    valid_times = [
        _normalize_iem_timestamp(str(row["ftime_utc"])) for row in target_rows
    ]
    forecast_value = max(float(row["tmp"]) for row in target_rows)
    periods = [
        {
            "startTime": valid_time,
            "endTime": normalize_utc_timestamp(
                (
                    _parse_utc(valid_time) + timedelta(hours=3)
                ).isoformat().replace("+00:00", "Z")
            ),
            "temperature": float(row["tmp"]),
            "temperatureUnit": "F",
            "source": "iem_mos_historical_forecast",
        }
        for row, valid_time in zip(target_rows, valid_times, strict=True)
    ]
    forecast_payload = {
        "properties": {
            "generatedAt": runtime_ts,
            "updateTime": runtime_ts,
            "periods": periods,
        },
        "archive_metadata": {
            "source_id": "iem_mos_historical_forecast",
            "station": station,
            "model": model,
            "model_runtime_ts": runtime_ts,
            "known_at_ts": known_at_ts,
            "target_local_date": target_date.isoformat(),
            "valid_times": valid_times,
            "uses_realized_weather": False,
            "uses_resolution_as_forecast": False,
        },
    }
    return {
        "schema_version": "iem_mos_historical_forecast_snapshot_v1",
        "market_id": market.get("ticker"),
        "forecast_source": "iem_mos_historical_forecast",
        "forecast_url": IEM_MOS_ENDPOINT,
        "station": station,
        "model": model,
        "forecast_ts": runtime_ts,
        "known_at_ts": known_at_ts,
        "orderbook_ts": orderbook_ts,
        "target_local_date": target_date.isoformat(),
        "valid_times": valid_times,
        "forecast_value": forecast_value,
        "forecast_payload": forecast_payload,
        "uses_realized_weather": False,
        "uses_resolution_as_forecast": False,
        "read_only": True,
        "source_policy_status": "WEATHER_ARCHIVE_SOURCE_ALLOWED",
    }


def _runtime_for_market(market: dict[str, Any]) -> str:
    open_time = _parse_utc(normalize_utc_timestamp(str(market.get("open_time"))))
    runtime_hour = max(hour for hour in (0, 6, 12, 18) if hour <= open_time.hour)
    runtime = open_time.replace(hour=runtime_hour, minute=0, second=0, microsecond=0)
    if runtime > open_time:
        runtime -= timedelta(hours=6)
    return runtime.isoformat().replace("+00:00", "Z")


def _target_local_date(market: dict[str, Any]) -> datetime.date:
    occurrence = str(market.get("occurrence_datetime") or "")
    if occurrence:
        return _parse_utc(normalize_utc_timestamp(occurrence)).astimezone(NYC_TZ).date()
    close_time = str(market.get("close_time"))
    return _parse_utc(normalize_utc_timestamp(close_time)).astimezone(NYC_TZ).date()


def _parse_iem_ts(value: str) -> datetime:
    return _parse_utc(_normalize_iem_timestamp(value))


def _normalize_iem_timestamp(value: str) -> str:
    raw = value.strip()
    if raw.endswith(".000"):
        raw = raw[:-4]
    if not raw.endswith("Z"):
        raw = raw + "Z"
    return normalize_utc_timestamp(raw)


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.astimezone(UTC).replace(microsecond=0)


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_weather_historical_forecast_archive.json"
    md_path = root / "latest_weather_historical_forecast_archive.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 52 Weather Historical Forecast Archive",
        "",
        "Public read-only historical forecast archive evaluation and capture.",
        "",
        f"Status: {payload['status']}",
        f"Forecasts captured: {payload['forecast_count']}",
        f"Preferred source: {payload['preferred_source_id']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        f"Execution authority: {payload['execution_authority']}",
        "",
        "## Blockers",
    ]
    lines.extend(f"- {item}" for item in payload.get("blockers", []) or ["None"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
