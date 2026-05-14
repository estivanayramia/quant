from __future__ import annotations

from typing import Any

from quant_os.research.replay_candidates.pm_crypto_updown_baselines import (
    MIN_CONFIDENT_SAMPLE_ROWS,
)
from quant_os.research.replay_candidates.pm_crypto_updown_schema import CANDIDATE_ID
from quant_os.research.replay_candidates.pm_crypto_updown_signals import (
    is_replay_ready_row,
    score_pm_crypto_updown_signals,
)
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY


def run_pm_crypto_updown_placebos(
    *,
    rows: list[dict[str, Any]],
    signal_report: dict[str, Any],
) -> dict[str, Any]:
    primary_rows = _primary_rows(rows)
    candidate_probabilities = [
        _decision_probability(signal_report, row["clob_snapshot_id"]) for row in primary_rows
    ]
    candidate_brier = _brier(primary_rows, candidate_probabilities)
    tests = [
        _placebo_result("timestamp_shift", primary_rows, _rotate(candidate_probabilities)),
        _label_permutation(primary_rows, candidate_probabilities),
        _spot_sign_flip(rows),
        _random_entry(primary_rows),
        _market_window_shuffle(primary_rows, candidate_probabilities),
    ]
    comparable = [
        item for item in tests if item["brier_score"] is not None and item["skipped"] is False
    ]
    numerically_beats = bool(comparable) and all(
        candidate_brier is not None and candidate_brier < item["brier_score"] for item in comparable
    )
    warnings = []
    if len(primary_rows) < MIN_CONFIDENT_SAMPLE_ROWS:
        warnings.append("PLACEBO_SAMPLE_TOO_THIN_DIAGNOSTIC_ONLY")
    return {
        "schema_version": "pm_crypto_updown_placebo_eval_v1",
        "sequence": "37",
        "candidate_id": CANDIDATE_ID,
        "primary_evidence_row_count": len(primary_rows),
        "candidate_brier_score": candidate_brier,
        "placebo_tests": tests,
        "candidate_numerically_beats_placebos": numerically_beats,
        "candidate_beats_placebos_for_readiness": (
            numerically_beats and len(primary_rows) >= MIN_CONFIDENT_SAMPLE_ROWS
        ),
        "placebo_comparison_status": (
            "PLACEBO_DIAGNOSTIC_TOO_THIN"
            if len(primary_rows) < MIN_CONFIDENT_SAMPLE_ROWS
            else "PLACEBOS_BEATEN"
            if numerically_beats
            else "PLACEBO_NOT_BEATEN"
        ),
        "promotion_blocked": len(primary_rows) < MIN_CONFIDENT_SAMPLE_ROWS or not numerically_beats,
        "warnings": warnings,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _primary_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if is_replay_ready_row(row)
        and row.get("label_status") == "RESOLVED"
        and row.get("resolved_outcome") is not None
    ]


def _decision_probability(signal_report: dict[str, Any], row_id: str) -> float:
    decision = next(item for item in signal_report["row_decisions"] if item["row_id"] == row_id)
    return float(decision["predicted_probability"])


def _rotate(values: list[float]) -> list[float]:
    if len(values) <= 1:
        return list(values)
    return values[1:] + values[:1]


def _placebo_result(
    placebo_type: str,
    rows: list[dict[str, Any]],
    probabilities: list[float],
) -> dict[str, Any]:
    return {
        "placebo_type": placebo_type,
        "row_count": len(rows),
        "brier_score": _brier(rows, probabilities),
        "skipped": False,
        "diagnostic_only": len(rows) < MIN_CONFIDENT_SAMPLE_ROWS,
    }


def _label_permutation(
    rows: list[dict[str, Any]],
    probabilities: list[float],
) -> dict[str, Any]:
    permuted_rows = [dict(row) for row in rows]
    labels = [row["resolved_outcome"] for row in reversed(rows)]
    for row, label in zip(permuted_rows, labels, strict=True):
        row["resolved_outcome"] = label
    payload = _placebo_result("label_permutation", permuted_rows, probabilities)
    payload["permutation"] = "reverse_resolved_outcomes"
    return payload


def _spot_sign_flip(rows: list[dict[str, Any]]) -> dict[str, Any]:
    flipped = []
    for row in rows:
        item = dict(row)
        for key in ("spot_return_1s", "spot_return_5s", "spot_return_15s"):
            if item.get(key) is not None:
                item[key] = -float(item[key])
        flipped.append(item)
    primary = _primary_rows(flipped)
    signals = score_pm_crypto_updown_signals(flipped)
    probabilities = [_decision_probability(signals, row["clob_snapshot_id"]) for row in primary]
    payload = _placebo_result("spot_return_sign_flip", primary, probabilities)
    payload["transformation"] = "spot_return_signs_negated"
    return payload


def _random_entry(rows: list[dict[str, Any]]) -> dict[str, Any]:
    probabilities = [0.40 if index % 2 == 0 else 0.60 for index, _row in enumerate(rows)]
    payload = _placebo_result("random_entry", rows, probabilities)
    payload["seed"] = "deterministic_alternating_fixture_seed"
    return payload


def _market_window_shuffle(
    rows: list[dict[str, Any]],
    probabilities: list[float],
) -> dict[str, Any]:
    market_ids = {row["market_id"] for row in rows}
    if len(market_ids) < 2:
        return {
            "placebo_type": "market_window_shuffle",
            "row_count": len(rows),
            "brier_score": None,
            "skipped": True,
            "diagnostic_only": True,
            "warning": "MARKET_WINDOW_SHUFFLE_SKIPPED_TOO_FEW_MARKETS",
        }
    shuffled = [dict(row) for row in rows]
    labels = [row["resolved_outcome"] for row in rows[1:] + rows[:1]]
    for row, label in zip(shuffled, labels, strict=True):
        row["resolved_outcome"] = label
    return _placebo_result("market_window_shuffle", shuffled, probabilities)


def _brier(rows: list[dict[str, Any]], probabilities: list[float]) -> float | None:
    if not rows:
        return None
    actuals = [1.0 if row["outcome"] == row["resolved_outcome"] else 0.0 for row in rows]
    return sum(
        (probability - actual) ** 2
        for probability, actual in zip(probabilities, actuals, strict=True)
    ) / len(rows)
