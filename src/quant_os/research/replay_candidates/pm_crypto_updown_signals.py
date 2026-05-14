from __future__ import annotations

from typing import Any

from quant_os.research.replay_candidates.pm_crypto_updown_schema import CANDIDATE_ID
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

REPLAY_READY_BLOCKING_FLAGS = {
    "MISSING_CLOB_SNAPSHOT",
    "MISSING_SPOT_SNAPSHOT",
    "WIDE_SPREAD",
    "LOW_LIQUIDITY",
    "LABEL_UNRESOLVED",
    "MISSING_WINDOW_LABELS",
}
MIN_ABS_SPOT_RETURN = 0.00005
MIN_SECONDS_TO_WINDOW_END = 5.0
CANDIDATE_PROBABILITY = 0.60
COUNTER_OUTCOME_PROBABILITY = 0.40
NEUTRAL_PROBABILITY = 0.50

SIGNAL_DEFINITIONS = [
    {
        "name": "spot_return_direction",
        "rationale": "A recent positive spot move favors the UP token; a negative move favors DOWN.",
        "failure_mode": "Microstructure noise can overwhelm tiny spot moves.",
    },
    {
        "name": "market_lag_vs_spot",
        "rationale": "The candidate only acts when market probability has not fully followed spot.",
        "failure_mode": "The CLOB may already encode information visible outside the fixture.",
    },
    {
        "name": "spread_liquidity_time_filter",
        "rationale": "Wide spreads, low liquidity, and near-expiry rows are blocked before evaluation.",
        "failure_mode": "A pass only means the row is replay-testable, not executable.",
    },
]


def score_pm_crypto_updown_signals(rows: list[dict[str, Any]]) -> dict[str, Any]:
    decisions = [_score_row(row) for row in rows]
    primary = [row for row in decisions if row["primary_evidence"]]
    candidate_signals = [row for row in decisions if row["side"] == "BUY"]
    return {
        "schema_version": "pm_crypto_updown_signal_score_v1",
        "sequence": "37",
        "candidate_id": CANDIDATE_ID,
        "signal_definitions": SIGNAL_DEFINITIONS,
        "row_decisions": decisions,
        "primary_evidence_row_count": len(primary),
        "candidate_signal_count": len(candidate_signals),
        "blocked_row_count": sum(1 for row in decisions if row["blocked"]),
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def is_replay_ready_row(row: dict[str, Any]) -> bool:
    return not (set(row.get("data_quality_flags", [])) & REPLAY_READY_BLOCKING_FLAGS)


def _score_row(row: dict[str, Any]) -> dict[str, Any]:
    blockers = _row_blockers(row)
    direction = _spot_direction(row)
    aligns_with_outcome = direction == row["outcome"]
    primary = not blockers and row.get("label_status") == "RESOLVED"
    strength = abs(row.get("spot_return_5s") or 0.0)
    side = "NO_SIGNAL"
    probability = NEUTRAL_PROBABILITY
    signal_reason = "No qualifying spot-lag signal."

    if primary and direction in {"UP", "DOWN"}:
        probability = CANDIDATE_PROBABILITY if aligns_with_outcome else COUNTER_OUTCOME_PROBABILITY
        if aligns_with_outcome and strength >= MIN_ABS_SPOT_RETURN:
            side = "BUY"
            signal_reason = (
                f"{direction} token aligns with spot_return_5s="
                f"{row['spot_return_5s']:.8f} and passes replay filters."
            )
        else:
            signal_reason = (
                f"{row['outcome']} token is the counter-outcome for spot direction {direction}."
            )
    elif blockers:
        signal_reason = "Row is excluded from primary evidence by replay quality filters."

    actual_won = row.get("resolved_outcome") == row.get("outcome")
    return {
        "row_id": row["clob_snapshot_id"],
        "clob_snapshot_id": row["clob_snapshot_id"],
        "market_id": row["market_id"],
        "token_id": row["token_id"],
        "outcome": row["outcome"],
        "resolved_outcome": row.get("resolved_outcome"),
        "actual_won": actual_won,
        "primary_evidence": primary,
        "blocked": bool(blockers),
        "blockers": blockers,
        "side": side,
        "predicted_probability": probability,
        "spot_direction": direction,
        "signal_strength": strength,
        "rationale": signal_reason,
        "failure_mode": _failure_mode(row, blockers),
        "hypothesis": "pm_crypto_updown_repricing_lag",
    }


def _row_blockers(row: dict[str, Any]) -> list[str]:
    blockers = sorted(set(row.get("data_quality_flags", [])) & REPLAY_READY_BLOCKING_FLAGS)
    if row.get("seconds_to_window_end", 0.0) < MIN_SECONDS_TO_WINDOW_END:
        blockers.append("TOO_CLOSE_TO_WINDOW_END")
    if row.get("spot_return_5s") is None:
        blockers.append("MISSING_SPOT_RETURN_5S")
    return sorted(set(blockers))


def _spot_direction(row: dict[str, Any]) -> str:
    value = row.get("spot_return_5s")
    if value is None or abs(value) < MIN_ABS_SPOT_RETURN:
        return "FLAT"
    if value > 0:
        return "UP"
    return "DOWN"


def _failure_mode(row: dict[str, Any], blockers: list[str]) -> str:
    if blockers:
        return "Excluded rows cannot support a replay promotion decision."
    if row.get("market_spread") is None:
        return "Missing market price prevents cost realism."
    return "Short-window spot lag can disappear after spread, fees, latency, or larger samples."
