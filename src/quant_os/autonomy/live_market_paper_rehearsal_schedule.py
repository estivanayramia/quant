from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.readiness.canary_readiness_common import safety_payload, write_json_markdown_report

REPORT_DIR = Path("reports/live_market_paper_rehearsal/schedule")


def build_live_market_paper_rehearsal_schedule() -> dict[str, Any]:
    command = (
        "python -m quant_os.cli autonomy live-market-paper-observer --public-network-ok && "
        "python -m quant_os.cli autonomy live-market-paper-intents && "
        "python -m quant_os.cli autonomy live-market-fake-fill && "
        "python -m quant_os.cli autonomy live-market-paper-ledger && "
        "python -m quant_os.cli autonomy live-market-paper-reconciliation && "
        "python -m quant_os.cli readiness live-market-paper-rehearsal"
    )
    powershell_command = (
        "for ($i = 1; $i -le 8; $i++) { "
        "python -m quant_os.cli autonomy live-market-paper-observer --public-network-ok; "
        "if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; "
        "python -m quant_os.cli autonomy live-market-paper-intents; "
        "if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; "
        "python -m quant_os.cli autonomy live-market-fake-fill; "
        "if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; "
        "python -m quant_os.cli autonomy live-market-paper-ledger; "
        "if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; "
        "python -m quant_os.cli autonomy live-market-paper-reconciliation; "
        "if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; "
        "python -m quant_os.cli readiness live-market-paper-rehearsal; "
        "$status = (Get-Content reports/live_market_paper_rehearsal/final/latest_live_market_paper_rehearsal.json "
        "| ConvertFrom-Json).status; "
        "if ($status -eq 'LIVE_MARKET_PAPER_REHEARSAL_PASSED' -or $status -like '*BLOCKED_BY*') { break }; "
        "Start-Sleep -Seconds 1800 "
        "}"
    )
    return safety_payload(
        schema_version="live_market_paper_rehearsal_schedule_v1",
        status="LIVE_MARKET_PAPER_REHEARSAL_SCHEDULE_READY",
        allowed_statuses=[
            "LIVE_MARKET_PAPER_REHEARSAL_SCHEDULE_READY",
            "LIVE_MARKET_PAPER_REHEARSAL_SCHEDULE_BLOCKED",
        ],
        data_only=True,
        public_read_only=True,
        public_network_optional_flag="--public-network-ok",
        check_interval_minutes=30,
        max_runs=8,
        exact_resume_command=command,
        exact_powershell_command=powershell_command,
        windows_task_scheduler_command=(
            'schtasks /Create /SC MINUTE /MO 30 /TN "QuantOSLiveMarketPaperRehearsal" '
            f'/TR "{command}"'
        ),
        output_directory="reports/live_market_paper_rehearsal",
        stop_condition="Stop after readiness status LIVE_MARKET_PAPER_REHEARSAL_PASSED or any BLOCKED_BY_* status.",
        credentials_required=False,
        authenticated_requests_enabled=False,
        order_transmission_enabled=False,
        live_trading_enabled=False,
        api_keys_loaded=False,
        private_keys_loaded=False,
        blockers=[],
        next_action="Run the exact resume command for the next fake-money public-market rehearsal observation.",
    )


def write_live_market_paper_rehearsal_schedule_report(
    *,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    payload = build_live_market_paper_rehearsal_schedule()
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_schedule.json",
        md_name="latest_schedule.md",
        title="Live Market Paper Rehearsal Schedule",
        summary="Data-only watcher plan for repeated fake-money live-market paper observations.",
    )
    return payload
