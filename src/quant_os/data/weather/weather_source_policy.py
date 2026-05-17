from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

REPORT_ROOT = Path("reports/sequence50/weather_source_policy")

PUBLIC_READ_ONLY_ALLOWED = "PUBLIC_READ_ONLY_ALLOWED"
PUBLIC_READ_ONLY_RATE_LIMITED = "PUBLIC_READ_ONLY_RATE_LIMITED"
MANUAL_CAPTURE_ALLOWED = "MANUAL_CAPTURE_ALLOWED"
PAID_OR_AUTH_REQUIRED = "PAID_OR_AUTH_REQUIRED"
UNSAFE_OR_BLOCKED = "UNSAFE_OR_BLOCKED"
UNKNOWN_REVIEW_REQUIRED = "UNKNOWN_REVIEW_REQUIRED"

ALLOWED_CLASSIFICATIONS = [
    PUBLIC_READ_ONLY_ALLOWED,
    PUBLIC_READ_ONLY_RATE_LIMITED,
    MANUAL_CAPTURE_ALLOWED,
    PAID_OR_AUTH_REQUIRED,
    UNSAFE_OR_BLOCKED,
    UNKNOWN_REVIEW_REQUIRED,
]

SOURCE_CLASSIFICATIONS = {
    "nws_api": PUBLIC_READ_ONLY_RATE_LIMITED,
    "iem_mos_historical_forecast": PUBLIC_READ_ONLY_RATE_LIMITED,
    "iem_nws_text_archive": PUBLIC_READ_ONLY_RATE_LIMITED,
    "noaa_ncei_noaaport_nwstg_text": PUBLIC_READ_ONLY_ALLOWED,
    "open_meteo_free_forecast": PUBLIC_READ_ONLY_RATE_LIMITED,
    "open_meteo_historical_forecast": PUBLIC_READ_ONLY_RATE_LIMITED,
    "official_noaa_station_public": PUBLIC_READ_ONLY_ALLOWED,
    "kalshi_public_market_data": PUBLIC_READ_ONLY_ALLOWED,
    "polymarket_gamma_public": PUBLIC_READ_ONLY_ALLOWED,
    "polymarket_clob_public_market_data": PUBLIC_READ_ONLY_ALLOWED,
    "manual_local_capture": MANUAL_CAPTURE_ALLOWED,
    "local_manual_capture": MANUAL_CAPTURE_ALLOWED,
    "open_meteo_paid_subscription": PAID_OR_AUTH_REQUIRED,
    "account_only_weather_vendor": PAID_OR_AUTH_REQUIRED,
    "paid_market_data_vendor": PAID_OR_AUTH_REQUIRED,
    "browser_cookie_capture": UNSAFE_OR_BLOCKED,
    "polymarket_order_endpoint": UNSAFE_OR_BLOCKED,
    "polymarket_cancel_endpoint": UNSAFE_OR_BLOCKED,
    "captcha_or_proxy_evasion": UNSAFE_OR_BLOCKED,
    "login_wall_scrape": UNSAFE_OR_BLOCKED,
    "wallet_or_signed_trading_endpoint": UNSAFE_OR_BLOCKED,
}


def classify_weather_source(source_id: str) -> str:
    return SOURCE_CLASSIFICATIONS.get(source_id, UNKNOWN_REVIEW_REQUIRED)


def build_weather_source_policy() -> dict[str, Any]:
    entries = [_source(source_id, status) for source_id, status in SOURCE_CLASSIFICATIONS.items()]
    return {
        "schema_version": "weather_source_policy_v1",
        "sequence": "50",
        "policy_status": "PUBLIC_READ_ONLY_SOURCE_POLICY_DEFINED",
        "allowed_classifications": ALLOWED_CLASSIFICATIONS,
        "sources": entries,
        "allowed_sources": [
            item
            for item in entries
            if item["classification"]
            in {PUBLIC_READ_ONLY_ALLOWED, PUBLIC_READ_ONLY_RATE_LIMITED, MANUAL_CAPTURE_ALLOWED}
        ],
        "blocked_sources": [
            item
            for item in entries
            if item["classification"] in {PAID_OR_AUTH_REQUIRED, UNSAFE_OR_BLOCKED}
        ],
        "unknown_review_required_status": UNKNOWN_REVIEW_REQUIRED,
        "source_policy_references": [
            {
                "source": "National Weather Service API",
                "url": "https://www.weather.gov/documentation/services-web-api",
                "policy_note": (
                    "Open public service; requires identifying User-Agent and has reasonable "
                    "rate limits."
                ),
            },
            {
                "source": "Open-Meteo Free API",
                "url": "https://open-meteo.com/en/terms",
                "policy_note": (
                    "Free tier is non-commercial, rate-limited, and CC-BY 4.0; commercial "
                    "use requires subscription."
                ),
            },
            {
                "source": "Polymarket market data",
                "url": "https://docs.polymarket.com/market-data/overview",
                "policy_note": (
                    "Public market data endpoints are allowed; authenticated trading/order "
                    "endpoints are blocked."
                ),
            },
        ],
        "public_read_only_only": True,
        "manual_capture_allowed": True,
        "paid_api_allowed": False,
        "auth_headers_allowed": False,
        "browser_cookies_allowed": False,
        "wallet_required": False,
        "wallet_signing_allowed": False,
        "order_endpoints_allowed": False,
        "order_placement_allowed": False,
        "order_cancellation_allowed": False,
        "anti_bot_evasion_allowed": False,
        "ci_network_dependency": False,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_weather_source_policy_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_weather_source_policy()
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _source(source_id: str, classification: str) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "classification": classification,
        "read_only": classification
        in {PUBLIC_READ_ONLY_ALLOWED, PUBLIC_READ_ONLY_RATE_LIMITED, MANUAL_CAPTURE_ALLOWED},
        "auth_required": classification == PAID_OR_AUTH_REQUIRED,
        "execution_authority": "NONE",
    }


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_weather_source_policy.json"
    md_path = root / "latest_weather_source_policy.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 50 Weather Source Policy",
        "",
        "Public/read-only source policy. No auth, cookies, wallets, order endpoints, or evasion.",
        "",
        f"Status: {payload['policy_status']}",
        f"Allowed sources: {len(payload['allowed_sources'])}",
        f"Blocked sources: {len(payload['blocked_sources'])}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        f"Execution authority: {payload['execution_authority']}",
        "",
        "## Allowed",
    ]
    lines.extend(
        f"- {item['source_id']}: {item['classification']}"
        for item in payload["allowed_sources"]
    )
    lines.extend(["", "## Blocked"])
    lines.extend(
        f"- {item['source_id']}: {item['classification']}"
        for item in payload["blocked_sources"]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}

