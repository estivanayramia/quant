from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.research.lane_selection.relentless_profit_campaign_models import CAMPAIGN_SAFETY

REPORT_ROOT = Path("reports/profit_campaign/forward_capture")


def build_forward_capture_plan() -> dict[str, Any]:
    command = (
        'schtasks /Create /TN "QuantOS Weather Forward Capture" /SC HOURLY /MO 1 '
        '/TR "cmd /c cd /d C:\\Users\\estiv\\quant && '
        'python -m quant_os.cli data weather-market-batch-capture --public-network-ok" /F'
    )
    return {
        "schema_version": "forward_capture_plan_v1",
        "status": "FORWARD_CAPTURE_PLAN_READY",
        "lane_id": "pm_weather_forecast_market_mismatch",
        "data_only": True,
        "purpose": "Collect timestamped public weather forecast/orderbook snapshots forward in time.",
        "why_needed": [
            "Historical issue-time weather forecast snapshots aligned before market close are missing.",
            "Realized weather or resolution values cannot be used as forecasts.",
        ],
        "capture_targets": [
            "public prediction-market metadata",
            "public orderbook snapshot",
            "public NWS forecast snapshot with issue time",
            "later public resolution label",
        ],
        "candidate_public_archives_for_source_review": [
            {
                "name": "Iowa Environmental Mesonet NWS Text Archives",
                "url": "https://mesonet3.agron.iastate.edu/nws/text.php",
                "review_status": "CANDIDATE_PUBLIC_ISSUE_TIME_ARCHIVE_NOT_YET_PROOF",
                "notes": "Provides issued NWS text products with UTC product identifiers.",
            },
            {
                "name": "NOAA NCEI NOAAPort NWSTG Text Products",
                "url": "https://www.ncei.noaa.gov/access/metadata/landing-page/bin/iso?id=gov.noaa.ncdc%3AC00610",
                "review_status": "CANDIDATE_PUBLIC_TEXT_PRODUCT_ARCHIVE_NOT_YET_PROOF",
                "notes": "NOAA metadata lists archived NWS Telecommunications Gateway text products.",
            },
            {
                "name": "Open-Meteo Historical Forecast API",
                "url": "https://open-meteo.com/en/docs/historical-forecast-api",
                "review_status": "CANDIDATE_MODEL_FORECAST_ARCHIVE_TERMS_REVIEW_REQUIRED",
                "notes": "Historical forecast and prior model-run data may help source forecasts without realized weather substitution.",
            },
        ],
        "windows_task_scheduler_command": command,
        "safe_manual_command": (
            "python -m quant_os.cli data weather-market-batch-capture --public-network-ok"
        ),
        "continues_elsewhere": True,
        "live_ready": False,
        "canary_ready": False,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
        **CAMPAIGN_SAFETY,
    }


def write_forward_capture_plan(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_forward_capture_plan()
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_forward_capture_plan.json"
    md_path = root / "latest_forward_capture_plan.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Forward Capture Plan",
        "",
        "Data-only capture plan. No trading, orders, credentials, wallets, or live authority.",
        "",
        f"Status: {payload['status']}",
        f"Lane: {payload['lane_id']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        f"Execution authority: {payload['execution_authority']}",
        "",
        "## Windows Task Scheduler Command",
        f"`{payload['windows_task_scheduler_command']}`",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
