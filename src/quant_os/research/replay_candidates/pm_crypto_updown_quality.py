from __future__ import annotations

from typing import Any

from quant_os.research.replay_candidates.pm_crypto_updown_schema import CANDIDATE_ID
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY


def evaluate_pm_crypto_updown_quality(dataset: dict[str, Any]) -> dict[str, Any]:
    rows = dataset["rows"]
    row_count = len(rows)
    market_ids = {row["market_id"] for row in rows}
    missing_clob = _count(rows, "MISSING_CLOB_SNAPSHOT")
    missing_spot = _count(rows, "MISSING_SPOT_SNAPSHOT")
    stale_count = _count(rows, "STALE_SPOT_SNAPSHOT") + _count(rows, "STALE_CLOB_SNAPSHOT")
    wide_spread_count = _count(rows, "WIDE_SPREAD")
    low_liquidity_count = _count(rows, "LOW_LIQUIDITY")
    unresolved_label_count = _count(rows, "LABEL_UNRESOLVED")
    missing_window_label_count = _count(rows, "MISSING_WINDOW_LABELS")
    resolved_label_count = sum(1 for row in rows if row["label_status"] == "RESOLVED")
    replay_ready_rows = [
        row
        for row in rows
        if not set(row["data_quality_flags"])
        & {
            "MISSING_CLOB_SNAPSHOT",
            "MISSING_SPOT_SNAPSHOT",
            "WIDE_SPREAD",
            "LOW_LIQUIDITY",
            "LABEL_UNRESOLVED",
            "MISSING_WINDOW_LABELS",
        }
    ]
    blockers = _blockers(
        row_count=row_count,
        missing_clob=missing_clob,
        missing_spot=missing_spot,
        missing_window_label_count=missing_window_label_count,
        replay_ready_row_count=len(replay_ready_rows),
    )
    caveats = _caveats(
        wide_spread_count=wide_spread_count,
        low_liquidity_count=low_liquidity_count,
        unresolved_label_count=unresolved_label_count,
    )
    return {
        "schema_version": "pm_crypto_updown_dataset_quality_v1",
        "sequence": "36",
        "candidate_id": CANDIDATE_ID,
        "quality_status": _status_from_blockers(blockers),
        "row_count": row_count,
        "market_count": len(market_ids),
        "resolved_label_count": resolved_label_count,
        "clob_coverage": _coverage(row_count, row_count - missing_clob),
        "spot_coverage": _coverage(row_count, row_count - missing_spot),
        "stale_snapshot_count": stale_count,
        "wide_spread_count": wide_spread_count,
        "low_liquidity_count": low_liquidity_count,
        "unresolved_label_count": unresolved_label_count,
        "missing_window_label_count": missing_window_label_count,
        "replay_ready_row_count": len(replay_ready_rows),
        "blockers": blockers,
        "caveats": caveats,
        "ready_for_phase37_candidate_replay": not blockers,
        "not_shadow_trading_readiness": True,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _count(rows: list[dict[str, Any]], flag: str) -> int:
    return sum(1 for row in rows if flag in row["data_quality_flags"])


def _coverage(row_count: int, covered_count: int) -> float:
    if row_count == 0:
        return 0.0
    return covered_count / row_count


def _blockers(
    *,
    row_count: int,
    missing_clob: int,
    missing_spot: int,
    missing_window_label_count: int,
    replay_ready_row_count: int,
) -> list[str]:
    blockers = []
    if row_count == 0:
        blockers.append("REPLAY_DATASET_TOO_THIN")
    if missing_clob:
        blockers.append("MISSING_CLOB_SNAPSHOT")
    if missing_spot:
        blockers.append("MISSING_SPOT_SNAPSHOT")
    if missing_window_label_count:
        blockers.append("MISSING_WINDOW_LABELS")
    if replay_ready_row_count < 2:
        blockers.append("REPLAY_READY_ROWS_TOO_THIN")
    return blockers


def _caveats(
    *,
    wide_spread_count: int,
    low_liquidity_count: int,
    unresolved_label_count: int,
) -> list[str]:
    caveats = []
    if unresolved_label_count:
        caveats.append("UNRESOLVED_LABELS_PRESENT")
    if wide_spread_count:
        caveats.append("WIDE_SPREAD_ROWS_PRESENT")
    if low_liquidity_count:
        caveats.append("LOW_LIQUIDITY_ROWS_PRESENT")
    return caveats


def _status_from_blockers(blockers: list[str]) -> str:
    if not blockers:
        return "REPLAY_DATASET_READY_FOR_CANDIDATE_TEST"
    if "MISSING_CLOB_SNAPSHOT" in blockers:
        return "REPLAY_DATASET_BLOCKED_MISSING_CLOB"
    if "MISSING_SPOT_SNAPSHOT" in blockers:
        return "REPLAY_DATASET_BLOCKED_MISSING_SPOT"
    if "MISSING_WINDOW_LABELS" in blockers:
        return "REPLAY_DATASET_BLOCKED_MISSING_WINDOW_LABELS"
    if "REPLAY_DATASET_TOO_THIN" in blockers or "REPLAY_READY_ROWS_TOO_THIN" in blockers:
        return "REPLAY_DATASET_BLOCKED_TOO_THIN"
    return "REPLAY_DATASET_PARTIAL"
