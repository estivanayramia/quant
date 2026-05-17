from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.data.weather.weather_market_capture_artifacts import utc_now_string
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

REPORT_ROOT = Path("reports/sequence52/weather_pending_resolution")


def build_weather_pending_resolution_monitor(*, checked_at: str | None = None) -> dict[str, Any]:
    checked_at = checked_at or utc_now_string()
    pending = [
        {
            "market_id": "KXHIGHNY-26MAY15-T65",
            "event_id": "KXHIGHNY-26MAY15",
            "expected_resolution_source": "NWS Climatological Report, Central Park / OKX NYC",
            "source_url": "https://forecast.weather.gov/product.php?site=OKX&product=CLI&issuedby=NYC",
            "last_checked": checked_at,
            "status": "RESOLUTION_LABELS_MISSING",
            "recheck_command": "python -m quant_os.cli data weather-resolution-labels --public-network-ok",
        }
    ]
    return {
        "schema_version": "weather_pending_resolution_monitor_v1",
        "sequence": "52",
        "status": "RESOLUTION_LABELS_MISSING",
        "candidate_id": "pm_weather_forecast_market_mismatch",
        "pending_markets": pending,
        "pending_count": len(pending),
        "blockers": ["OFFICIAL_NWS_RESOLUTION_LABEL_NOT_AVAILABLE"],
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


def write_weather_pending_resolution_monitor_report(
    *,
    output_root: str | Path = ".",
    checked_at: str | None = None,
) -> dict[str, Any]:
    payload = build_weather_pending_resolution_monitor(checked_at=checked_at)
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_weather_pending_resolution.json"
    md_path = root / "latest_weather_pending_resolution.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 52 Weather Pending Resolution Monitor",
        "",
        "Tracks unresolved Phase 51 weather market labels without counting them as proof.",
        "",
        f"Status: {payload['status']}",
        f"Pending count: {payload['pending_count']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        f"Execution authority: {payload['execution_authority']}",
        "",
        "## Pending Markets",
    ]
    lines.extend(
        f"- {item['market_id']}: {item['status']} (`{item['recheck_command']}`)"
        for item in payload["pending_markets"]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
