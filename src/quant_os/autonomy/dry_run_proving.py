from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from quant_os.autonomy.proving_health import (
    Sequence2ReadinessStatus,
    evaluate_sequence2_readiness,
)
from quant_os.autonomy.proving_reports import write_dry_run_proving_report
from quant_os.replay.liquidity_filters import LiquidityGate, LiquidityPolicy
from quant_os.replay.realism_report import write_replay_realism_report
from quant_os.research.crypto.candidate_strategies import (
    CryptoSignal,
    generate_crypto_candidate_signals,
)
from quant_os.research.crypto.features import build_crypto_features
from quant_os.research.crypto.ingest import build_crypto_research_dataset
from quant_os.research.validation.walk_forward import run_crypto_walk_forward


@dataclass(frozen=True)
class DryRunProvingConfig:
    periods: int = 180
    min_edge_bps: float = 4.0
    max_order_quantity: float = 0.01
    max_quote_age_ms: float = 5_000.0
    min_liquidity_score: float = 0.25
    min_top_of_book_notional: float = 500.0
    max_drift_bps: float = 10.0
    output_root: str | Path = "."


def run_dry_run_proving_cycle(
    *,
    frame: pd.DataFrame | None = None,
    config: DryRunProvingConfig | None = None,
    walk_forward_summary: dict[str, Any] | None = None,
    realism_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = config or DryRunProvingConfig()
    raw_frame = (
        frame.copy()
        if frame is not None
        else build_crypto_research_dataset(periods=cfg.periods).frame
    )
    features = build_crypto_features(raw_frame)
    gate = LiquidityGate(
        policy=LiquidityPolicy(
            min_liquidity_score=cfg.min_liquidity_score,
            min_top_of_book_notional=cfg.min_top_of_book_notional,
            max_quote_age_ms=cfg.max_quote_age_ms,
        )
    )
    signals = _select_signals(features, cfg)
    proposals = [_proposal_from_signal(signal, cfg) for signal in signals]
    proposals.extend(_stale_book_health_checks(features, cfg))

    allowed = []
    blocked = []
    for proposal in proposals:
        row = _row_for_proposal(features, proposal)
        reasons = _block_reasons(proposal, row, gate, cfg)
        if reasons:
            proposal["status"] = "BLOCKED"
            proposal["block_reasons"] = reasons
            blocked.append(proposal)
        else:
            proposal["status"] = "ALLOWED_FOR_DRY_RUN_ONLY"
            proposal["block_reasons"] = []
            allowed.append(proposal)

    wf = walk_forward_summary or run_crypto_walk_forward(
        raw_frame,
        output_root=cfg.output_root,
        train_bars=30,
        validation_bars=15,
        test_bars=15,
        step_bars=15,
    )
    realism = realism_summary or write_replay_realism_report(
        periods=cfg.periods,
        output_root=cfg.output_root,
    )
    average_edge = _average_expected_edge(allowed)
    replay_to_dry_run_drift_bps = abs(
        average_edge
        - float(wf.get("aggregate", {}).get("mean_test_expectancy_after_costs_bps", 0.0))
    )
    warnings = []
    if replay_to_dry_run_drift_bps > cfg.max_drift_bps:
        warnings.append("REPLAY_DRY_RUN_DRIFT_TOO_HIGH")
    if not allowed:
        warnings.append("NO_ALLOWED_DRY_RUN_ACTIONS")
    block_reasons = sorted({reason for item in blocked for reason in item["block_reasons"]})
    status = _proving_status(allowed=allowed, warnings=warnings)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": status,
        "cycle_count": 1,
        "order_proposals": proposals,
        "allowed_action_count": len(allowed),
        "blocked_action_count": len(blocked),
        "block_reasons": block_reasons,
        "warnings": sorted(set(warnings)),
        "average_allowed_expected_edge_bps": average_edge,
        "replay_to_dry_run_drift_bps": float(replay_to_dry_run_drift_bps),
        "walk_forward_status": wf.get("status"),
        "realism_status": realism.get("status"),
        "edge_concentration": _edge_concentration(allowed),
        "live_trading_enabled": False,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
    }
    payload["readiness"] = evaluate_sequence2_readiness(
        walk_forward_summary=wf,
        proving_summary=payload,
        validation_summary={
            "status": "PASS",
            "unsafe_action_failure_count": 0,
            "live_trading_enabled": False,
        },
        realism_summary=realism,
        max_drift_bps=cfg.max_drift_bps,
    )
    payload["report_paths"] = write_dry_run_proving_report(
        payload,
        output_root=cfg.output_root,
    )
    return payload


def _proving_status(*, allowed: list[dict[str, Any]], warnings: list[str]) -> str:
    if "REPLAY_DRY_RUN_DRIFT_TOO_HIGH" in warnings:
        return Sequence2ReadinessStatus.BLOCKED.value
    if not allowed:
        return Sequence2ReadinessStatus.NOT_READY.value
    if warnings:
        return Sequence2ReadinessStatus.PROVING_WITH_WARNINGS.value
    return Sequence2ReadinessStatus.PROVING.value


def _select_signals(frame: pd.DataFrame, config: DryRunProvingConfig) -> list[CryptoSignal]:
    signals = [
        signal
        for signal in generate_crypto_candidate_signals(frame, min_edge_bps=config.min_edge_bps)
        if signal.strategy_id != "random_placebo"
    ]
    return sorted(signals, key=lambda item: (item.timestamp, item.symbol, item.strategy_id))[:20]


def _proposal_from_signal(signal: CryptoSignal, config: DryRunProvingConfig) -> dict[str, Any]:
    return {
        "strategy_id": signal.strategy_id,
        "symbol": signal.symbol,
        "timestamp": pd.Timestamp(signal.timestamp).isoformat(),
        "side": signal.side,
        "quantity": min(config.max_order_quantity, max(0.0, signal.strength * config.max_order_quantity)),
        "expected_edge_bps": signal.expected_edge_bps,
        "confidence": signal.confidence,
        "reason_code": signal.reason_code,
        "source": "crypto_candidate_signal",
    }


def _stale_book_health_checks(
    frame: pd.DataFrame,
    config: DryRunProvingConfig,
) -> list[dict[str, Any]]:
    if "quote_age_ms" not in frame:
        return []
    stale = frame[frame["quote_age_ms"].fillna(0.0) > config.max_quote_age_ms]
    proposals = []
    for _, row in stale.tail(5).iterrows():
        proposals.append(
            {
                "strategy_id": "market_data_health_check",
                "symbol": str(row["symbol"]),
                "timestamp": pd.Timestamp(row["timestamp"]).isoformat(),
                "side": "BUY",
                "quantity": 0.0,
                "expected_edge_bps": 0.0,
                "confidence": 0.0,
                "reason_code": "STALE_BOOK_HEALTH_CHECK",
                "source": "data_quality_probe",
            }
        )
    return proposals


def _row_for_proposal(frame: pd.DataFrame, proposal: dict[str, Any]) -> pd.Series:
    symbol_frame = frame[frame["symbol"] == proposal["symbol"]].sort_values("timestamp")
    timestamp = pd.Timestamp(proposal["timestamp"])
    matches = symbol_frame[symbol_frame["timestamp"] == timestamp]
    if not matches.empty:
        return matches.iloc[0]
    return symbol_frame.iloc[-1]


def _block_reasons(
    proposal: dict[str, Any],
    row: pd.Series,
    gate: LiquidityGate,
    config: DryRunProvingConfig,
) -> list[str]:
    reasons = []
    if not proposal.get("reason_code"):
        reasons.append("MISSING_REASON_CODE")
    if float(proposal.get("expected_edge_bps", 0.0)) < config.min_edge_bps:
        reasons.append("EDGE_BELOW_THRESHOLD")
    decision = gate.evaluate(row)
    if not decision.allowed and decision.reason:
        reasons.append(decision.reason)
    if float(proposal.get("quantity", 0.0)) > config.max_order_quantity:
        reasons.append("ORDER_SIZE_EXCEEDS_DRY_RUN_CAP")
    return sorted(set(reasons))


def _average_expected_edge(proposals: list[dict[str, Any]]) -> float:
    if not proposals:
        return 0.0
    return float(pd.Series([float(item["expected_edge_bps"]) for item in proposals]).mean())


def _edge_concentration(proposals: list[dict[str, Any]]) -> dict[str, Any]:
    if not proposals:
        return {"top_strategy_share": 0.0, "top_strategy_id": None}
    counts = pd.Series([item["strategy_id"] for item in proposals]).value_counts()
    return {
        "top_strategy_id": str(counts.index[0]),
        "top_strategy_share": float(counts.iloc[0] / counts.sum()),
    }
