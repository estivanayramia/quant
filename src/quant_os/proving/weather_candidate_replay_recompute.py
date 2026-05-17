from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.proving.weather_market_batch_paper_proving import (
    run_weather_market_batch_paper_proving,
)
from quant_os.readiness.canary_readiness_common import (
    decimal_value,
    load_paper_payload,
    load_rows,
    safety_payload,
    update_canary_state,
    write_json_markdown_report,
)

REPORT_DIR = Path("reports/canary_readiness/replay_recompute")


def evaluate_replay_recompute(
    *,
    rows: list[dict[str, Any]] | None = None,
    expected_paper_payload: dict[str, Any] | None = None,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    rows = rows if rows is not None else load_rows(output_root=output_root)
    expected_paper_payload = expected_paper_payload or load_paper_payload(output_root=output_root) or {}
    blockers: list[str] = []
    if not rows:
        blockers.append("REPLAY_ROWS_MISSING")
    recomputed = run_weather_market_batch_paper_proving(rows, output_root=output_root) if rows else {}
    if expected_paper_payload:
        if decimal_value(recomputed.get("net_simulated_pnl_after_costs")) != decimal_value(
            expected_paper_payload.get("net_simulated_pnl_after_costs")
        ):
            blockers.append("NET_PNL_MISMATCH")
        if recomputed.get("proof_row_count") != expected_paper_payload.get("proof_row_count"):
            blockers.append("PROOF_ROW_COUNT_MISMATCH")
        if recomputed.get("readiness_status") != expected_paper_payload.get("readiness_status"):
            blockers.append("READINESS_STATUS_MISMATCH")
    else:
        blockers.append("EXPECTED_PAPER_REPORT_MISSING")
    status = "REPLAY_RECOMPUTE_MATCHED" if not blockers else "REPLAY_RECOMPUTE_MISMATCH"
    if "REPLAY_ROWS_MISSING" in blockers:
        status = "REPLAY_RECOMPUTE_BLOCKED"
    payload = safety_payload(
        schema_version="weather_candidate_replay_recompute_v1",
        status=status,
        allowed_statuses=[
            "REPLAY_RECOMPUTE_MATCHED",
            "REPLAY_RECOMPUTE_MISMATCH",
            "REPLAY_RECOMPUTE_BLOCKED",
        ],
        candidate_id="pm_weather_forecast_market_mismatch",
        recomputed=recomputed,
        expected_summary={
            "proof_row_count": expected_paper_payload.get("proof_row_count"),
            "net_simulated_pnl_after_costs": expected_paper_payload.get(
                "net_simulated_pnl_after_costs"
            ),
            "readiness_status": expected_paper_payload.get("readiness_status"),
        },
        recomputed_summary={
            "proof_row_count": recomputed.get("proof_row_count"),
            "net_simulated_pnl_after_costs": recomputed.get("net_simulated_pnl_after_costs"),
            "readiness_status": recomputed.get("readiness_status"),
            "gross_simulated_pnl": recomputed.get("gross_simulated_pnl"),
            "fill_adjusted_pnl": recomputed.get("fill_adjusted_pnl"),
            "max_drawdown": recomputed.get("max_drawdown"),
            "baseline_comparison": recomputed.get("baseline_comparison"),
            "placebo_comparison": recomputed.get("placebo_comparison"),
            "one_row_dominance": recomputed.get("one_row_dominance"),
            "oos_walk_forward_status": recomputed.get("oos_walk_forward_status"),
        },
        blockers=sorted(set(blockers)),
        next_action="Run robustness hardening." if status == "REPLAY_RECOMPUTE_MATCHED" else "Resolve replay mismatch.",
    )
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_replay_recompute.json",
        md_name="latest_replay_recompute.md",
        title="Weather Candidate Replay Recompute",
        summary="Independently recomputes paper results from rows.",
    )
    update_canary_state(
        output_root=output_root,
        gate="replay_recompute",
        gate_status=status,
        evidence_paths=payload["report_paths"],
        gates_passed=["replay_recompute"] if status == "REPLAY_RECOMPUTE_MATCHED" else [],
        gates_failed=[] if status == "REPLAY_RECOMPUTE_MATCHED" else ["replay_recompute"],
        blocker=payload["blockers"][0] if payload["blockers"] else None,
        next_action=payload["next_action"],
    )
    return payload


def write_weather_candidate_replay_recompute_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    return evaluate_replay_recompute(output_root=output_root)
