from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from quant_os.data.weather.weather_market_capture_artifacts import (
    canonical_provenance_hash,
    load_capture_artifact,
    utc_now_string,
    write_capture_artifact,
)
from quant_os.data.weather.weather_market_discovery import (
    default_kalshi_markets_fixture,
    default_kalshi_series_fixture,
    discover_weather_markets,
)
from quant_os.data.weather.weather_source_matching import match_weather_source_to_market
from quant_os.data.weather.weather_source_policy import build_weather_source_policy
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

REPORT_ROOT = Path("reports/sequence51/weather_capture")
DEFAULT_CAPTURE_ROOT = Path("data/external/manual_captures/weather_market_mismatch")
KALSHI_BASE_URL = "https://external-api.kalshi.com/trade-api/v2"
NWS_FORECAST_URL = "https://api.weather.gov/gridpoints/OKX/34,45/forecast/hourly"
USER_AGENT = "quant-os-phase51-readonly estivanayramia@example.com"


def default_orderbook_fixture() -> dict[str, Any]:
    return {
        "orderbook_fp": {
            "yes_dollars": [["0.2700", "614.00"], ["0.3800", "1.00"]],
            "no_dollars": [["0.4000", "616.40"], ["0.5900", "6.00"]],
        }
    }


def default_forecast_fixture() -> dict[str, Any]:
    return {
        "properties": {
            "generatedAt": "2026-05-15T22:01:46+00:00",
            "updateTime": "2026-05-15T18:26:01+00:00",
            "periods": [
                {
                    "startTime": "2026-05-16T09:00:00-04:00",
                    "endTime": "2026-05-16T10:00:00-04:00",
                    "temperature": 75,
                    "temperatureUnit": "F",
                },
                {
                    "startTime": "2026-05-16T15:00:00-04:00",
                    "endTime": "2026-05-16T16:00:00-04:00",
                    "temperature": 79,
                    "temperatureUnit": "F",
                },
            ],
        }
    }


def run_weather_market_public_capture(
    *,
    output_root: str | Path = ".",
    capture_root: str | Path = DEFAULT_CAPTURE_ROOT,
    run_id: str = "weather_market_manual_051",
    public_network_ok: bool = False,
    series_ticker: str = "KXHIGHNY",
    series_payload: dict[str, Any] | None = None,
    markets_payload: dict[str, Any] | None = None,
    orderbook_payload: dict[str, Any] | None = None,
    forecast_payload: dict[str, Any] | None = None,
    captured_at: str | None = None,
) -> dict[str, Any]:
    captured_at = captured_at or utc_now_string()
    has_fixture_payloads = any(
        payload is not None
        for payload in (series_payload, markets_payload, orderbook_payload, forecast_payload)
    )
    if not public_network_ok and not has_fixture_payloads:
        payload = _disabled_payload(
            output_root=output_root,
            capture_root=capture_root,
            run_id=run_id,
            captured_at=captured_at,
        )
        payload["report_paths"] = _write_report(payload, output_root=output_root)
        return payload

    network_fetch_attempted = public_network_ok and not has_fixture_payloads
    if network_fetch_attempted:
        series_payload = _fetch_json(f"{KALSHI_BASE_URL}/series/{series_ticker}")
        query = urllib.parse.urlencode(
            {"series_ticker": series_ticker, "status": "open", "limit": 100}
        )
        markets_payload = _fetch_json(f"{KALSHI_BASE_URL}/markets?{query}")
    else:
        series_payload = series_payload or default_kalshi_series_fixture()
        markets_payload = markets_payload or default_kalshi_markets_fixture()

    discovery = discover_weather_markets(
        series_payload=series_payload,
        markets_payload=markets_payload,
        captured_at=captured_at,
    )
    selected = discovery.get("selected_market")
    if not selected:
        payload = _blocked_payload(
            status="MARKET_DATA_CAPTURE_BLOCKED",
            blockers=discovery["blockers"],
            output_root=output_root,
            capture_root=capture_root,
            run_id=run_id,
            captured_at=captured_at,
            network_fetch_attempted=network_fetch_attempted,
        )
        payload["report_paths"] = _write_report(payload, output_root=output_root)
        return payload

    market = _market_by_ticker(markets_payload, selected["ticker"])
    series = series_payload.get("series", series_payload)
    source_match = match_weather_source_to_market(market, series)
    if source_match["status"] != "WEATHER_SOURCE_MATCHED":
        payload = _blocked_payload(
            status="WEATHER_DATA_CAPTURE_BLOCKED",
            blockers=source_match["blockers"],
            output_root=output_root,
            capture_root=capture_root,
            run_id=run_id,
            captured_at=captured_at,
            network_fetch_attempted=network_fetch_attempted,
        )
        payload["report_paths"] = _write_report(payload, output_root=output_root)
        return payload

    if network_fetch_attempted:
        orderbook_payload = _fetch_json(
            f"{KALSHI_BASE_URL}/markets/{selected['ticker']}/orderbook"
        )
        forecast_payload = _fetch_json(NWS_FORECAST_URL, user_agent=USER_AGENT)
    else:
        orderbook_payload = orderbook_payload or default_orderbook_fixture()
        forecast_payload = forecast_payload or default_forecast_fixture()

    root = Path(output_root) / Path(capture_root) / run_id
    source_policy = build_weather_source_policy()
    market_metadata = {
        "series": series,
        "selected_market": market,
        "discovery": discovery,
        "source_matching": source_match,
        "captured_at": captured_at,
        "network_fetch_attempted": network_fetch_attempted,
    }
    resolution_snapshot = _resolution_snapshot(market=market, source_match=source_match)
    artifacts = {
        "market_metadata": write_capture_artifact(
            root / "market_metadata.json",
            market_metadata,
            artifact_type="market_metadata",
            source_id="kalshi_public_market_data",
            captured_at=captured_at,
        ),
        "orderbook_snapshot": write_capture_artifact(
            root / "orderbook_snapshot.json",
            {
                "market_ticker": selected["ticker"],
                "orderbook": orderbook_payload,
                "captured_at": captured_at,
            },
            artifact_type="orderbook_snapshot",
            source_id="kalshi_public_market_data",
            captured_at=captured_at,
        ),
        "forecast_snapshot": write_capture_artifact(
            root / "forecast_snapshot.json",
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
            root / "resolution_snapshot.json",
            resolution_snapshot,
            artifact_type="resolution_snapshot",
            source_id="nws_climatological_report",
            captured_at=captured_at,
        ),
    }
    manifest_payload = {
        "schema_version": "weather_market_capture_manifest_v1",
        "sequence": "51",
        "run_id": run_id,
        "captured_at": captured_at,
        "capture_root": str(root).replace("\\", "/"),
        "read_only": True,
        "network_fetch_attempted": network_fetch_attempted,
        "public_network_ok": public_network_ok,
        "ci_network_dependency": False,
        "source_policy": source_policy,
        "source_policy_verdicts": {
            key: value["source_id"] for key, value in artifacts.items()
        },
        "artifacts": artifacts,
        "combined_provenance_hash": canonical_provenance_hash(
            {key: value["provenance_hash"] for key, value in artifacts.items()}
        ),
        "rejected_artifacts": [],
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
    payload = {
        "schema_version": "weather_market_public_capture_v1",
        "sequence": "51",
        "status": (
            "PUBLIC_READ_ONLY_CAPTURE_READY"
            if resolution_snapshot["resolution_label"]
            else "PUBLIC_READ_ONLY_CAPTURED_RESOLUTION_PENDING"
        ),
        "candidate_id": "pm_weather_forecast_market_mismatch",
        "run_id": run_id,
        "capture_root": str(root).replace("\\", "/"),
        "manifest_path": manifest["path"],
        "artifacts": artifacts,
        "selected_market": selected,
        "source_matching_status": source_match["status"],
        "resolution_status": resolution_snapshot["status"],
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
        "blockers": ["RESOLUTION_LABELS_MISSING"]
        if not resolution_snapshot["resolution_label"]
        else [],
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
        **SOCIAL_INTAKE_SAFETY,
    }
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def load_capture_manifest(path: str | Path) -> dict[str, Any]:
    return load_capture_artifact(path)["payload"]


def _fetch_json(url: str, *, user_agent: str | None = None) -> dict[str, Any]:
    headers = {"User-Agent": user_agent or USER_AGENT}
    request = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _market_by_ticker(markets_payload: dict[str, Any], ticker: str) -> dict[str, Any]:
    for market in markets_payload.get("markets", []):
        if market.get("ticker") == ticker:
            return market
    raise ValueError(f"selected market not found in payload: {ticker}")


def _resolution_snapshot(*, market: dict[str, Any], source_match: dict[str, Any]) -> dict[str, Any]:
    label = str(market.get("result") or "").upper()
    value = market.get("expiration_value") or None
    if label in {"YES", "NO"}:
        resolution_label = "IN_BUCKET" if label == "YES" else "OUT_OF_BUCKET"
        status = "RESOLUTION_LABEL_AVAILABLE"
    else:
        resolution_label = ""
        status = "RESOLUTION_PENDING"
    return {
        "status": status,
        "market_ticker": market.get("ticker"),
        "resolution_value": value,
        "resolution_label": resolution_label,
        "resolution_ts": source_match.get("resolution_time"),
        "resolution_source": source_match.get("resolution_source"),
    }


def _disabled_payload(
    *,
    output_root: str | Path,
    capture_root: str | Path,
    run_id: str,
    captured_at: str,
) -> dict[str, Any]:
    root = Path(output_root) / Path(capture_root) / run_id
    return {
        "schema_version": "weather_market_public_capture_v1",
        "sequence": "51",
        "status": "PUBLIC_NETWORK_DISABLED",
        "candidate_id": "pm_weather_forecast_market_mismatch",
        "run_id": run_id,
        "capture_root": str(root).replace("\\", "/"),
        "manifest_path": None,
        "artifacts": {},
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
        "blockers": ["PUBLIC_NETWORK_FLAG_REQUIRED_FOR_REAL_CAPTURE"],
        "captured_at": captured_at,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
        **SOCIAL_INTAKE_SAFETY,
    }


def _blocked_payload(
    *,
    status: str,
    blockers: list[str],
    output_root: str | Path,
    capture_root: str | Path,
    run_id: str,
    captured_at: str,
    network_fetch_attempted: bool,
) -> dict[str, Any]:
    payload = _disabled_payload(
        output_root=output_root,
        capture_root=capture_root,
        run_id=run_id,
        captured_at=captured_at,
    )
    payload.update(
        {
            "status": status,
            "blockers": blockers,
            "network_fetch_attempted": network_fetch_attempted,
        }
    )
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_weather_capture.json"
    md_path = root / "latest_weather_capture.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 51 Weather Public Capture",
        "",
        "Public read-only capture. Raw artifacts stay under ignored local capture roots.",
        "",
        f"Status: {payload['status']}",
        f"Run ID: {payload['run_id']}",
        f"Network fetch attempted: {payload['network_fetch_attempted']}",
        f"Manifest: {payload.get('manifest_path')}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        f"Execution authority: {payload['execution_authority']}",
        "",
        "## Blockers",
    ]
    lines.extend(f"- {item}" for item in payload.get("blockers", []) or ["None"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
