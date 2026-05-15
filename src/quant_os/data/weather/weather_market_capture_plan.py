from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.data.weather.weather_source_policy import build_weather_source_policy
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

REPORT_ROOT = Path("reports/sequence50/weather_capture_plan")
DEFAULT_CAPTURE_ROOT = Path("data/external/manual_captures/weather_market_mismatch")


def build_weather_market_capture_plan(
    *,
    capture_root: str | Path = DEFAULT_CAPTURE_ROOT,
    run_id: str = "weather_market_manual_050",
    manual_network_ok: bool = False,
    market_id: str | None = None,
    location: str = "operator_selected_location",
    variable: str = "temperature_max",
) -> dict[str, Any]:
    root = Path(capture_root) / run_id
    source_policy = build_weather_source_policy()
    has_market = bool(market_id)
    status = (
        "LOCAL_ONLY_CAPTURE_PLAN_READY"
        if has_market
        else "LOCAL_ONLY_CAPTURE_PLAN_READY_NEEDS_OPERATOR_MARKET"
    )
    return {
        "schema_version": "weather_market_capture_plan_v1",
        "sequence": "50",
        "candidate_id": "pm_weather_forecast_market_mismatch",
        "status": status,
        "manual_only": True,
        "read_only": True,
        "network_enabled": bool(manual_network_ok and has_market),
        "network_fetch_attempted": False,
        "ci_network_dependency": False,
        "auth_headers_allowed": False,
        "browser_cookies_allowed": False,
        "wallet_required": False,
        "wallet_signing_allowed": False,
        "order_endpoints_allowed": False,
        "order_placement_allowed": False,
        "order_cancellation_allowed": False,
        "paid_api_allowed": False,
        "anti_bot_evasion_allowed": False,
        "raw_captures_commit_allowed": False,
        "tiny_sanitized_fixtures_allowed": True,
        "capture_root": str(root).replace("\\", "/"),
        "forecast_source": "nws_api_or_open_meteo_free_forecast",
        "forecast_timestamp": "record source published/valid/issued timestamp in UTC",
        "target_weather_variable": variable,
        "location": location,
        "market_id": market_id or "operator_must_select_public_market_id",
        "bucket_range_rules": [
            "map market rule text to inclusive/exclusive weather bucket boundaries",
            "record unit, timezone, station/location, and resolution source",
        ],
        "market_implied_probability": (
            "derive from public outcome price, midpoint, or best bid/ask snapshot"
        ),
        "price_orderbook_snapshot": {
            "required_fields": [
                "market_id",
                "token_id_or_outcome",
                "best_bid",
                "best_ask",
                "midpoint",
                "spread",
                "liquidity",
                "orderbook_ts",
            ],
        },
        "resolution_source": "official_station_or_market_resolution_public_label",
        "label_timestamp": "record when resolution was known publicly in UTC",
        "no_lookahead_alignment": [
            "forecast_ts <= known_at_ts <= orderbook_ts",
            "resolution_ts must be after decision/orderbook timestamp",
            "proof rows require real labels and source-quality separation",
        ],
        "expected_local_files": {
            "source_manifest": str(root / "source_manifest.json").replace("\\", "/"),
            "forecast_snapshot": str(root / "forecast_snapshot.json").replace("\\", "/"),
            "market_snapshot": str(root / "market_snapshot.json").replace("\\", "/"),
            "orderbook_snapshot": str(root / "orderbook_snapshot.json").replace("\\", "/"),
            "resolution_label": str(root / "resolution_label.json").replace("\\", "/"),
            "reduced_fixture": str(root / "reduced_fixture.json").replace("\\", "/"),
        },
        "allowed_public_sources": source_policy["allowed_sources"],
        "rejected_sources": source_policy["blocked_sources"],
        "operator_instructions": [
            "Select one resolved or soon-to-resolve public weather prediction market.",
            "Capture only public forecast and market-data endpoints with local timestamps.",
            "Write raw captures under data/external/manual_captures/weather_market_mismatch/.",
            "Commit only tiny sanitized fixture rows marked fixture_only and not proof.",
            "If market, forecast, or resolution source policy is ambiguous, stop as blocked.",
        ],
        "exact_next_commands": [
            (
                "python -m quant_os.cli data weather-market-capture-plan "
                "--market-id <public_market_id> --manual-network-ok"
            ),
            (
                "python -m quant_os.cli proving weather-market-paper-proving "
                "--fixture-path <tiny_sanitized_fixture>"
            ),
            "python -m quant_os.cli readiness weather-market-data-readiness",
        ],
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_weather_market_capture_plan(
    *,
    output_root: str | Path = ".",
    capture_root: str | Path = DEFAULT_CAPTURE_ROOT,
    run_id: str = "weather_market_manual_050",
    manual_network_ok: bool = False,
    market_id: str | None = None,
) -> dict[str, Any]:
    payload = build_weather_market_capture_plan(
        capture_root=capture_root,
        run_id=run_id,
        manual_network_ok=manual_network_ok,
        market_id=market_id,
    )
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_weather_capture_plan.json"
    md_path = root / "latest_weather_capture_plan.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 50 Weather Market Capture Plan",
        "",
        "Local-only read-only capture plan. Raw captures stay ignored/local-only.",
        "",
        f"Status: {payload['status']}",
        f"Manual only: {payload['manual_only']}",
        f"Read-only: {payload['read_only']}",
        f"Network enabled: {payload['network_enabled']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        f"Execution authority: {payload['execution_authority']}",
        "",
        "## Required Local Files",
    ]
    lines.extend(f"- {key}: {value}" for key, value in payload["expected_local_files"].items())
    lines.extend(["", "## Next Commands"])
    lines.extend(f"- `{item}`" for item in payload["exact_next_commands"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}

