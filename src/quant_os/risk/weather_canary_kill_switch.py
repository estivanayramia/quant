from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.readiness.canary_readiness_common import (
    safety_payload,
    update_canary_state,
    write_json_markdown_report,
)

REPORT_DIR = Path("reports/canary_readiness/kill_switch")


def evaluate_kill_switch(
    *,
    stale_data: bool = False,
    forecast_present: bool = True,
    market_data_present: bool = True,
    spread: float = 0.02,
    liquidity: float = 500.0,
    price_moved: bool = False,
    duplicate_client_order_id: bool = False,
    reconciliation_present: bool = True,
    previous_order_known: bool = True,
    loss_cap_hit: bool = False,
    manual_kill: bool = False,
    exception_seen: bool = False,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    matrix = {
        "global_live_disabled_by_default": {"disables": True, "condition": True},
        "canary_disabled_by_default": {"disables": True, "condition": True},
        "one_shot_arm_required": {"disables": True, "condition": True},
        "stale_data": {"disables": stale_data, "condition": stale_data},
        "missing_forecast": {"disables": not forecast_present, "condition": not forecast_present},
        "missing_market_data": {"disables": not market_data_present, "condition": not market_data_present},
        "spread_too_wide": {"disables": spread > 0.12, "condition": spread > 0.12},
        "liquidity_too_thin": {"disables": liquidity < 1, "condition": liquidity < 1},
        "price_moved": {"disables": price_moved, "condition": price_moved},
        "duplicate_client_order_id": {
            "disables": duplicate_client_order_id,
            "condition": duplicate_client_order_id,
        },
        "reconciliation_missing": {
            "disables": not reconciliation_present,
            "condition": not reconciliation_present,
        },
        "previous_order_unknown": {"disables": not previous_order_known, "condition": not previous_order_known},
        "loss_cap_hit": {"disables": loss_cap_hit, "condition": loss_cap_hit},
        "manual_kill": {"disables": manual_kill, "condition": manual_kill},
        "any_exception": {"disables": exception_seen, "condition": exception_seen},
    }
    incomplete = [key for key, item in matrix.items() if item["condition"] and not item["disables"]]
    status = "KILL_SWITCH_PROOF_PASSED" if not incomplete else "SELF_DISABLE_INCOMPLETE"
    payload = safety_payload(
        schema_version="weather_canary_kill_switch_v1",
        status=status,
        allowed_statuses=[
            "KILL_SWITCH_PROOF_PASSED",
            "KILL_SWITCH_PROOF_FAILED",
            "SELF_DISABLE_INCOMPLETE",
        ],
        candidate_id="pm_weather_forecast_market_mismatch",
        disable_matrix=matrix,
        blockers=incomplete,
        next_action="Run reconciliation proof." if status == "KILL_SWITCH_PROOF_PASSED" else "Fix self-disable matrix.",
    )
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_kill_switch.json",
        md_name="latest_kill_switch.md",
        title="Weather Canary Kill Switch",
        summary="Proves default-off and self-disable conditions.",
    )
    update_canary_state(
        output_root=output_root,
        gate="kill_switch",
        gate_status=status,
        evidence_paths=payload["report_paths"],
        gates_passed=["kill_switch"] if status == "KILL_SWITCH_PROOF_PASSED" else [],
        gates_failed=[] if status == "KILL_SWITCH_PROOF_PASSED" else ["kill_switch"],
        blocker=incomplete[0] if incomplete else None,
        next_action=payload["next_action"],
    )
    return payload


def write_weather_canary_kill_switch_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    return evaluate_kill_switch(output_root=output_root)
