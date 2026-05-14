from __future__ import annotations

from typing import Any

from quant_os.research.replay_candidates.pm_crypto_updown_schema import CANDIDATE_ID
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

FEE_PENALTY = 0.01
LATENCY_PENALTY = 0.02
STALE_SNAPSHOT_PENALTY = 0.03


def apply_pm_crypto_updown_cost_stress(
    *,
    rows: list[dict[str, Any]],
    signal_report: dict[str, Any],
) -> dict[str, Any]:
    rows_by_id = {row["clob_snapshot_id"]: row for row in rows}
    cost_rows = [
        _cost_row(rows_by_id[decision["row_id"]], decision)
        for decision in signal_report["row_decisions"]
    ]
    cost_rows = sorted(cost_rows, key=lambda item: (item["side"] != "BUY", item["row_id"]))
    candidate_rows = [row for row in cost_rows if row["side"] == "BUY"]
    cost_adjusted_score = sum(row["cost_adjusted_edge"] for row in candidate_rows)
    return {
        "schema_version": "pm_crypto_updown_cost_stress_v1",
        "sequence": "37",
        "candidate_id": CANDIDATE_ID,
        "candidate_signal_count": len(candidate_rows),
        "rows": cost_rows,
        "cost_adjusted_score": cost_adjusted_score,
        "costs_destroy_edge": bool(candidate_rows) and cost_adjusted_score <= 0.0,
        "assumptions": {
            "fee_penalty": FEE_PENALTY,
            "latency_penalty": LATENCY_PENALTY,
            "stale_snapshot_penalty": STALE_SNAPSHOT_PENALTY,
            "spread_crossing": "buy signal crosses from mid to ask",
        },
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _cost_row(row: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    if decision["side"] != "BUY":
        return {
            "row_id": row["clob_snapshot_id"],
            "market_id": row["market_id"],
            "token_id": row["token_id"],
            "side": decision["side"],
            "gross_realized_edge": 0.0,
            "spread_crossing_cost": 0.0,
            "total_conservative_cost": 0.0,
            "cost_adjusted_edge": 0.0,
            "blocked_by_cost": False,
            "cost_blockers": [],
        }
    gross = _gross_realized_edge(row)
    spread_crossing = max(float(row["market_ask"]) - float(row["market_mid"]), 0.0)
    total_cost = spread_crossing + FEE_PENALTY + LATENCY_PENALTY + _stale_penalty(row)
    adjusted = gross - total_cost
    blockers = ["COST_ADJUSTED_EDGE_NON_POSITIVE"] if adjusted <= 0.0 else []
    return {
        "row_id": row["clob_snapshot_id"],
        "market_id": row["market_id"],
        "token_id": row["token_id"],
        "side": decision["side"],
        "gross_realized_edge": gross,
        "spread_crossing_cost": spread_crossing,
        "total_conservative_cost": total_cost,
        "cost_adjusted_edge": adjusted,
        "blocked_by_cost": bool(blockers),
        "cost_blockers": blockers,
    }


def _gross_realized_edge(row: dict[str, Any]) -> float:
    ask = float(row["market_ask"])
    if row.get("resolved_outcome") == row.get("outcome"):
        return 1.0 - ask
    return -ask


def _stale_penalty(row: dict[str, Any]) -> float:
    flags = set(row.get("data_quality_flags", []))
    if {"STALE_SPOT_SNAPSHOT", "STALE_CLOB_SNAPSHOT"} & flags:
        return STALE_SNAPSHOT_PENALTY
    return 0.0
