from __future__ import annotations

import math
from typing import Any

from quant_os.research.replay_candidates.pm_crypto_updown_schema import CANDIDATE_ID
from quant_os.research.replay_candidates.pm_crypto_updown_signals import is_replay_ready_row
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

MIN_CONFIDENT_SAMPLE_ROWS = 20


def evaluate_pm_crypto_updown_baselines(
    *,
    rows: list[dict[str, Any]],
    signal_report: dict[str, Any],
) -> dict[str, Any]:
    primary_rows = _primary_rows(rows)
    candidate_probabilities = {
        item["row_id"]: item["predicted_probability"] for item in signal_report["row_decisions"]
    }
    candidate_metrics = _metrics(
        primary_rows,
        [candidate_probabilities[row["clob_snapshot_id"]] for row in primary_rows],
    )
    baselines = {
        "market_probability": _metrics(
            primary_rows,
            [float(row["market_mid"]) for row in primary_rows],
        ),
        "no_skill": _metrics(primary_rows, [0.5 for _row in primary_rows]),
        "transparent_shrinkage": _metrics(
            primary_rows,
            [0.5 + ((float(row["market_mid"]) - 0.5) * 0.5) for row in primary_rows],
        ),
        "spot_direction_naive": _metrics(
            primary_rows,
            [_spot_direction_probability(row) for row in primary_rows],
        ),
        "previous_market_probability": _metrics(
            primary_rows,
            [_previous_market_probability(row) for row in primary_rows],
        ),
    }
    warnings = []
    if len(primary_rows) < MIN_CONFIDENT_SAMPLE_ROWS:
        warnings.append("SAMPLE_TOO_THIN_FOR_CONFIDENCE")
    return {
        "schema_version": "pm_crypto_updown_baseline_eval_v1",
        "sequence": "37",
        "candidate_id": CANDIDATE_ID,
        "primary_evidence_row_count": len(primary_rows),
        "candidate_metrics": candidate_metrics,
        "baselines": baselines,
        "candidate_beats_market_baseline": _beats(
            candidate_metrics,
            baselines["market_probability"],
        ),
        "candidate_beats_no_skill": _beats(candidate_metrics, baselines["no_skill"]),
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


def _metrics(rows: list[dict[str, Any]], probabilities: list[float]) -> dict[str, Any]:
    if not rows:
        return {
            "row_count": 0,
            "accuracy": None,
            "brier_score": None,
            "log_loss": None,
            "directional_correct_count": 0,
            "expected_value_before_cost": None,
            "expected_value_after_conservative_cost": None,
            "warning": "NO_PRIMARY_ROWS",
        }
    actuals = [1.0 if row["outcome"] == row["resolved_outcome"] else 0.0 for row in rows]
    clipped = [min(max(probability, 0.001), 0.999) for probability in probabilities]
    correct = [
        (probability >= 0.5 and actual == 1.0) or (probability < 0.5 and actual == 0.0)
        for probability, actual in zip(probabilities, actuals, strict=True)
    ]
    ev_before_cost = [
        _realized_buy_value(row) * max(probability - 0.5, 0.0)
        for row, probability in zip(rows, probabilities, strict=True)
    ]
    ev_after_cost = [
        value - (_conservative_cost(row) if value > 0.0 else 0.0) for row, value in zip(rows, ev_before_cost, strict=True)
    ]
    return {
        "row_count": len(rows),
        "accuracy": sum(correct) / len(correct),
        "brier_score": sum(
            (probability - actual) ** 2
            for probability, actual in zip(probabilities, actuals, strict=True)
        )
        / len(rows),
        "log_loss": -sum(
            (actual * math.log(probability)) + ((1.0 - actual) * math.log(1.0 - probability))
            for probability, actual in zip(clipped, actuals, strict=True)
        )
        / len(rows),
        "directional_correct_count": sum(1 for item in correct if item),
        "expected_value_before_cost": sum(ev_before_cost),
        "expected_value_after_conservative_cost": sum(ev_after_cost),
    }


def _spot_direction_probability(row: dict[str, Any]) -> float:
    value = row.get("spot_return_5s")
    if value is None or abs(value) < 0.00005:
        return 0.5
    direction = "UP" if value > 0 else "DOWN"
    return 0.58 if row["outcome"] == direction else 0.42


def _previous_market_probability(row: dict[str, Any]) -> float:
    if row.get("market_last_trade_price") is not None:
        return float(row["market_last_trade_price"])
    return float(row["market_mid"])


def _beats(candidate: dict[str, Any], baseline: dict[str, Any]) -> bool:
    if candidate["brier_score"] is None or baseline["brier_score"] is None:
        return False
    return candidate["brier_score"] < baseline["brier_score"]


def _realized_buy_value(row: dict[str, Any]) -> float:
    ask = float(row["market_ask"])
    return (1.0 - ask) if row["outcome"] == row["resolved_outcome"] else -ask


def _conservative_cost(row: dict[str, Any]) -> float:
    spread = float(row.get("market_spread") or 0.0)
    return (spread / 2.0) + 0.01 + 0.02
