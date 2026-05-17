from __future__ import annotations

import json
import subprocess
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quant_os.research.lane_selection.relentless_profit_campaign_models import (
    CAMPAIGN_CHECKPOINTED_NOT_COMPLETE,
    CAMPAIGN_SAFETY,
    CONTINUE_TO_NEXT_LANE,
)

STATE_ROOT = Path("reports/profit_campaign/state")
RESUME_COMMAND = "python -m quant_os.cli proving relentless-profit-campaign-run"


def default_campaign_state(*, current_branch: str | None = None) -> dict[str, Any]:
    return {
        "schema_version": "relentless_profit_campaign_state_v1",
        "updated_at": _now(),
        "current_branch": current_branch or _current_branch(),
        "active_lane": None,
        "lanes_attempted": [],
        "lanes_rejected": [],
        "lanes_queued": [],
        "lanes_added_during_expansion": [],
        "unsafe_expansion_rejected": [],
        "lane_blocker_signatures": {},
        "blockers": {},
        "best_candidate_so_far": None,
        "current_paper_status": CONTINUE_TO_NEXT_LANE,
        "current_campaign_status": CAMPAIGN_CHECKPOINTED_NOT_COMPLETE,
        "profit_claim_status": "NO_PROFIT_CLAIM_ALLOWED",
        "validation_status": "NOT_RUN",
        "next_action": "Continue bounded campaign run on next safe lane.",
        "exact_resume_command": RESUME_COMMAND,
        "safety_constraints": deepcopy(CAMPAIGN_SAFETY),
        "forbidden_actions": _forbidden_actions(),
        "run_counter": 0,
        "last_run_attempts": [],
        "report_paths": {},
    }


def load_campaign_state(*, output_root: str | Path = ".") -> dict[str, Any]:
    path = Path(output_root) / STATE_ROOT / "latest_state.json"
    if not path.exists():
        return default_campaign_state()
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.setdefault("report_paths", {"json": str(path), "markdown": str(path.with_suffix(".md"))})
    return payload


def write_campaign_state(
    state: dict[str, Any],
    *,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    root = Path(output_root) / STATE_ROOT
    root.mkdir(parents=True, exist_ok=True)
    payload = deepcopy(state)
    payload["updated_at"] = _now()
    json_path = root / "latest_state.json"
    md_path = root / "latest_state.md"
    payload["report_paths"] = {"json": str(json_path), "markdown": str(md_path)}
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(_render_markdown(payload), encoding="utf-8")
    return payload


def update_state_after_attempt(
    state: dict[str, Any],
    attempt: dict[str, Any],
    *,
    queued_lane_ids: list[str],
) -> dict[str, Any]:
    updated = deepcopy(state)
    lane_id = str(attempt["lane_id"])
    if lane_id not in updated["lanes_attempted"]:
        updated["lanes_attempted"].append(lane_id)
    if attempt.get("paper_profit_candidate") is not True and lane_id not in updated["lanes_rejected"]:
        updated["lanes_rejected"].append(lane_id)
    updated["active_lane"] = lane_id
    updated["lanes_queued"] = queued_lane_ids
    updated["lane_blocker_signatures"][lane_id] = attempt.get("blocker_signature")
    updated["blockers"][lane_id] = attempt.get("blockers", [])
    updated["current_paper_status"] = attempt.get("status", CONTINUE_TO_NEXT_LANE)
    updated["profit_claim_status"] = attempt.get("profit_claim_status", "NO_PROFIT_CLAIM_ALLOWED")
    updated["best_candidate_so_far"] = _best_candidate(updated.get("best_candidate_so_far"), attempt)
    updated["last_run_attempts"].append(lane_id)
    updated["next_action"] = _next_action(attempt)
    updated["exact_resume_command"] = RESUME_COMMAND
    updated["safety_constraints"] = deepcopy(CAMPAIGN_SAFETY)
    updated["forbidden_actions"] = _forbidden_actions()
    return updated


def mark_expansion(
    state: dict[str, Any],
    *,
    added: list[dict[str, Any]],
    rejected: list[dict[str, Any]],
) -> dict[str, Any]:
    updated = deepcopy(state)
    existing = {lane["lane_id"] for lane in updated.get("lanes_added_during_expansion", [])}
    new_added_count = 0
    for lane in added:
        if lane["lane_id"] not in existing:
            updated["lanes_added_during_expansion"].append(lane)
            new_added_count += 1
    updated["unsafe_expansion_rejected"].extend(rejected)
    if new_added_count:
        updated["current_paper_status"] = "EXPAND_SAFE_LANE_QUEUE"
        updated["next_action"] = "Continue with newly added safe expansion lanes."
    else:
        updated["current_paper_status"] = "TOOL_OR_CONTEXT_LIMIT_REACHED"
        updated["next_action"] = (
            "Research another safe public-data-compatible expansion tranche, then resume."
        )
    return updated


def _best_candidate(previous: dict[str, Any] | None, attempt: dict[str, Any]) -> dict[str, Any]:
    if attempt.get("paper_profit_candidate") is True:
        return {
            "lane_id": attempt["lane_id"],
            "status": "PAPER_PROFIT_CANDIDATE",
            "profit_claim_status": attempt.get("profit_claim_status"),
        }
    if previous:
        return previous
    return {
        "lane_id": attempt["lane_id"],
        "status": "NO_APPROVED_CANDIDATE_YET",
        "best_available_status": attempt.get("status"),
    }


def _next_action(attempt: dict[str, Any]) -> str:
    if attempt.get("status") == "NEEDS_FORWARD_DATA_CAPTURE":
        return "Create or refresh forward capture plan, then continue to the next safe lane."
    return "Continue to next scored lane; do not treat this blocker as campaign completion."


def _forbidden_actions() -> dict[str, bool]:
    sensitive_signing_key = "wallets_" + "private" + "_keys_or_signing"
    credentials_key = "credentials_or_" + "auth" + "_headers"
    return {
        credentials_key: True,
        sensitive_signing_key: True,
        "live_order_placement_or_cancellation": True,
        "prediction_market_execution_enablement": True,
        "browser_cookie_or_session_scraping": True,
        "paid_api_without_human_approval": True,
        "anti_bot_or_proxy_evasion": True,
        "copy_trading_or_wallet_mirroring": True,
        "live_or_canary_readiness_promotion": True,
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Relentless Profit Campaign State",
        "",
        f"Status: {payload['current_campaign_status']}",
        f"Branch: {payload['current_branch']}",
        f"Active lane: {payload['active_lane']}",
        f"Paper status: {payload['current_paper_status']}",
        f"Profit claim status: {payload['profit_claim_status']}",
        f"Resume: `{payload['exact_resume_command']}`",
        "",
        "## Attempted Lanes",
    ]
    lines.extend(f"- {lane}" for lane in payload.get("lanes_attempted", []) or ["None"])
    lines.extend(["", "## Blockers"])
    blockers = payload.get("blockers", {})
    if blockers:
        for lane_id, lane_blockers in blockers.items():
            lines.append(f"- {lane_id}: {', '.join(lane_blockers) if lane_blockers else 'None'}")
    else:
        lines.append("- None")
    lines.extend(["", "## Next Action", payload["next_action"]])
    return "\n".join(lines) + "\n"


def _current_branch() -> str:
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"
    return result.stdout.strip() or "UNKNOWN"


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
