from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.readiness.canary_readiness_common import (
    safety_payload,
    update_canary_state,
    write_json_markdown_report,
)

REPORT_DIR = Path("reports/canary_readiness/risk")


def evaluate_tiny_canary_risk(
    *,
    venue_minimum_exposure_usd: float = 1.0,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    envelope = {
        "max_canary_orders": 1,
        "max_contracts": 1,
        "max_nominal_exposure_usd": 1.0,
        "max_total_loss_usd": 1.0,
        "no_martingale": True,
        "no_averaging_down": True,
        "no_second_order": True,
        "no_automatic_retry": True,
        "no_autonomous_re_entry": True,
        "no_position_scaling": True,
        "no_overnight_expansion_beyond_contract_design": True,
        "manual_arming_required": True,
        "kill_switch_required": True,
        "post_canary_reconciliation_required": True,
    }
    blockers = []
    if venue_minimum_exposure_usd > envelope["max_nominal_exposure_usd"]:
        blockers.append("VENUE_MINIMUM_EXCEEDS_LIMIT")
    status = "TINY_CANARY_RISK_PASSED" if not blockers else "VENUE_MINIMUM_EXCEEDS_LIMIT"
    payload = safety_payload(
        schema_version="weather_tiny_canary_risk_v1",
        status=status,
        allowed_statuses=[
            "TINY_CANARY_RISK_PASSED",
            "TINY_CANARY_RISK_BLOCKED",
            "VENUE_MINIMUM_EXCEEDS_LIMIT",
            "RISK_ENVELOPE_INCOMPLETE",
        ],
        candidate_id="pm_weather_forecast_market_mismatch",
        risk_envelope=envelope,
        venue_minimum_exposure_usd=venue_minimum_exposure_usd,
        manual_arming_required=True,
        blockers=blockers,
        next_action="Run kill-switch proof." if status == "TINY_CANARY_RISK_PASSED" else "Human must review venue minimum before any arming.",
    )
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_tiny_canary_risk.json",
        md_name="latest_tiny_canary_risk.md",
        title="Weather Tiny Canary Risk",
        summary="Defines the tiny manual canary envelope without execution authority.",
    )
    update_canary_state(
        output_root=output_root,
        gate="risk",
        gate_status=status,
        evidence_paths=payload["report_paths"],
        gates_passed=["risk"] if status == "TINY_CANARY_RISK_PASSED" else [],
        gates_failed=[] if status == "TINY_CANARY_RISK_PASSED" else ["risk"],
        blocker=blockers[0] if blockers else None,
        next_action=payload["next_action"],
    )
    return payload


def write_weather_tiny_canary_risk_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    return evaluate_tiny_canary_risk(output_root=output_root)
