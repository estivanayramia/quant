from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path
from typing import Any

from quant_os.data.weather.weather_market_capture_artifacts import canonical_provenance_hash
from quant_os.data.weather.weather_resolved_market_discovery import (
    default_resolved_markets_fixture,
)
from quant_os.data.weather.weather_source_matching import match_weather_source_to_market
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

REPORT_ROOT = Path("reports/sequence52/weather_resolution_labels")
DEFAULT_SOURCE_URL = "https://forecast.weather.gov/product.php?site=OKX&product=CLI&issuedby=NYC"
USER_AGENT = "quant-os-phase52-readonly estivanayramia@example.com"


def default_label_payloads_fixture() -> dict[str, str]:
    return {
        "KXHIGHNY-26MAY12-B73.5": "CLIMATE REPORT\nMAXIMUM 73\nISSUED 1200 AM EDT MAY 13 2026\n",
        "KXHIGHNY-26MAY13-B72.5": "CLIMATE REPORT\nMAXIMUM 68\nISSUED 1200 AM EDT MAY 14 2026\n",
        "KXHIGHNY-26MAY14-B80.5": "CLIMATE REPORT\nMAXIMUM 80\nISSUED 1200 AM EDT MAY 15 2026\n",
        "KXHIGHNY-26MAY15-T65": "",
    }


def fetch_weather_resolution_labels(
    *,
    markets: list[dict[str, Any]] | None = None,
    label_payloads: dict[str, str] | None = None,
    public_network_ok: bool = False,
    source_url: str = DEFAULT_SOURCE_URL,
    allow_exchange_result_labels: bool = False,
) -> dict[str, Any]:
    markets = markets or default_resolved_markets_fixture()["markets"]
    label_payloads = label_payloads if label_payloads is not None else default_label_payloads_fixture()
    labels = []
    network_fetch_attempted = False
    for market in markets:
        text = label_payloads.get(str(market.get("ticker")), "")
        if public_network_ok and not text:
            text = _fetch_text(source_url)
            network_fetch_attempted = True
        labels.append(
            parse_high_temp_resolution_label(
                market=market,
                cli_text=text,
                source_url=source_url,
                allow_exchange_result_label=allow_exchange_result_labels,
            )
        )
    available = [item for item in labels if item["status"] == "RESOLUTION_LABEL_AVAILABLE"]
    ambiguous = [item for item in labels if item["status"] == "RESOLUTION_LABEL_AMBIGUOUS"]
    if available:
        status = "RESOLUTION_LABELS_AVAILABLE"
        blockers: list[str] = []
    elif ambiguous:
        status = "RESOLUTION_LABELS_AMBIGUOUS"
        blockers = ["AMBIGUOUS_RESOLUTION_LABELS"]
    else:
        status = "RESOLUTION_LABELS_MISSING"
        blockers = ["NO_PUBLIC_RESOLUTION_LABELS_AVAILABLE"]
    return {
        "schema_version": "weather_resolution_labels_v1",
        "sequence": "52",
        "status": status,
        "candidate_id": "pm_weather_forecast_market_mismatch",
        "label_count": len(labels),
        "available_label_count": len(available),
        "ambiguous_label_count": len(ambiguous),
        "missing_label_count": len(labels) - len(available) - len(ambiguous),
        "labels": labels,
        "blockers": blockers,
        "network_fetch_attempted": network_fetch_attempted,
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


def parse_high_temp_resolution_label(
    *,
    market: dict[str, Any],
    cli_text: str,
    source_url: str,
    allow_exchange_result_label: bool = False,
) -> dict[str, Any]:
    source_match = match_weather_source_to_market(market, {"settlement_sources": [{"url": source_url}]})
    blockers = []
    if source_match["variable"] != "temperature_max_f":
        blockers.append("UNSUPPORTED_WEATHER_VARIABLE")
    observed = _observed_max_temp(cli_text)
    if observed is None and not cli_text and allow_exchange_result_label:
        exchange_result = str(market.get("result") or "").upper()
        exchange_value = market.get("expiration_value")
        if exchange_result in {"YES", "NO"} and exchange_value not in {None, ""}:
            return _label_payload(
                market=market,
                status="RESOLUTION_LABEL_AVAILABLE",
                observed_value=float(exchange_value),
                resolution_label="IN_BUCKET" if exchange_result == "YES" else "OUT_OF_BUCKET",
                source_url=source_url,
                issue_timestamp=_issue_timestamp(cli_text),
                blockers=[],
                label_confidence="MEDIUM_PUBLIC_EXCHANGE_RESULT",
                cli_text=cli_text or json.dumps(
                    {
                        "result": exchange_result,
                        "expiration_value": exchange_value,
                        "ticker": market.get("ticker"),
                    },
                    sort_keys=True,
                ),
            )
    if observed is None:
        blockers.append("OBSERVED_MAX_TEMP_MISSING")
    if not source_url:
        blockers.append("SOURCE_URL_MISSING")
    if blockers:
        status = "RESOLUTION_LABELS_MISSING" if "OBSERVED_MAX_TEMP_MISSING" in blockers and not cli_text else "RESOLUTION_LABEL_AMBIGUOUS"
        return _label_payload(
            market=market,
            status=status,
            observed_value=None,
            resolution_label="",
            source_url=source_url,
            issue_timestamp=_issue_timestamp(cli_text),
            blockers=blockers,
            label_confidence="NONE",
            cli_text=cli_text,
        )
    label = "IN_BUCKET" if _bucket_contains(float(observed), source_match["bucket_range"]) else "OUT_OF_BUCKET"
    return _label_payload(
        market=market,
        status="RESOLUTION_LABEL_AVAILABLE",
        observed_value=float(observed),
        resolution_label=label,
        source_url=source_url,
        issue_timestamp=_issue_timestamp(cli_text),
        blockers=[],
        label_confidence="HIGH",
        cli_text=cli_text,
    )


def write_weather_resolution_labels_report(
    *,
    output_root: str | Path = ".",
    markets: list[dict[str, Any]] | None = None,
    label_payloads: dict[str, str] | None = None,
    public_network_ok: bool = False,
) -> dict[str, Any]:
    payload = fetch_weather_resolution_labels(
        markets=markets,
        label_payloads=label_payloads,
        public_network_ok=public_network_ok,
    )
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _label_payload(
    *,
    market: dict[str, Any],
    status: str,
    observed_value: float | None,
    resolution_label: str,
    source_url: str,
    issue_timestamp: str | None,
    blockers: list[str],
    label_confidence: str,
    cli_text: str,
) -> dict[str, Any]:
    return {
        "market_id": market.get("ticker"),
        "event_id": market.get("event_ticker"),
        "status": status,
        "resolution_value": observed_value,
        "resolution_label": resolution_label,
        "source_url": source_url,
        "issue_timestamp": issue_timestamp,
        "provenance_hash": canonical_provenance_hash(
            {"market": market.get("ticker"), "source_url": source_url, "cli_text": cli_text}
        ),
        "label_confidence": label_confidence,
        "blockers": blockers,
        "guessed_label": False,
    }


def _observed_max_temp(text: str) -> float | None:
    match = re.search(r"\bMAXIMUM\s+(-?\d+(?:\.\d+)?)\b", text, flags=re.IGNORECASE)
    if not match:
        return None
    return float(match.group(1))


def _issue_timestamp(text: str) -> str | None:
    match = re.search(r"ISSUED\s+([^\n]+)", text, flags=re.IGNORECASE)
    return match.group(1).strip() if match else None


def _bucket_contains(value: float, bucket_range: str) -> bool:
    parts = bucket_range.split("_")
    if bucket_range.startswith("greater_than_"):
        return value > float(parts[2])
    if bucket_range.startswith("less_than_"):
        return value < float(parts[2])
    if "_to_" in bucket_range:
        return float(parts[0]) <= value <= float(parts[2])
    return False


def _fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT}, method="GET")
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_weather_resolution_labels.json"
    md_path = root / "latest_weather_resolution_labels.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 52 Weather Resolution Labels",
        "",
        "Parses objective public weather labels. Ambiguous or missing labels do not count.",
        "",
        f"Status: {payload['status']}",
        f"Available labels: {payload['available_label_count']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        f"Execution authority: {payload['execution_authority']}",
        "",
        "## Blockers",
    ]
    lines.extend(f"- {item}" for item in payload["blockers"] or ["None"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
