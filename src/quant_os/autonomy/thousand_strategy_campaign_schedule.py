from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.research.strategy_factory.campaign_common import (
    RESUME_COMMAND,
    safe_payload,
    write_json_md,
)


def write_thousand_strategy_campaign_schedule_report(
    *,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    command = (
        f"cd C:\\Users\\estiv\\quant; {RESUME_COMMAND}; "
        "fixture-safe smoke is no credentials, no orders, no auth, no live"
    )
    payload = safe_payload(
        status="THOUSAND_STRATEGY_CAMPAIGN_SCHEDULE_READY",
        data_only=True,
        powershell_command=command,
        batch_size=1000,
        target_variants=1000,
        target_sample_count=1000,
        target_intent_count=300,
        target_completed_marks=150,
        interval="manual_or_hourly_data_only",
        stop_condition=(
            "MONEY_WORTHY_CANARY_GRADE_PROFITABILITY_PROVEN and "
            "FIRST_TINY_MANUAL_CANARY_PACKET_READY"
        ),
        report_paths_expected=[
            "reports/thousand_strategy_campaign/state/latest_state.json",
            "reports/thousand_strategy_campaign/final/latest_money_worthy_readiness.json",
        ],
        no_credentials=True,
        no_orders=True,
        no_auth=True,
        no_live=True,
    )
    return write_json_md(
        payload,
        output_root=output_root,
        report_dir="schedule",
        json_name="latest_schedule.json",
        md_name="latest_schedule.md",
        title="Thousand Strategy Campaign Schedule",
        lines=[f"Status: {payload['status']}", f"Command: `{command}`"],
    )
