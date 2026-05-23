from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.autonomy.live_market_sim_common import RESUME_COMMAND, sim_safety_payload
from quant_os.readiness.canary_readiness_common import write_json_markdown_report

REPORT_DIR = Path("reports/live_market_sim_profitability/schedule")


def build_live_market_sim_profitability_schedule() -> dict[str, Any]:
    powershell = (
        "$commands = @( "
        "@('python','-m','quant_os.cli','autonomy','live-market-profit-observer','--public-network-ok'), "
        "@('python','-m','quant_os.cli','autonomy','live-market-sim-intents'), "
        "@('python','-m','quant_os.cli','autonomy','live-market-sim-fill'), "
        "@('python','-m','quant_os.cli','autonomy','live-market-sim-ledger'), "
        "@('python','-m','quant_os.cli','autonomy','live-market-sim-outcomes','--public-network-ok'), "
        "@('python','-m','quant_os.cli','autonomy','live-market-sim-pnl'), "
        "@('python','-m','quant_os.cli','proving','live-market-sim-comparison'), "
        "@('python','-m','quant_os.cli','autonomy','live-market-sim-reconciliation'), "
        "@('python','-m','quant_os.cli','readiness','live-market-sim-profitability') "
        "); "
        "for ($i = 1; $i -le 20; $i++) { "
        "foreach ($cmd in $commands) { "
        "& $cmd[0] $cmd[1..($cmd.Count - 1)]; "
        "if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } "
        "}; "
        "$status = (Get-Content reports/live_market_sim_profitability/final/latest_live_market_sim_profitability.json "
        "| ConvertFrom-Json).status; "
        "if ($status -eq 'LIVE_MARKET_SIMULATED_PROFITABILITY_PROVEN' -or $status -eq 'LIVE_MARKET_SIMULATED_PROFITABILITY_NOT_PROVEN') { break }; "
        "Start-Sleep -Seconds 1800 "
        "}"
    )
    return sim_safety_payload(
        schema_version="live_market_sim_profitability_schedule_v1",
        status="LIVE_MARKET_SIM_PROFITABILITY_SCHEDULE_READY",
        allowed_statuses=["LIVE_MARKET_SIM_PROFITABILITY_SCHEDULE_READY", "LIVE_MARKET_SIM_PROFITABILITY_SCHEDULE_BLOCKED"],
        data_only=True,
        public_read_only=True,
        interval_minutes=30,
        max_runs=20,
        outcome_recheck_interval_minutes=30,
        exact_resume_command=RESUME_COMMAND,
        exact_powershell_command=powershell,
        report_paths=[
            "reports/live_market_sim_profitability/state/latest_state.json",
            "reports/live_market_sim_profitability/final/latest_live_market_sim_profitability.json",
        ],
        stop_conditions=[
            "LIVE_MARKET_SIMULATED_PROFITABILITY_PROVEN",
            "LIVE_MARKET_SIMULATED_PROFITABILITY_NOT_PROVEN",
        ],
        credentials_required=False,
        order_transmission_enabled=False,
        authenticated_requests_enabled=False,
        request_signing_enabled=False,
        blockers=[],
        next_action="Run exact resume command or schedule the data-only PowerShell loop.",
    )


def write_live_market_sim_profitability_schedule_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_live_market_sim_profitability_schedule()
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_schedule.json",
        md_name="latest_schedule.md",
        title="Live Market Simulated Profitability Schedule",
        summary="Data-only scheduler/resume loop for fake-money live-market simulated profitability.",
    )
    return payload
