from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from quant_os.autonomy.forward_capture_plan import write_forward_capture_plan
from quant_os.proving.relentless_profit_campaign_state import (
    default_campaign_state,
    load_campaign_state,
    mark_expansion,
    update_state_after_attempt,
    write_campaign_state,
)
from quant_os.readiness.profit_candidate_autonomy_path import (
    write_profit_candidate_autonomy_path,
)
from quant_os.research.lane_selection.relentless_profit_campaign_engine import (
    attempt_lane,
    build_campaign_queue,
    expand_safe_lane_queue,
    is_campaign_complete_status,
    select_next_lane,
    should_expand_queue,
)
from quant_os.research.lane_selection.relentless_profit_campaign_models import (
    CAMPAIGN_CHECKPOINTED_NOT_COMPLETE,
    CAMPAIGN_SAFETY,
    PAPER_PROFIT_CANDIDATE_FOUND,
    build_initial_lane_universe,
)
from quant_os.research.lane_selection.relentless_profit_campaign_report import (
    write_profit_campaign_report,
)


def run_relentless_profit_campaign(
    *,
    output_root: str | Path = ".",
    max_lanes: int = 6,
    public_network_ok: bool = False,
) -> dict[str, Any]:
    root = Path(output_root)
    state = load_campaign_state(output_root=root)
    if not state:
        state = default_campaign_state()
    state = deepcopy(state)
    state["run_counter"] = int(state.get("run_counter", 0)) + 1
    state["last_run_attempts"] = []

    lanes = build_initial_lane_universe()
    attempts: list[dict[str, Any]] = []
    forward_plan = None
    candidate_found = False

    for _ in range(max(0, max_lanes)):
        queue = build_campaign_queue(state, lanes=lanes)
        selected = select_next_lane(
            queue,
            state,
            retry_public_data_blockers=public_network_ok,
        )
        if selected is None:
            if should_expand_queue(queue, state):
                expansion = expand_safe_lane_queue()
                state = mark_expansion(
                    state,
                    added=expansion["added"],
                    rejected=expansion["rejected"],
                )
                queue = build_campaign_queue(state, lanes=lanes)
                selected = select_next_lane(
                    queue,
                    state,
                    retry_public_data_blockers=public_network_ok,
                )
            if selected is None:
                break
        attempt = attempt_lane(selected, public_network_ok=public_network_ok)
        attempts.append(attempt)
        queued_lane_ids = [
            str(lane["lane_id"])
            for lane in queue
            if str(lane["lane_id"]) not in set(state.get("lanes_attempted", []))
        ]
        state = update_state_after_attempt(state, attempt, queued_lane_ids=queued_lane_ids)
        if attempt.get("status") == "NEEDS_FORWARD_DATA_CAPTURE" and forward_plan is None:
            forward_plan = write_forward_capture_plan(output_root=root)
        if attempt.get("paper_profit_candidate") is True:
            candidate_found = True
            break

    campaign_status = (
        PAPER_PROFIT_CANDIDATE_FOUND if candidate_found else CAMPAIGN_CHECKPOINTED_NOT_COMPLETE
    )
    if not is_campaign_complete_status(campaign_status):
        campaign_status = CAMPAIGN_CHECKPOINTED_NOT_COMPLETE
    state["current_campaign_status"] = campaign_status
    state["validation_status"] = "NOT_RUN"
    if public_network_ok and campaign_status != PAPER_PROFIT_CANDIDATE_FOUND:
        state["exact_resume_command"] = (
            "python -m quant_os.cli proving relentless-profit-campaign-run "
            "--public-network-ok --max-lanes 1"
        )
    if campaign_status == PAPER_PROFIT_CANDIDATE_FOUND:
        state["current_paper_status"] = PAPER_PROFIT_CANDIDATE_FOUND
        state["next_action"] = "Write autonomy path report and run bounded shadow rehearsal gate."
    elif (
        not attempts
        and state.get("lanes_added_during_expansion")
        and state.get("current_paper_status") != "TOOL_OR_CONTEXT_LIMIT_REACHED"
    ):
        state["current_paper_status"] = "EXPAND_SAFE_LANE_QUEUE"
        state["next_action"] = "Continue with expanded safe lane queue."

    state = write_campaign_state(state, output_root=root)
    autonomy_path = write_profit_candidate_autonomy_path(
        output_root=root,
        campaign_payload={"state": state},
    )
    payload = {
        "schema_version": "relentless_profit_campaign_v1",
        "campaign_status": campaign_status,
        "paper_profit_status": state.get("current_paper_status"),
        "profit_claim_guard_status": state.get("profit_claim_status"),
        "state": state,
        "attempts": attempts,
        "run_summary": {
            "lanes_attempted_this_run": len(attempts),
            "max_lanes": max_lanes,
            "bounded_per_run": True,
            "resumable": True,
        },
        "lanes_added_by_expansion": state.get("lanes_added_during_expansion", []),
        "unsafe_expansion_rejected": state.get("unsafe_expansion_rejected", []),
        "best_candidate_so_far": state.get("best_candidate_so_far"),
        "forward_capture_plan": forward_plan,
        "autonomy_path": autonomy_path,
        "next_action": state.get("next_action"),
        "exact_resume_command": state.get("exact_resume_command"),
        "live_ready": False,
        "canary_ready": False,
        "live_readiness_claimed": False,
        "canary_readiness_claimed": False,
        "profit_claim_made": False,
        **CAMPAIGN_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }
    return write_profit_campaign_report(payload, output_root=root)
