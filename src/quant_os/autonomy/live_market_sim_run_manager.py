from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.autonomy.live_market_sim_common import (
    ACTIVE_POLICY_VERSION,
    ROOT,
    hash_payload,
    load_json,
    load_state,
    reset_state,
    sim_safety_payload,
)
from quant_os.readiness.canary_readiness_common import utc_now, write_json_markdown_report

REPORT_DIR = ROOT / "runs"
ARCHIVE_DIR = ROOT / "archive"


def build_live_market_sim_start_new_run(*, output_root: str | Path = ".") -> dict[str, Any]:
    state = load_state(output_root=output_root)
    final = load_json(
        "reports/live_market_sim_profitability/final/latest_live_market_sim_profitability.json",
        output_root=output_root,
    ) or {}
    pnl = load_json("reports/live_market_sim_profitability/pnl/latest_pnl.json", output_root=output_root) or {}
    outcomes = load_json(
        "reports/live_market_sim_profitability/outcomes/latest_outcomes.json",
        output_root=output_root,
    ) or {}
    archive_id = f"lmsa_{hash_payload({'state': state, 'final': final, 'ts': utc_now()})}"
    archive_path = ARCHIVE_DIR / f"{archive_id}.json"
    archive_payload = sim_safety_payload(
        schema_version="live_market_sim_run_archive_v1",
        archive_id=archive_id,
        archived_at=utc_now(),
        archived_policy_version=state.get("active_policy_version", "legacy_strict_weather_yes_v1"),
        archived_run_id=state.get("run_id", "legacy_unversioned_run"),
        final_status=final.get("status", "UNKNOWN"),
        observation_count=final.get("observation_count", state.get("observations_count", 0)),
        eligible_intent_count=final.get("eligible_intent_count", state.get("eligible_intent_count", 0)),
        fake_fill_count=final.get("fake_fill_count", state.get("fake_fill_count", 0)),
        resolved_outcome_count=final.get("resolved_outcome_count", state.get("resolved_outcome_count", 0)),
        pending_outcome_count=final.get("pending_outcome_count", state.get("pending_outcome_count", 0)),
        fake_net_pnl=final.get("fake_net_pnl", state.get("fake_net_pnl", 0.0)),
        blockers=final.get("blockers", state.get("current_blockers", [])),
        final=final,
        pnl=pnl,
        outcomes=outcomes,
    )
    root = Path(output_root)
    archive_file = root / archive_path
    archive_file.parent.mkdir(parents=True, exist_ok=True)
    archive_file.write_text(json.dumps(archive_payload, indent=2, sort_keys=True), encoding="utf-8")
    new_state = reset_state(
        output_root=output_root,
        previous_run_archive=str(archive_path),
        previous_run_status=str(final.get("status", "UNKNOWN")),
    )
    return sim_safety_payload(
        schema_version="live_market_sim_start_new_run_v1",
        status="LIVE_MARKET_SIM_NEW_RUN_STARTED",
        allowed_statuses=["LIVE_MARKET_SIM_NEW_RUN_STARTED"],
        archived_run_path=str(archive_path),
        archived_run_status=archive_payload["final_status"],
        archived_fake_net_pnl=archive_payload["fake_net_pnl"],
        new_run_id=new_state["run_id"],
        new_policy_version=ACTIVE_POLICY_VERSION,
        blockers=[],
        next_action="Run .\\make.cmd live-market-sim-profitability-public-run to collect v2 public-forward evidence.",
        exact_resume_command=".\\make.cmd live-market-sim-profitability-public-run",
    )


def write_live_market_sim_start_new_run_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_live_market_sim_start_new_run(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_start_new_run.json",
        md_name="latest_start_new_run.md",
        title="Live Market Sim Start New Run",
        summary="Archives the prior strict live-market simulated run and starts a clean policy-versioned run.",
    )
    return payload
