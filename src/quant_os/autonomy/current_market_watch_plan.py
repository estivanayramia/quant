from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.readiness.canary_readiness_common import safety_payload, write_json_markdown_report

REPORT_DIR = Path("reports/first_dollar_preflight/current_market_watch")


def build_current_market_watch_plan() -> dict[str, Any]:
    cli_command = "python -m quant_os.cli data current-weather-market-discovery --public-network-ok"
    return safety_payload(
        schema_version="current_market_watch_plan_v1",
        status="CURRENT_MARKET_WATCH_PLAN_READY",
        allowed_statuses=[
            "CURRENT_MARKET_WATCH_PLAN_READY",
            "CURRENT_MARKET_WATCH_PLAN_BLOCKED",
        ],
        data_only=True,
        public_read_only=True,
        check_interval_minutes=30,
        eligible_series_list=["KXHIGHNY", "KXHIGHAUS", "KXHIGHCHI", "KXHIGHMIA", "KXHIGHLAX"],
        exact_cli_command=cli_command,
        windows_task_scheduler_command=(
            'schtasks /Create /SC MINUTE /MO 30 /TN "QuantOSCurrentMarketWatch" '
            f'/TR "{cli_command}"'
        ),
        local_report_path="reports/first_dollar_preflight/current_market_discovery/latest_current_market_discovery.json",
        credentials_required=False,
        authenticated_requests_enabled=False,
        order_transmission_enabled=False,
        live_trading_enabled=False,
        api_keys_loaded=False,
        private_keys_loaded=False,
        blockers=[],
        next_action="Run the public read-only watcher until a current eligible weather market appears.",
    )


def write_current_market_watch_plan(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_current_market_watch_plan()
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_current_market_watch.json",
        md_name="latest_current_market_watch.md",
        title="Current Market Watch Plan",
        summary="Data-only public market watcher plan. No credentials, auth, live trading, orders, or cancels.",
    )
    return payload
