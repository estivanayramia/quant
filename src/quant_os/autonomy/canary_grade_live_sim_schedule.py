from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.autonomy.canary_grade_live_sim_common import RESUME_COMMAND, ROOT, canary_safe_payload
from quant_os.readiness.canary_readiness_common import write_json_markdown_report

REPORT_DIR = ROOT / "schedule"


def build_canary_grade_live_sim_schedule() -> dict[str, Any]:
    return canary_safe_payload(
        schema_version="canary_grade_live_sim_schedule_v1",
        status="CANARY_GRADE_LIVE_SIM_SCHEDULE_READY",
        data_only=True,
        powershell_command=(
            "PowerShell data-only resume: no credentials, no orders, no auth, no signing; "
            f"{RESUME_COMMAND}; stop on CANARY_GRADE_LIVE_SIM_PROFITABILITY_PROVEN "
            "or documented blocker"
        ),
        fixture_safe_smoke_command=".\\make.cmd canary-grade-live-sim-smoke",
        interval="5 minutes",
        max_runs=150,
        target_observation_count=1000,
        target_intent_count=300,
        target_completed_mark_count=150,
        stop_condition="CANARY_GRADE_LIVE_SIM_PROFITABILITY_PROVEN",
        report_paths=[
            "reports/canary_grade_live_sim/state/latest_state.json",
            "reports/canary_grade_live_sim/final/latest_canary_grade_live_sim_readiness.json",
            "reports/canary_grade_live_sim/manual_canary_packet/latest_manual_canary_packet.json",
        ],
        blockers=[],
        next_action="Run canary-grade live sim schedule/resume command.",
    )


def write_canary_grade_live_sim_schedule_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_canary_grade_live_sim_schedule()
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_schedule.json",
        md_name="latest_schedule.md",
        title="Canary-Grade Live Sim Schedule",
        summary="Data-only schedule for large-sample canary-grade fake-money simulation.",
    )
    return payload
