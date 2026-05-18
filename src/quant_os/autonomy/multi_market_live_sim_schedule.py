from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.autonomy.multi_market_live_sim_common import ROOT, safe_report_payload
from quant_os.readiness.canary_readiness_common import write_json_markdown_report

REPORT_DIR = ROOT / "schedule"


def build_multi_market_live_sim_schedule() -> dict[str, Any]:
    command = (
        "PowerShell data-only resume: no credentials, no auth, no signing; "
        ".\\make.cmd multi-market-live-sim-smoke; "
        "stop when MULTI_MARKET_LIVE_SIM_PROFITABILITY_PROVEN or human data boundary appears"
    )
    return safe_report_payload(
        schema_version="multi_market_live_sim_schedule_v1",
        status="MULTI_MARKET_LIVE_SIM_SCHEDULE_READY",
        allowed_statuses=["MULTI_MARKET_LIVE_SIM_SCHEDULE_READY"],
        data_only=True,
        powershell_command=command,
        market_family_order=[
            "crypto_spot",
            "weather_prediction_markets",
            "prediction_market_structural",
            "etf_equity",
        ],
        interval="5 minutes",
        max_runs=30,
        outcome_mark_recheck_interval="5 minutes",
        report_paths=[
            "reports/multi_market_live_sim/state/latest_state.json",
            "reports/multi_market_live_sim/router/latest_router.json",
            "reports/multi_market_live_sim/crypto_spot/latest_crypto_profitability.json",
            "reports/multi_market_live_sim/final/latest_multi_market_live_sim_profitability.json",
        ],
        stop_conditions=[
            "MULTI_MARKET_LIVE_SIM_PROFITABILITY_PROVEN",
            "HUMAN_DATA_OR_CREDENTIAL_BOUNDARY_REACHED",
        ],
        blockers=[],
        next_action="Run the data-only multi-market resume command.",
    )


def write_multi_market_live_sim_schedule_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_multi_market_live_sim_schedule()
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_schedule.json",
        md_name="latest_schedule.md",
        title="Multi-Market Live Sim Schedule",
        summary="Data-only resume plan for public-market fake-money simulation.",
    )
    return payload
