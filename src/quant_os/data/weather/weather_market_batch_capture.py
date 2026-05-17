from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from quant_os.data.weather.weather_market_batch_import import import_weather_batch_capture
from quant_os.data.weather.weather_market_capture_artifacts import (
    canonical_provenance_hash,
    utc_now_string,
    write_capture_artifact,
)
from quant_os.data.weather.weather_resolution_label_fetcher import (
    default_label_payloads_fixture,
    fetch_weather_resolution_labels,
)
from quant_os.data.weather.weather_resolved_market_discovery import (
    KALSHI_BASE_URL,
    default_resolved_markets_fixture,
    discover_resolved_weather_markets,
)
from quant_os.data.weather.weather_source_policy import build_weather_source_policy
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

REPORT_ROOT = Path("reports/sequence52/weather_batch_capture")
DEFAULT_CAPTURE_ROOT = Path("data/external/manual_captures/weather_market_mismatch")
NWS_FORECAST_URL = "https://api.weather.gov/gridpoints/OKX/34,45/forecast/hourly"
USER_AGENT = "quant-os-phase52-readonly estivanayramia@example.com"


def default_batch_orderbook_fixture() -> dict[str, Any]:
    return {
        "orderbooks": {
            "KXHIGHNY-26MAY12-B73.5": {
                "orderbook_fp": {
                    "yes_dollars": [["0.9200", "125.00"]],
                    "no_dollars": [["0.0500", "150.00"]],
                }
            },
            "KXHIGHNY-26MAY13-B72.5": {
                "orderbook_fp": {
                    "yes_dollars": [["0.0300", "120.00"]],
                    "no_dollars": [["0.9400", "160.00"]],
                }
            },
            "KXHIGHNY-26MAY14-B80.5": {
                "orderbook_fp": {
                    "yes_dollars": [["0.8500", "140.00"]],
                    "no_dollars": [["0.1200", "190.00"]],
                }
            },
        }
    }


def default_batch_forecast_fixture() -> dict[str, Any]:
    periods = []
    for day, temps in [(12, [70, 73, 74]), (13, [67, 68, 69]), (14, [78, 80, 79]), (15, [62, 64, 66])]:
        for hour, temp in enumerate(temps, start=13):
            periods.append(
                {
                    "startTime": f"2026-05-{day:02d}T{hour}:00:00-04:00",
                    "endTime": f"2026-05-{day:02d}T{hour + 1}:00:00-04:00",
                    "temperature": temp,
                    "temperatureUnit": "F",
                }
            )
    return {
        "properties": {
            "generatedAt": "2026-05-11T22:01:46+00:00",
            "updateTime": "2026-05-11T18:26:01+00:00",
            "periods": periods,
        }
    }


def run_weather_market_batch_capture(
    *,
    output_root: str | Path = ".",
    capture_root: str | Path = DEFAULT_CAPTURE_ROOT,
    run_id: str = "weather_market_batch_052",
    public_network_ok: bool = False,
    series_ticker: str = "KXHIGHNY",
    series_payload: dict[str, Any] | None = None,
    markets_payload: dict[str, Any] | None = None,
    orderbook_payload: dict[str, Any] | None = None,
    forecast_payload: dict[str, Any] | None = None,
    label_payloads: dict[str, str] | None = None,
    captured_at: str | None = None,
) -> dict[str, Any]:
    captured_at = captured_at or utc_now_string()
    has_payloads = any(
        payload is not None
        for payload in (
            series_payload,
            markets_payload,
            orderbook_payload,
            forecast_payload,
            label_payloads,
        )
    )
    if not public_network_ok and not has_payloads:
        payload = _disabled_payload(
            output_root=output_root,
            capture_root=capture_root,
            run_id=run_id,
            captured_at=captured_at,
        )
        payload["report_paths"] = _write_report(payload, output_root=output_root)
        return payload

    network_fetch_attempted = public_network_ok and not has_payloads
    if network_fetch_attempted:
        series_payload = _fetch_json(f"{KALSHI_BASE_URL}/series/{series_ticker}")
        query = urllib.parse.urlencode(
            {"series_ticker": series_ticker, "status": "settled", "limit": 100}
        )
        markets_payload = _fetch_json(f"{KALSHI_BASE_URL}/markets?{query}")
        forecast_payload = _fetch_json(NWS_FORECAST_URL)
    else:
        from quant_os.data.weather.weather_market_discovery import default_kalshi_series_fixture

        series_payload = series_payload or default_kalshi_series_fixture()
        markets_payload = markets_payload or default_resolved_markets_fixture()
        orderbook_payload = orderbook_payload or default_batch_orderbook_fixture()
        forecast_payload = forecast_payload or default_batch_forecast_fixture()
        label_payloads = label_payloads if label_payloads is not None else default_label_payloads_fixture()

    discovery = discover_resolved_weather_markets(
        series_payload=series_payload,
        markets_payload=markets_payload,
        captured_at=captured_at,
    )
    markets = discovery.get("markets", [])
    raw_markets_by_ticker = {
        str(market.get("ticker")): market for market in markets_payload.get("markets", [])
    }
    labels_payload = fetch_weather_resolution_labels(
        markets=[raw_markets_by_ticker[item["ticker"]] for item in markets if item["ticker"] in raw_markets_by_ticker],
        label_payloads=label_payloads or {},
        public_network_ok=False,
        allow_exchange_result_labels=network_fetch_attempted,
    )
    labels_by_ticker = {item["market_id"]: item for item in labels_payload["labels"]}

    root = Path(output_root) / Path(capture_root) / run_id
    market_records = []
    artifacts_accepted = 0
    rejected_artifacts: list[dict[str, Any]] = []
    for candidate in markets:
        ticker = candidate["ticker"]
        market = raw_markets_by_ticker[ticker]
        label = labels_by_ticker.get(ticker, {})
        orderbook = _orderbook_for_market(orderbook_payload, market)
        market_dir = root / str(ticker)
        artifacts = {
            "market_metadata": write_capture_artifact(
                market_dir / "market_metadata.json",
                {
                    "series": series_payload.get("series", series_payload),
                    "selected_market": market,
                    "discovery": candidate,
                    "captured_at": captured_at,
                    "network_fetch_attempted": network_fetch_attempted,
                },
                artifact_type="market_metadata",
                source_id="kalshi_public_market_data",
                captured_at=captured_at,
            ),
            "orderbook_snapshot": write_capture_artifact(
                market_dir / "orderbook_snapshot.json",
                {
                    "market_ticker": ticker,
                    "orderbook": orderbook,
                    "captured_at": captured_at,
                },
                artifact_type="orderbook_snapshot",
                source_id="kalshi_public_market_data",
                captured_at=captured_at,
            ),
            "forecast_snapshot": write_capture_artifact(
                market_dir / "forecast_snapshot.json",
                {
                    "forecast_url": NWS_FORECAST_URL,
                    "forecast": forecast_payload,
                    "captured_at": captured_at,
                },
                artifact_type="forecast_snapshot",
                source_id="nws_api",
                captured_at=captured_at,
            ),
            "resolution_snapshot": write_capture_artifact(
                market_dir / "resolution_snapshot.json",
                {
                    "status": label.get("status", "RESOLUTION_LABELS_MISSING"),
                    "market_ticker": ticker,
                    "resolution_value": label.get("resolution_value"),
                    "resolution_label": label.get("resolution_label", ""),
                    "resolution_ts": market.get("expected_expiration_time"),
                    "resolution_source": label.get("source_url"),
                    "issue_timestamp": label.get("issue_timestamp"),
                    "label_confidence": label.get("label_confidence", "NONE"),
                    "label_provenance_hash": label.get("provenance_hash"),
                    "blockers": label.get("blockers", []),
                },
                artifact_type="resolution_snapshot",
                source_id="nws_climatological_report",
                captured_at=captured_at,
            ),
        }
        artifacts_accepted += len(artifacts)
        market_records.append(
            {
                "ticker": ticker,
                "artifacts": artifacts,
                "proof_row_ready": bool(label.get("resolution_label")),
                "pending_label": not bool(label.get("resolution_label")),
                "blocked_by_missing_market_data": False,
                "blocked_by_ambiguous_mapping": candidate.get("source_matching_status")
                != "WEATHER_SOURCE_MATCHED",
                "source_quality": "PUBLIC_READ_ONLY_ALLOWED",
            }
        )

    manifest_payload = {
        "schema_version": "weather_market_batch_capture_manifest_v1",
        "sequence": "52",
        "run_id": run_id,
        "captured_at": captured_at,
        "capture_root": str(root).replace("\\", "/"),
        "read_only": True,
        "network_fetch_attempted": network_fetch_attempted,
        "public_network_ok": public_network_ok,
        "ci_network_dependency": False,
        "source_policy": build_weather_source_policy(),
        "discovery": discovery,
        "labels": labels_payload,
        "markets": market_records,
        "combined_provenance_hash": canonical_provenance_hash(
            {
                record["ticker"]: {
                    name: artifact["provenance_hash"]
                    for name, artifact in record["artifacts"].items()
                }
                for record in market_records
            }
        ),
        "rejected_artifacts": rejected_artifacts,
        "auth_headers_allowed": False,
        "browser_cookies_allowed": False,
        "wallet_signing_allowed": False,
        "order_placement_allowed": False,
        "order_cancellation_allowed": False,
        "anti_bot_evasion_allowed": False,
        "raw_captures_commit_allowed": False,
    }
    manifest = write_capture_artifact(
        root / "capture_manifest.json",
        manifest_payload,
        artifact_type="capture_manifest",
        source_id="local_manifest",
        captured_at=captured_at,
    )
    imported = import_weather_batch_capture(manifest["path"])
    proof_rows = imported["proof_rows_created"]
    pending_rows = imported["rows_pending_labels"]
    status = (
        "RESOLVED_WEATHER_BATCH_READY"
        if proof_rows
        else "RESOLUTION_LABELS_MISSING"
        if pending_rows
        else "WEATHER_MARKET_BACKFILL_BLOCKED"
    )
    payload = {
        "schema_version": "weather_market_batch_capture_v1",
        "sequence": "52",
        "status": status,
        "candidate_id": "pm_weather_forecast_market_mismatch",
        "run_id": run_id,
        "capture_root": str(root).replace("\\", "/"),
        "manifest_path": manifest["path"],
        "markets_discovered": len(markets),
        "markets_captured": len(market_records),
        "artifacts_accepted": artifacts_accepted,
        "artifacts_rejected": len(rejected_artifacts),
        "proof_rows_created": proof_rows,
        "rows_pending_labels": pending_rows,
        "rows_blocked_by_missing_market_data": imported["rows_blocked_by_missing_market_data"],
        "rows_blocked_by_ambiguous_mapping": imported["rows_blocked_by_ambiguous_mapping"],
        "source_quality_distribution": imported["source_quality_distribution"],
        "combined_provenance_hash": manifest_payload["combined_provenance_hash"],
        "read_only": True,
        "network_fetch_attempted": network_fetch_attempted,
        "ci_network_dependency": False,
        "auth_headers_allowed": False,
        "browser_cookies_allowed": False,
        "wallet_signing_allowed": False,
        "order_placement_allowed": False,
        "order_cancellation_allowed": False,
        "anti_bot_evasion_allowed": False,
        "raw_captures_commit_allowed": False,
        "blockers": [] if proof_rows else ["RESOLUTION_LABELS_MISSING"],
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
        **SOCIAL_INTAKE_SAFETY,
    }
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _orderbook_for_market(orderbook_payload: dict[str, Any] | None, market: dict[str, Any]) -> dict[str, Any]:
    ticker = str(market.get("ticker"))
    if orderbook_payload and "orderbooks" in orderbook_payload:
        found = orderbook_payload["orderbooks"].get(ticker)
        if found:
            return found
    if orderbook_payload and "orderbook_fp" in orderbook_payload:
        return orderbook_payload
    yes_bid = float(market.get("yes_bid_dollars") or 0.0)
    yes_ask = float(market.get("yes_ask_dollars") or 0.0)
    no_bid = max(1.0 - yes_ask, 0.0)
    return {
        "orderbook_fp": {
            "yes_dollars": [[f"{yes_bid:.4f}", str(market.get("yes_bid_size_fp") or "1.00")]],
            "no_dollars": [[f"{no_bid:.4f}", str(market.get("yes_ask_size_fp") or "1.00")]],
        }
    }


def _fetch_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT}, method="GET")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _disabled_payload(
    *,
    output_root: str | Path,
    capture_root: str | Path,
    run_id: str,
    captured_at: str,
) -> dict[str, Any]:
    root = Path(output_root) / Path(capture_root) / run_id
    return {
        "schema_version": "weather_market_batch_capture_v1",
        "sequence": "52",
        "status": "PUBLIC_NETWORK_DISABLED",
        "candidate_id": "pm_weather_forecast_market_mismatch",
        "run_id": run_id,
        "capture_root": str(root).replace("\\", "/"),
        "manifest_path": None,
        "markets_discovered": 0,
        "markets_captured": 0,
        "artifacts_accepted": 0,
        "artifacts_rejected": 0,
        "proof_rows_created": 0,
        "rows_pending_labels": 0,
        "rows_blocked_by_missing_market_data": 0,
        "rows_blocked_by_ambiguous_mapping": 0,
        "source_quality_distribution": {},
        "combined_provenance_hash": "",
        "read_only": True,
        "network_fetch_attempted": False,
        "ci_network_dependency": False,
        "auth_headers_allowed": False,
        "browser_cookies_allowed": False,
        "wallet_signing_allowed": False,
        "order_placement_allowed": False,
        "order_cancellation_allowed": False,
        "anti_bot_evasion_allowed": False,
        "raw_captures_commit_allowed": False,
        "blockers": ["PUBLIC_NETWORK_FLAG_OR_FIXTURE_PAYLOADS_REQUIRED_FOR_BATCH_CAPTURE"],
        "captured_at": captured_at,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
        **SOCIAL_INTAKE_SAFETY,
    }


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_weather_batch_capture.json"
    md_path = root / "latest_weather_batch_capture.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 52 Weather Batch Capture",
        "",
        "Batch public read-only weather-market capture. Raw captures stay ignored/local-only.",
        "",
        f"Status: {payload['status']}",
        f"Markets captured: {payload['markets_captured']}",
        f"Proof rows created: {payload['proof_rows_created']}",
        f"Rows pending labels: {payload['rows_pending_labels']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        f"Execution authority: {payload['execution_authority']}",
        "",
        "## Blockers",
    ]
    lines.extend(f"- {item}" for item in payload["blockers"] or ["None"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
