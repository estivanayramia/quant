from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

REPORT_ROOT = Path("reports/sequence49/profit_lane_tournament")

PROMOTE_TO_PAPER_PROVING = "PROMOTE_TO_PAPER_PROVING"
PROMOTE_TO_DATA_CAPTURE = "PROMOTE_TO_DATA_CAPTURE"
RESEARCH_ONLY = "RESEARCH_ONLY"
BLOCKED_SOURCE_UNAVAILABLE = "BLOCKED_SOURCE_UNAVAILABLE"
BLOCKED_EXECUTION_UNSAFE = "BLOCKED_EXECUTION_UNSAFE"
BLOCKED_COST_FILL_UNREALISTIC = "BLOCKED_COST_FILL_UNREALISTIC"
DEPRIORITIZED = "DEPRIORITIZED"
REJECTED = "REJECTED"

PROMOTABLE_STATUSES = {PROMOTE_TO_PAPER_PROVING, PROMOTE_TO_DATA_CAPTURE}

PROFIT_LANE_SAFETY = {
    "execution_authority": "NONE",
    "wallet_signing_enabled": False,
    "live_trading_enabled": False,
    "copy_trading_enabled": False,
    "real_orders_enabled": False,
    "order_placement_enabled": False,
    "order_cancellation_enabled": False,
    "prediction_market_execution_authority_added": False,
}

EVIDENCE_FIELDS = [
    "public_data_availability",
    "timestamp_quality",
    "label_resolution_quality",
    "historical_depth",
    "replayability",
    "oos_walk_forward_feasibility",
]
TRADING_REALISM_FIELDS = [
    "trade_frequency",
    "spread_liquidity",
    "fill_realism",
    "cost_burden",
    "slippage_sensitivity",
    "latency_sensitivity",
    "capacity_crowding_risk",
]
VALIDATION_FIELDS = [
    "baseline_testability",
    "placebo_testability",
    "anti_overfit_feasibility",
    "calibration_feasibility",
    "minimum_sample_feasibility",
    "oos_walk_forward_feasibility",
]
SAFETY_FIT_FIELDS = [
    "no_auth_wallet_order_requirement",
    "no_leverage_futures_margin_requirement",
    "no_copy_trade_dependency",
    "repo_compatibility",
    "time_to_honest_paper_evidence",
    "complexity",
]


def build_profit_lane_tournament(
    *,
    lane_overrides: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    lanes = [
        _score_lane(_apply_override(profile, lane_overrides or {}))
        for profile in _candidate_lane_profiles()
    ]
    lanes = sorted(lanes, key=lambda item: (-item["total_score"], item["lane_id"]))
    selected = _select_lane(lanes)
    status = _tournament_status(lanes=lanes, selected=selected)
    return {
        "schema_version": "profit_lane_tournament_v1",
        "sequence": "49",
        "tournament_status": status,
        "allowed_tournament_statuses": [
            "PAPER_PROVING_READY_FOR_SELECTED_LANE",
            "SELECTED_LANE_NEEDS_DATA_CAPTURE",
            "NO_TESTABLE_PROFIT_LANE_FOUND",
            "ALL_LANES_REJECTED_OR_RESEARCH_ONLY",
        ],
        "selected_lane_id": selected["lane_id"] if selected else None,
        "selected_lane": selected,
        "lanes": lanes,
        "scoring_model": {
            "scale": "0_to_5_higher_is_better",
            "evidence_fields": EVIDENCE_FIELDS,
            "trading_realism_fields": TRADING_REALISM_FIELDS,
            "validation_fields": VALIDATION_FIELDS,
            "safety_fit_fields": SAFETY_FIT_FIELDS,
            "score_is_path_to_proof_not_profit": True,
        },
        "decision_rules": [
            "Do not promote lanes requiring private/authenticated data, wallets, orders, or copy trading.",
            "Do not promote futures, leverage, or margin lanes under current doctrine.",
            "Prefer lanes with public data, labels, replayability, costs, fills, baselines, and placebos.",
            "Treat synthetic fixtures as plumbing tests only, never profitability evidence.",
            "Allow no-edge or no-testable-lane outcomes.",
        ],
        "profit_claim_made": False,
        **PROFIT_LANE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_profit_lane_tournament_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_profit_lane_tournament()
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _apply_override(
    profile: dict[str, Any],
    lane_overrides: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    copied = copy.deepcopy(profile)
    override = lane_overrides.get(copied["lane_id"])
    if not override:
        return copied
    return _deep_merge(copied, override)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key] = _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def _score_lane(profile: dict[str, Any]) -> dict[str, Any]:
    evidence_score = _category_score(profile["evidence"], EVIDENCE_FIELDS)
    trading_score = _category_score(profile["trading_realism"], TRADING_REALISM_FIELDS)
    validation_score = _category_score(profile["validation"], VALIDATION_FIELDS)
    safety_score = _category_score(profile["safety_fit"], SAFETY_FIT_FIELDS)
    promotion_status = _enforced_status(profile)
    blockers = _blockers(profile=profile, promotion_status=promotion_status)
    total_score = evidence_score + trading_score + validation_score + safety_score
    if promotion_status not in PROMOTABLE_STATUSES:
        total_score = max(total_score - _blocker_penalty(promotion_status), 0)
    return {
        **profile,
        "promotion_status": promotion_status,
        "category_scores": {
            "evidence": evidence_score,
            "trading_realism": trading_score,
            "validation": validation_score,
            "safety_fit": safety_score,
        },
        "total_score": total_score,
        "blockers": blockers,
        "profit_claim_made": False,
    }


def _category_score(scores: dict[str, int], fields: list[str]) -> int:
    return sum(_bounded_score(scores.get(field, 0)) for field in fields)


def _bounded_score(value: Any) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        return 0
    return min(max(score, 0), 5)


def _enforced_status(profile: dict[str, Any]) -> str:
    if profile.get("requires_wallet_or_signing") or profile.get("on_chain_execution_risk"):
        return BLOCKED_EXECUTION_UNSAFE
    if profile.get("requires_private_auth"):
        return BLOCKED_SOURCE_UNAVAILABLE
    if profile.get("copy_trade_dependency"):
        return REJECTED
    if profile.get("blocked_source_fields"):
        return BLOCKED_SOURCE_UNAVAILABLE
    if profile.get("requires_futures_or_margin"):
        return RESEARCH_ONLY
    if profile.get("cost_fill_unrealistic"):
        return BLOCKED_COST_FILL_UNREALISTIC
    return str(profile["promotion_status"])


def _blockers(*, profile: dict[str, Any], promotion_status: str) -> list[str]:
    blockers = list(profile.get("blockers", []))
    if profile.get("blocked_source_fields"):
        blockers.append("BLOCKED_MISSING_PUBLIC_FILL_ATTRIBUTION")
    if profile.get("requires_private_auth"):
        blockers.append("PRIVATE_OR_AUTHENTICATED_SOURCE_REQUIRED")
    if profile.get("requires_wallet_or_signing"):
        blockers.append("WALLET_OR_SIGNING_REQUIRED")
    if profile.get("on_chain_execution_risk"):
        blockers.append("ON_CHAIN_EXECUTION_RISK")
    if profile.get("requires_futures_or_margin"):
        blockers.append("FUTURES_LEVERAGE_OR_MARGIN_OUT_OF_SCOPE")
    if profile.get("copy_trade_dependency"):
        blockers.append("COPY_TRADE_DEPENDENCY_FORBIDDEN")
    if promotion_status == BLOCKED_COST_FILL_UNREALISTIC:
        blockers.append("COST_FILL_REALISM_NOT_PLAUSIBLE")
    return _dedupe(blockers)


def _blocker_penalty(status: str) -> int:
    return {
        RESEARCH_ONLY: 18,
        DEPRIORITIZED: 22,
        BLOCKED_SOURCE_UNAVAILABLE: 28,
        BLOCKED_COST_FILL_UNREALISTIC: 32,
        BLOCKED_EXECUTION_UNSAFE: 45,
        REJECTED: 50,
    }.get(status, 0)


def _select_lane(lanes: list[dict[str, Any]]) -> dict[str, Any] | None:
    promotable = [lane for lane in lanes if lane["promotion_status"] in PROMOTABLE_STATUSES]
    if not promotable:
        return None
    return sorted(promotable, key=lambda item: (-item["total_score"], item["lane_id"]))[0]


def _tournament_status(
    *,
    lanes: list[dict[str, Any]],
    selected: dict[str, Any] | None,
) -> str:
    if selected is None:
        if all(lane["promotion_status"] in {RESEARCH_ONLY, DEPRIORITIZED, REJECTED} for lane in lanes):
            return "ALL_LANES_REJECTED_OR_RESEARCH_ONLY"
        return "NO_TESTABLE_PROFIT_LANE_FOUND"
    if selected["promotion_status"] == PROMOTE_TO_PAPER_PROVING:
        return "PAPER_PROVING_READY_FOR_SELECTED_LANE"
    return "SELECTED_LANE_NEEDS_DATA_CAPTURE"


def _candidate_lane_profiles() -> list[dict[str, Any]]:
    return [
        _lane(
            "pm_weather_forecast_market_mismatch",
            "prediction_market",
            "Forecast probability or bucket estimate versus market-implied probability mismatch.",
            promotion_status=PROMOTE_TO_DATA_CAPTURE,
            evidence=[5, 4, 5, 3, 4, 4],
            trading=[2, 4, 3, 4, 4, 3, 3],
            validation=[5, 5, 4, 4, 3, 4],
            safety=[5, 5, 5, 4, 4, 4],
            required_data=[
                "forecast snapshots",
                "forecast source timestamp",
                "market metadata",
                "bucket/range rules",
                "price snapshots",
                "liquidity/spread",
                "resolution labels",
                "event timestamps",
            ],
            first_replay_schema="weather_bucket_forecast_market_snapshot_v1",
            rationale="Public forecast and resolution sources look slower and cleaner than high-frequency fill attribution lanes, but a real replay dataset still has to be captured.",
        ),
        _lane(
            "pm_cross_market_equivalence_arbitrage",
            "prediction_market",
            "Related markets with violated logical relationships.",
            promotion_status=PROMOTE_TO_DATA_CAPTURE,
            evidence=[4, 4, 4, 3, 4, 3],
            trading=[3, 3, 3, 3, 3, 3, 2],
            validation=[4, 5, 3, 3, 3, 3],
            safety=[5, 5, 5, 3, 3, 2],
            required_data=[
                "market metadata",
                "semantic relation mapping",
                "orderbook snapshots",
                "fees/spreads/liquidity",
                "resolution labels",
                "timestamps",
            ],
            first_replay_schema="cross_market_relation_orderbook_snapshot_v1",
            rationale="Testable, but semantic relation mapping has more ambiguity and model-risk than weather buckets.",
        ),
        _lane(
            "pm_resolution_rule_mispricing",
            "prediction_market",
            "Rule or definition misunderstanding in market prices.",
            promotion_status=RESEARCH_ONLY,
            evidence=[4, 3, 4, 2, 3, 2],
            trading=[1, 3, 2, 3, 3, 2, 2],
            validation=[3, 3, 3, 3, 2, 2],
            safety=[5, 5, 5, 3, 2, 2],
            required_data=["rule text", "public sources", "resolution history", "price snapshots"],
            first_replay_schema="resolution_rule_price_snapshot_v1",
            rationale="Often too subjective or legally ambiguous for a deterministic first proving lane.",
        ),
        _lane(
            "pm_crypto_updown_repricing_lag_revival",
            "prediction_market",
            "Previous crypto up/down repricing-lag lane.",
            promotion_status=DEPRIORITIZED,
            evidence=[3, 4, 4, 2, 3, 2],
            trading=[4, 2, 2, 2, 2, 2, 2],
            validation=[3, 3, 3, 2, 2, 2],
            safety=[5, 5, 5, 3, 2, 3],
            blockers=["FRESH_ALLOWED_PRIMARY_INTENTS_REQUIRED"],
            required_data=["fresh allowed primary intents", "resolved windows", "cost/fill replay"],
            first_replay_schema="pm_crypto_updown_allowed_intent_v1",
            rationale="Explicitly deprioritized unless fresh allowed primary intent evidence appears.",
        ),
        _lane(
            "pm_lp_refresh_lag_arbitrage",
            "prediction_market",
            "LP refresh lag around stale quotes after spot triggers.",
            promotion_status=BLOCKED_SOURCE_UNAVAILABLE,
            evidence=[3, 4, 4, 2, 2, 1],
            trading=[4, 3, 1, 2, 1, 1, 2],
            validation=[3, 4, 2, 2, 1, 1],
            safety=[3, 5, 5, 4, 1, 2],
            blocked_source_fields=["maker_taker_role", "maker_wallet_order_attribution"],
            required_data=[
                "public quote lifecycle",
                "exact maker/taker role",
                "maker wallet/order attribution",
            ],
            first_replay_schema="pm_lp_refresh_lag_public_source_sample_v1",
            rationale="Phase 48 showed exact maker/taker and maker-wallet/order attribution are not public.",
        ),
        _lane(
            "crypto_spot_momentum_reversion_intraday",
            "crypto_spot",
            "Spot-only intraday momentum or mean-reversion for BTC/ETH/SOL.",
            promotion_status=PROMOTE_TO_DATA_CAPTURE,
            evidence=[5, 5, 3, 4, 5, 4],
            trading=[4, 4, 3, 3, 3, 3, 3],
            validation=[5, 5, 4, 3, 3, 4],
            safety=[5, 5, 5, 4, 3, 3],
            required_data=["public candles", "public orderbook snapshots if available", "fees", "spreads"],
            first_replay_schema="crypto_spot_signal_bar_replay_v1",
            rationale="Highly testable, but crowded and cost-sensitive enough to rank behind cleaner weather provenance.",
        ),
        _lane(
            "crypto_cross_exchange_spot_arbitrage",
            "crypto_spot",
            "Spot price divergence across exchanges.",
            promotion_status=RESEARCH_ONLY,
            evidence=[5, 5, 2, 4, 4, 3],
            trading=[5, 3, 2, 1, 1, 1, 1],
            validation=[3, 3, 3, 2, 2, 3],
            safety=[5, 5, 5, 2, 2, 2],
            blockers=["INVENTORY_FEES_WITHDRAWAL_LATENCY_NOT_MODELED"],
            required_data=["cross-exchange orderbooks", "fees", "withdrawal constraints", "latency"],
            first_replay_schema="crypto_cross_exchange_public_book_snapshot_v1",
            rationale="Research-only without inventory, withdrawal, fee, and latency modeling.",
        ),
        _lane(
            "crypto_triangular_arbitrage",
            "crypto_spot",
            "Three-leg spot mispricing.",
            promotion_status=RESEARCH_ONLY,
            evidence=[5, 5, 2, 4, 4, 3],
            trading=[5, 2, 2, 1, 1, 1, 1],
            validation=[3, 3, 3, 2, 2, 3],
            safety=[5, 5, 5, 2, 2, 2],
            blockers=["CROWDED_FEE_SENSITIVE_REQUIRES_ORDERBOOK_REPLAY"],
            required_data=["three-leg public orderbooks", "fees", "slippage", "latency"],
            first_replay_schema="crypto_triangular_public_book_replay_v1",
            rationale="Likely crowded and fee-sensitive until public orderbook replay says otherwise.",
        ),
        _lane(
            "crypto_stat_arb_pairs",
            "crypto_spot",
            "Spot-only pairs or cointegration-style mean reversion.",
            promotion_status=PROMOTE_TO_DATA_CAPTURE,
            evidence=[5, 5, 3, 4, 5, 4],
            trading=[3, 4, 3, 3, 3, 3, 3],
            validation=[5, 5, 5, 4, 3, 4],
            safety=[5, 5, 5, 4, 3, 3],
            required_data=["historical spot data", "spreads", "fees", "OOS splits"],
            first_replay_schema="crypto_spot_pairs_walk_forward_v1",
            rationale="Statistically testable, but shorting/live structure remains constrained to spot-only paper simulation.",
        ),
        _lane(
            "crypto_volatility_regime_signal",
            "crypto_spot",
            "Spot-only volatility breakout or reversion signal.",
            promotion_status=PROMOTE_TO_DATA_CAPTURE,
            evidence=[5, 5, 3, 4, 5, 4],
            trading=[3, 4, 3, 3, 3, 3, 3],
            validation=[5, 5, 4, 4, 3, 4],
            safety=[5, 5, 5, 4, 3, 3],
            required_data=["public candles", "spread assumptions", "walk-forward splits"],
            first_replay_schema="crypto_volatility_regime_walk_forward_v1",
            rationale="Paper-testable but needs robust OOS and cost sensitivity before it can beat simpler baselines.",
        ),
        _lane(
            "defi_cex_dex_arbitrage",
            "defi",
            "CEX/DEX arbitrage.",
            promotion_status=BLOCKED_EXECUTION_UNSAFE,
            evidence=[3, 3, 2, 2, 2, 2],
            trading=[4, 1, 1, 1, 1, 1, 1],
            validation=[2, 2, 2, 2, 1, 2],
            safety=[1, 5, 5, 1, 1, 1],
            requires_wallet_or_signing=True,
            on_chain_execution_risk=True,
            required_data=["DEX quotes", "CEX books", "gas", "MEV assumptions"],
            first_replay_schema="defi_cex_dex_simulation_only_v1",
            rationale="Gas, MEV, wallets, and on-chain signing keep this out of the current live path.",
        ),
        _lane(
            "funding_basis_arbitrage",
            "basis",
            "Funding or basis arbitrage using perps/futures.",
            promotion_status=RESEARCH_ONLY,
            evidence=[5, 5, 3, 4, 4, 3],
            trading=[4, 4, 3, 3, 3, 3, 3],
            validation=[4, 4, 4, 3, 3, 3],
            safety=[5, 1, 5, 2, 2, 2],
            requires_futures_or_margin=True,
            required_data=["futures funding", "spot prices", "margin requirements"],
            first_replay_schema="funding_basis_research_only_v1",
            rationale="Futures, perps, leverage, and margin are outside current doctrine.",
        ),
        _lane(
            "uniswap_v3_lp_strategy",
            "defi",
            "Uniswap v3 liquidity provisioning.",
            promotion_status=RESEARCH_ONLY,
            evidence=[4, 4, 2, 3, 3, 3],
            trading=[2, 2, 2, 1, 2, 2, 2],
            validation=[3, 3, 3, 2, 2, 3],
            safety=[1, 5, 5, 1, 1, 1],
            requires_wallet_or_signing=True,
            on_chain_execution_risk=True,
            required_data=["pool states", "gas", "LVR", "fee tiers"],
            first_replay_schema="uniswap_v3_lp_research_only_v1",
            rationale="Wallet, gas, LVR, and on-chain execution complexity block current promotion.",
        ),
    ]


def _lane(
    lane_id: str,
    family: str,
    description: str,
    *,
    promotion_status: str,
    evidence: list[int],
    trading: list[int],
    validation: list[int],
    safety: list[int],
    required_data: list[str],
    first_replay_schema: str,
    rationale: str,
    blockers: list[str] | None = None,
    blocked_source_fields: list[str] | None = None,
    requires_private_auth: bool = False,
    requires_wallet_or_signing: bool = False,
    requires_futures_or_margin: bool = False,
    copy_trade_dependency: bool = False,
    on_chain_execution_risk: bool = False,
    cost_fill_unrealistic: bool = False,
) -> dict[str, Any]:
    return {
        "lane_id": lane_id,
        "family": family,
        "description": description,
        "promotion_status": promotion_status,
        "evidence": dict(zip(EVIDENCE_FIELDS, evidence, strict=True)),
        "trading_realism": dict(zip(TRADING_REALISM_FIELDS, trading, strict=True)),
        "validation": dict(zip(VALIDATION_FIELDS, validation, strict=True)),
        "safety_fit": dict(zip(SAFETY_FIT_FIELDS, safety, strict=True)),
        "required_data": required_data,
        "first_replay_schema": first_replay_schema,
        "rationale": rationale,
        "blockers": blockers or [],
        "blocked_source_fields": blocked_source_fields or [],
        "requires_private_auth": requires_private_auth,
        "requires_wallet_or_signing": requires_wallet_or_signing,
        "requires_futures_or_margin": requires_futures_or_margin,
        "copy_trade_dependency": copy_trade_dependency,
        "on_chain_execution_risk": on_chain_execution_risk,
        "cost_fill_unrealistic": cost_fill_unrealistic,
    }


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_profit_lane_tournament.json"
    md_path = root / "latest_profit_lane_tournament.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 49 Profit Lane Tournament",
        "",
        "Ranks path-to-proof only. No profitability, canary, or live-readiness claim.",
        "",
        f"Status: {payload['tournament_status']}",
        f"Selected lane: {payload['selected_lane_id']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        f"Execution authority: {payload['execution_authority']}",
        "",
        "## Ranked Lanes",
    ]
    lines.extend(
        "- {lane_id}: score={score}, status={status}".format(
            lane_id=lane["lane_id"],
            score=lane["total_score"],
            status=lane["promotion_status"],
        )
        for lane in payload["lanes"]
    )
    lines.extend(["", "## Decision Rules"])
    lines.extend(f"- {item}" for item in payload["decision_rules"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped = []
    for item in items:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped
