from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from quant_os.research.replay_candidates.pm_crypto_updown_schema import CANDIDATE_ID
from quant_os.research.replay_candidates.pm_crypto_updown_signals import (
    score_pm_crypto_updown_signals,
)


@dataclass(frozen=True)
class PmCryptoUpdownShadowPolicyConfig:
    max_spread: float = 0.05
    min_liquidity: float = 100.0
    max_stale_book_age_seconds: float = 2.0
    max_latency_penalty: float = 0.05
    min_spot_lag_confidence: float = 0.60
    min_expected_edge_after_cost: float = 0.01
    min_time_to_window_end_seconds: float = 5.0
    max_no_fill_probability: float = 0.85
    min_partial_fill_ratio: float = 0.25
    fee_penalty: float = 0.01
    default_latency_penalty: float = 0.02
    stale_book_penalty: float = 0.03


DEFAULT_PM_CRYPTO_UPDOWN_SHADOW_POLICY = PmCryptoUpdownShadowPolicyConfig()

BLOCKER_PRIORITY = [
    "NO_SHADOW_SIGNAL",
    "SPREAD_TOO_WIDE",
    "LOW_LIQUIDITY",
    "STALE_CLOB",
    "LATENCY_PENALTY_TOO_HIGH",
    "NO_FILL_PROBABILITY_TOO_HIGH",
    "PARTIAL_FILL_TOO_SMALL",
    "TOO_CLOSE_TO_WINDOW_END",
    "SPOT_LAG_CONFIDENCE_TOO_LOW",
    "PRICE_DISCIPLINE_FAILED",
    "EXPECTED_EDGE_AFTER_COST_TOO_LOW",
]


def build_pm_crypto_updown_shadow_intents(
    *,
    rows: list[dict[str, Any]],
    signal_report: dict[str, Any] | None = None,
    config: PmCryptoUpdownShadowPolicyConfig = DEFAULT_PM_CRYPTO_UPDOWN_SHADOW_POLICY,
) -> list[dict[str, Any]]:
    report = signal_report or score_pm_crypto_updown_signals(rows)
    rows_by_id = {str(row["clob_snapshot_id"]): row for row in rows}
    intents = [
        build_pm_crypto_updown_shadow_intent(
            row=rows_by_id[str(decision["row_id"])],
            decision=decision,
            config=config,
        )
        for decision in report["row_decisions"]
        if str(decision["row_id"]) in rows_by_id
    ]
    return sorted(intents, key=lambda item: (item["market_id"], item["token_id"]))


def build_pm_crypto_updown_shadow_intent(
    *,
    row: dict[str, Any],
    decision: dict[str, Any],
    config: PmCryptoUpdownShadowPolicyConfig = DEFAULT_PM_CRYPTO_UPDOWN_SHADOW_POLICY,
) -> dict[str, Any]:
    ask = _float(row.get("market_ask"))
    predicted_probability = _float(decision.get("predicted_probability"), default=0.5)
    spread = _float(row.get("market_spread"))
    liquidity = _float(row.get("market_liquidity"))
    latency_penalty = _latency_penalty(row, config)
    stale = _is_stale_clob(row, config)
    before_cost = predicted_probability - ask
    conservative_cost = (spread / 2.0) + config.fee_penalty + latency_penalty
    if stale:
        conservative_cost += config.stale_book_penalty
    after_cost = before_cost - conservative_cost
    max_acceptable_price = max(
        predicted_probability - conservative_cost - config.min_expected_edge_after_cost,
        0.0,
    )
    hypothetical_limit_price = min(ask, max_acceptable_price)
    no_fill_probability = _no_fill_probability(row)
    partial_fill_ratio = _partial_fill_ratio(row)
    blockers = _blockers(
        row=row,
        decision=decision,
        config=config,
        ask=ask,
        spread=spread,
        liquidity=liquidity,
        latency_penalty=latency_penalty,
        stale=stale,
        predicted_probability=predicted_probability,
        max_acceptable_price=max_acceptable_price,
        no_fill_probability=no_fill_probability,
        partial_fill_ratio=partial_fill_ratio,
        expected_edge_after_cost=after_cost,
    )
    primary_blocker = _primary_blocker(blockers)
    return {
        "candidate_id": CANDIDATE_ID,
        "row_id": row["clob_snapshot_id"],
        "market_id": row["market_id"],
        "token_id": row["token_id"],
        "outcome": row["outcome"],
        "event_ts": row.get("event_ts"),
        "side": "BUY" if decision.get("side") == "BUY" else "NO_TRADE",
        "hypothetical_limit_price": round(hypothetical_limit_price, 6),
        "observed_ask_price": round(ask, 6),
        "max_acceptable_price": round(max_acceptable_price, 6),
        "expected_edge_before_cost": round(before_cost, 6),
        "expected_edge_after_cost": round(after_cost, 6),
        "conservative_cost": round(conservative_cost, 6),
        "no_fill_probability": round(no_fill_probability, 6),
        "partial_fill_ratio": round(partial_fill_ratio, 6),
        "fill_assumption": _fill_assumption(blockers, partial_fill_ratio),
        "decision": "BLOCK_SHADOW_INTENT" if blockers else "ALLOW_SHADOW_INTENT",
        "blocker_reason": primary_blocker,
        "blocker_reasons": blockers,
        "data_quality_flags": sorted(set(row.get("data_quality_flags", []))),
        "risk_flags": _risk_flags(row),
        "source_quality": row.get("source_quality", "unknown"),
        "execution_authority": "NONE",
        "live_trading_enabled": False,
    }


def _blockers(
    *,
    row: dict[str, Any],
    decision: dict[str, Any],
    config: PmCryptoUpdownShadowPolicyConfig,
    ask: float,
    spread: float,
    liquidity: float,
    latency_penalty: float,
    stale: bool,
    predicted_probability: float,
    max_acceptable_price: float,
    no_fill_probability: float,
    partial_fill_ratio: float,
    expected_edge_after_cost: float,
) -> list[str]:
    blockers = []
    if decision.get("side") != "BUY":
        blockers.append("NO_SHADOW_SIGNAL")
    if spread > config.max_spread:
        blockers.append("SPREAD_TOO_WIDE")
    if liquidity < config.min_liquidity:
        blockers.append("LOW_LIQUIDITY")
    if stale:
        blockers.append("STALE_CLOB")
    if latency_penalty > config.max_latency_penalty:
        blockers.append("LATENCY_PENALTY_TOO_HIGH")
    if no_fill_probability > config.max_no_fill_probability:
        blockers.append("NO_FILL_PROBABILITY_TOO_HIGH")
    if partial_fill_ratio < config.min_partial_fill_ratio:
        blockers.append("PARTIAL_FILL_TOO_SMALL")
    if _float(row.get("seconds_to_window_end")) < config.min_time_to_window_end_seconds:
        blockers.append("TOO_CLOSE_TO_WINDOW_END")
    if predicted_probability < config.min_spot_lag_confidence:
        blockers.append("SPOT_LAG_CONFIDENCE_TOO_LOW")
    if ask > max_acceptable_price:
        blockers.append("PRICE_DISCIPLINE_FAILED")
    if expected_edge_after_cost < config.min_expected_edge_after_cost:
        blockers.append("EXPECTED_EDGE_AFTER_COST_TOO_LOW")
    return _sort_blockers(blockers)


def _primary_blocker(blockers: list[str]) -> str:
    if not blockers:
        return "NONE"
    ordered = _sort_blockers(blockers)
    return ordered[0]


def _sort_blockers(blockers: list[str]) -> list[str]:
    unique = set(blockers)
    return [item for item in BLOCKER_PRIORITY if item in unique] + sorted(
        unique - set(BLOCKER_PRIORITY)
    )


def _fill_assumption(blockers: list[str], partial_fill_ratio: float) -> str:
    if blockers:
        return "NO_HYPOTHETICAL_FILL"
    if partial_fill_ratio < 1.0:
        return "PARTIAL_FILL_ALLOWED"
    return "PASSIVE_LIMIT_NO_FILL_ALLOWED"


def _risk_flags(row: dict[str, Any]) -> list[str]:
    flags = ["OFFLINE_SHADOW_ONLY", "ZERO_TRADE_OUTCOME_ALLOWED"]
    if row.get("source_quality") == "synthetic_stress":
        flags.append("SYNTHETIC_STRESS_ONLY")
    return flags


def _is_stale_clob(
    row: dict[str, Any],
    config: PmCryptoUpdownShadowPolicyConfig,
) -> bool:
    flags = set(row.get("data_quality_flags", []))
    if "STALE_CLOB_SNAPSHOT" in flags:
        return True
    age = row.get("clob_age_seconds")
    return age is not None and _float(age) > config.max_stale_book_age_seconds


def _latency_penalty(
    row: dict[str, Any],
    config: PmCryptoUpdownShadowPolicyConfig,
) -> float:
    if row.get("latency_penalty") is not None:
        return _float(row["latency_penalty"])
    return config.default_latency_penalty


def _no_fill_probability(row: dict[str, Any]) -> float:
    if row.get("no_fill_probability") is not None:
        return _float(row["no_fill_probability"])
    return 0.25


def _partial_fill_ratio(row: dict[str, Any]) -> float:
    if row.get("expected_partial_fill_ratio") is not None:
        return _float(row["expected_partial_fill_ratio"])
    return 1.0


def _float(value: Any, *, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
