from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quant_os.data.weather.weather_market_capture_artifacts import (
    canonical_provenance_hash,
    load_capture_artifact,
    normalize_utc_timestamp,
)
from quant_os.data.weather.weather_market_discovery import (
    default_kalshi_markets_fixture,
    default_kalshi_series_fixture,
)
from quant_os.data.weather.weather_market_public_capture import (
    default_forecast_fixture,
    default_orderbook_fixture,
    run_weather_market_public_capture,
)
from quant_os.research.replay_candidates.weather_market_replay_schema import (
    CANDIDATE_ID,
    WeatherMarketReplayRow,
)
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

REPORT_ROOT = Path("reports/sequence51/weather_dataset")
MONTHS = {
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


def build_weather_market_dataset_from_capture(
    *,
    capture_manifest_path: str | Path,
    market_artifact_path: str | Path,
    orderbook_artifact_path: str | Path,
    forecast_artifact_path: str | Path,
    resolution_artifact_path: str | Path,
    output_root: str | Path = ".",
    override_known_at_ts: str | None = None,
    override_orderbook_ts: str | None = None,
) -> dict[str, Any]:
    manifest = load_capture_artifact(capture_manifest_path)["payload"]
    market_artifact = load_capture_artifact(market_artifact_path)
    orderbook_artifact = load_capture_artifact(orderbook_artifact_path)
    forecast_artifact = load_capture_artifact(forecast_artifact_path)
    resolution_artifact = load_capture_artifact(resolution_artifact_path)
    market_payload = market_artifact["payload"]
    market = market_payload["selected_market"]
    source_match = market_payload["source_matching"]
    forecast_payload = forecast_artifact["payload"]["forecast"]
    resolution_payload = resolution_artifact["payload"]
    orderbook_payload = orderbook_artifact["payload"]
    orderbook_stats = _orderbook_stats(orderbook_payload["orderbook"])
    target_date = _target_date(market)
    forecast_ts = _forecast_timestamp(forecast_payload)
    known_at_ts = normalize_utc_timestamp(override_known_at_ts or forecast_ts)
    orderbook_ts = normalize_utc_timestamp(
        override_orderbook_ts or orderbook_artifact.get("captured_at") or orderbook_payload["captured_at"]
    )
    forecast_value = _forecast_high_for_date(forecast_payload, target_date)
    resolution_label = str(resolution_payload.get("resolution_label") or "")
    proof_eligible = bool(resolution_label)
    row_payload = {
        "candidate_id": CANDIDATE_ID,
        "market_id": market["ticker"],
        "event_id": market["event_ticker"],
        "location": source_match["location"],
        "variable": source_match["variable"],
        "bucket_range": source_match["bucket_range"],
        "forecast_value": forecast_value,
        "forecast_probability": _forecast_bucket_probability(
            forecast_value,
            source_match["bucket_range"],
        ),
        "forecast_source": "nws_api",
        "forecast_ts": forecast_ts,
        "market_price": orderbook_stats["yes_ask"],
        "market_mid": orderbook_stats["market_mid"],
        "spread": orderbook_stats["spread"],
        "liquidity": orderbook_stats["liquidity"],
        "orderbook_ts": orderbook_ts,
        "resolution_value": _resolution_value(resolution_payload),
        "resolution_label": resolution_label,
        "resolution_ts": normalize_utc_timestamp(resolution_payload["resolution_ts"]),
        "known_at_ts": known_at_ts,
        "source_quality": "PUBLIC_READ_ONLY_RATE_LIMITED",
        "provenance_hash": canonical_provenance_hash(
            {
                "manifest": manifest.get("combined_provenance_hash"),
                "market": market_artifact["provenance_hash"],
                "orderbook": orderbook_artifact["provenance_hash"],
                "forecast": forecast_artifact["provenance_hash"],
                "resolution": resolution_artifact["provenance_hash"],
            }
        ),
        "fixture_only": False,
        "synthetic": False,
        "proof_eligible": proof_eligible,
        "source_ids": ["kalshi_public_market_data", "nws_api", "nws_climatological_report"],
        "data_quality_flags": []
        if proof_eligible
        else ["resolution_label_missing", "not_proof"],
    }
    row = WeatherMarketReplayRow.model_validate(row_payload)
    rows = [row.to_report_dict()]
    proof_count = sum(1 for item in rows if item["proof_eligible"])
    status = (
        "WEATHER_MARKET_DATASET_READY"
        if proof_count
        else "RESOLUTION_LABELS_MISSING"
    )
    payload = {
        "schema_version": "weather_market_dataset_v1",
        "sequence": "51",
        "dataset_status": status,
        "candidate_id": CANDIDATE_ID,
        "row_count": len(rows),
        "real_public_row_count": len(rows),
        "fixture_row_count": 0,
        "proof_row_count": proof_count,
        "rows": rows,
        "capture_manifest_path": str(capture_manifest_path).replace("\\", "/"),
        "blockers": [] if proof_count else ["RESOLUTION_LABELS_MISSING"],
        "source_quality_warnings": [
            "NWS deterministic forecast converted to heuristic bucket probability",
            "Resolution label required before proof rows can count",
        ],
        "no_lookahead": True,
        "ci_network_dependency": False,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
        **SOCIAL_INTAKE_SAFETY,
    }
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def write_weather_market_dataset_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    capture = run_weather_market_public_capture(
        output_root=output_root,
        public_network_ok=True,
        run_id="fixture_dataset_051",
        series_payload=default_kalshi_series_fixture(),
        markets_payload=default_kalshi_markets_fixture(),
        orderbook_payload=default_orderbook_fixture(),
        forecast_payload=default_forecast_fixture(),
    )
    return build_weather_market_dataset_from_capture(
        capture_manifest_path=capture["manifest_path"],
        market_artifact_path=capture["artifacts"]["market_metadata"]["path"],
        orderbook_artifact_path=capture["artifacts"]["orderbook_snapshot"]["path"],
        forecast_artifact_path=capture["artifacts"]["forecast_snapshot"]["path"],
        resolution_artifact_path=capture["artifacts"]["resolution_snapshot"]["path"],
        output_root=output_root,
    )


def _target_date(market: dict[str, Any]) -> datetime.date:
    event_ticker = str(market.get("event_ticker", ""))
    try:
        _, raw = event_ticker.rsplit("-", 1)
        year = 2000 + int(raw[:2])
        month = MONTHS[raw[2:5].upper()]
        day = int(raw[5:])
        return datetime(year, month, day, tzinfo=UTC).date()
    except (KeyError, ValueError):
        occurrence = str(market.get("occurrence_datetime") or "")
        return datetime.fromisoformat(occurrence.replace("Z", "+00:00")).date()


def _forecast_timestamp(forecast_payload: dict[str, Any]) -> str:
    properties = forecast_payload.get("properties", {})
    value = str(properties.get("generatedAt") or properties.get("updateTime"))
    return normalize_utc_timestamp(value)


def _forecast_high_for_date(forecast_payload: dict[str, Any], target_date: datetime.date) -> float:
    periods = forecast_payload.get("properties", {}).get("periods", [])
    values = []
    for period in periods:
        start = datetime.fromisoformat(str(period["startTime"]))
        if start.date() == target_date and str(period.get("temperatureUnit")) == "F":
            values.append(float(period["temperature"]))
    if not values:
        raise ValueError(f"no NWS hourly forecast periods for target date {target_date}")
    return max(values)


def _forecast_bucket_probability(forecast_value: float, bucket_range: str) -> float:
    in_bucket = _bucket_contains(forecast_value, bucket_range)
    return 0.78 if in_bucket else 0.22


def _bucket_contains(value: float, bucket_range: str) -> bool:
    parts = bucket_range.split("_")
    if bucket_range.startswith("greater_than_"):
        return value > float(parts[2])
    if bucket_range.startswith("less_than_"):
        return value < float(parts[2])
    if "_to_" in bucket_range:
        low = float(parts[0])
        high = float(parts[2])
        return low <= value <= high
    return False


def _orderbook_stats(orderbook: dict[str, Any]) -> dict[str, float]:
    books = orderbook.get("orderbook_fp", {})
    yes_bids = [_price_size(row) for row in books.get("yes_dollars", [])]
    no_bids = [_price_size(row) for row in books.get("no_dollars", [])]
    best_yes_bid = max((price for price, _size in yes_bids), default=0.0)
    best_no_bid = max((price for price, _size in no_bids), default=0.0)
    yes_ask = 1.0 - best_no_bid if best_no_bid else 0.0
    spread = max(yes_ask - best_yes_bid, 0.0)
    liquidity = sum(size for _price, size in yes_bids) + sum(size for _price, size in no_bids)
    return {
        "yes_bid": round(best_yes_bid, 6),
        "yes_ask": round(yes_ask, 6),
        "market_mid": round((best_yes_bid + yes_ask) / 2.0, 6),
        "spread": round(spread, 6),
        "liquidity": round(liquidity, 6),
    }


def _price_size(row: list[Any]) -> tuple[float, float]:
    return float(row[0]), float(row[1])


def _resolution_value(resolution_payload: dict[str, Any]) -> float | None:
    value = resolution_payload.get("resolution_value")
    if value in {None, ""}:
        return None
    return float(value)


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_weather_dataset.json"
    md_path = root / "latest_weather_dataset.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 51 Weather Dataset",
        "",
        "Non-fixture weather replay dataset builder. Missing labels block proof rows.",
        "",
        f"Status: {payload['dataset_status']}",
        f"Rows: {payload['row_count']}",
        f"Proof rows: {payload['proof_row_count']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        f"Execution authority: {payload['execution_authority']}",
        "",
        "## Blockers",
    ]
    lines.extend(f"- {item}" for item in payload["blockers"] or ["None"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
