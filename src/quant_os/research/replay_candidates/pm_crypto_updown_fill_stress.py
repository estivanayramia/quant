from __future__ import annotations

from typing import Any

from quant_os.research.replay_candidates.pm_crypto_updown_schema import CANDIDATE_ID
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

MAX_SPREAD = 0.05
MIN_LIQUIDITY = 100.0
BASE_FILL_PROBABILITY = 0.75
PARTIAL_FILL_FACTOR = 0.50


def apply_pm_crypto_updown_fill_stress(
    *,
    rows: list[dict[str, Any]],
    cost_report: dict[str, Any],
) -> dict[str, Any]:
    rows_by_id = {row["clob_snapshot_id"]: row for row in rows}
    fill_rows = [
        _fill_row(rows_by_id[cost_row["row_id"]], cost_row) for cost_row in cost_report["rows"]
    ]
    candidate_rows = [row for row in fill_rows if row["side"] == "BUY"]
    fill_adjusted_score = sum(row["fill_adjusted_edge"] for row in candidate_rows)
    realism_blocks = any(row["blocked_by_fill"] for row in candidate_rows)
    return {
        "schema_version": "pm_crypto_updown_fill_stress_v1",
        "sequence": "37",
        "candidate_id": CANDIDATE_ID,
        "candidate_signal_count": len(candidate_rows),
        "rows": fill_rows,
        "fill_adjusted_score": fill_adjusted_score,
        "fill_realism_blocks_edge": realism_blocks,
        "assumptions": {
            "max_spread": MAX_SPREAD,
            "min_liquidity": MIN_LIQUIDITY,
            "base_fill_probability": BASE_FILL_PROBABILITY,
            "partial_fill_factor": PARTIAL_FILL_FACTOR,
        },
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _fill_row(row: dict[str, Any], cost_row: dict[str, Any]) -> dict[str, Any]:
    blockers = []
    spread = float(row.get("market_spread") or 0.0)
    liquidity = float(row.get("market_liquidity") or 0.0)
    if cost_row["side"] != "BUY":
        blockers.append("NO_SHADOW_SIGNAL")
    if spread > MAX_SPREAD:
        blockers.append("WIDE_SPREAD_REJECTION")
    if liquidity < MIN_LIQUIDITY:
        blockers.append("LOW_LIQUIDITY_REJECTION")
    if cost_row.get("blocked_by_cost"):
        blockers.extend(cost_row["cost_blockers"])
    if "LABEL_UNRESOLVED" in row.get("data_quality_flags", []):
        blockers.append("UNRESOLVED_LABEL_REJECTION")
    fill_probability = 0.0 if blockers else BASE_FILL_PROBABILITY
    fill_adjusted_edge = cost_row["cost_adjusted_edge"] * fill_probability * PARTIAL_FILL_FACTOR
    return {
        "row_id": row["clob_snapshot_id"],
        "market_id": row["market_id"],
        "token_id": row["token_id"],
        "side": cost_row["side"],
        "fill_probability": fill_probability,
        "partial_fill_factor": PARTIAL_FILL_FACTOR if cost_row["side"] == "BUY" else 0.0,
        "fill_adjusted_edge": fill_adjusted_edge,
        "blocked_by_fill": bool(blockers and cost_row["side"] == "BUY"),
        "fill_blockers": sorted(set(blockers)),
    }
