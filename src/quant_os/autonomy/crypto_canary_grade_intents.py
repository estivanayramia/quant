from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.autonomy.canary_grade_live_sim_common import (
    ROOT,
    canary_safe_payload,
    cg_hash,
    update_state_from_payload,
)
from quant_os.autonomy.live_market_sim_common import load_json
from quant_os.readiness.canary_readiness_common import write_json_markdown_report

REPORT_DIR = ROOT / "crypto"
CANARY_PROOF_MARK_HORIZONS = {15, 60}
CANARY_PROOF_EXCLUDED_SESSION_BUCKETS = {"session_5"}
CANARY_SIGNAL_QUALITY_GATE = (
    "broad_kraken_60m_reversion_plus_selected_15m_momentum_cost_hurdled_no_session5"
)
CANARY_REVERSION_60M_SYMBOLS = {
    "ADA/USD",
    "AKT/USD",
    "BCH/USD",
    "BILL/USD",
    "BNB/USD",
    "BTC/USD",
    "DASH/USD",
    "DOGE/USD",
    "ETH/USD",
    "FUN/USD",
    "HYPE/USD",
    "ICP/USD",
    "MNT/USD",
    "PLUME/USD",
    "POL/USD",
    "RED/USD",
    "TRX/USD",
    "WLD/USD",
    "XRP/USD",
    "XTZ/USD",
}
CANARY_MOMENTUM_15M_SYMBOLS = {
    "FUN/USD",
    "HYPE/USD",
    "MNT/USD",
}


def build_crypto_canary_grade_intents(
    *,
    output_root: str | Path = ".",
    observer: dict[str, Any] | None = None,
    max_intents: int = 1500,
) -> dict[str, Any]:
    observer = observer or load_json(
        "reports/canary_grade_live_sim/crypto/latest_observer.json",
        output_root=output_root,
    ) or {}
    intents = []
    for observation in list(observer.get("observations", []) or []):
        if not observation.get("eligible"):
            continue
        if not _passes_canary_signal_quality_gate(observation):
            continue
        side = _canary_side_for_observation(observation)
        if side is None:
            continue
        notional_usd = 1.0
        entry_price = float(observation["entry_price"])
        quantity = round(notional_usd / entry_price, 8) if entry_price > 0.0 else 0.0
        if quantity <= 0.0:
            continue
        intents.append(
            {
                "fake_client_order_id": f"cgint_{cg_hash(observation)}",
                "observation_id": observation["observation_id"],
                "symbol": observation["symbol"],
                "strategy": observation["strategy"],
                "venue": observation["venue"],
                "side": side,
                "quantity": quantity,
                "notional_usd": notional_usd,
                "limit_price": round(float(observation["entry_price"]) + float(observation["spread"]) / 2, 8),
                "entry_timestamp": observation["entry_timestamp"],
                "mark_timestamp": observation["mark_timestamp"],
                "mark_price": observation["mark_price"],
                "mark_horizon_minutes": observation.get("mark_horizon_minutes"),
                "return_1m": observation.get("return_1m"),
                "regime": observation["regime"],
                "walk_forward_window": observation["walk_forward_window"],
                "session_bucket": observation["session_bucket"],
                "fake_money": True,
                "no_transmit": True,
                "signal_quality_gate": CANARY_SIGNAL_QUALITY_GATE,
                "dry_run_only": True,
                "order_transmission_enabled": False,
                "authenticated_requests_enabled": False,
                "request_signing_enabled": False,
                "contains_signed_headers": False,
                "contains_private_key_path": False,
                "contains_executable_submission_code": False,
                "blocked_capabilities": ["private_order_submission", "portfolio_access", "request_signing"],
                "evidence_hash": cg_hash({"intent_observation": observation}),
            }
        )
        if len(intents) >= max_intents:
            break
    return canary_safe_payload(
        schema_version="crypto_canary_grade_intents_v1",
        status="CANARY_GRADE_INTENTS_READY" if intents else "CANARY_GRADE_NO_ELIGIBLE_INTENTS",
        intents=intents,
        eligible_intent_count=len(intents),
        assets_tested=sorted({intent["symbol"] for intent in intents}),
        strategy_families_tested=sorted({intent["strategy"] for intent in intents}),
        regime_buckets=sorted({intent["regime"] for intent in intents}),
        walk_forward_windows=sorted({intent["walk_forward_window"] for intent in intents}),
        fake_money=True,
        no_transmit=True,
        blockers=[],
        next_action="Apply canary-grade conservative fake fill model.",
    )


def _passes_canary_signal_quality_gate(observation: dict[str, Any]) -> bool:
    horizon = int(observation.get("mark_horizon_minutes") or 0)
    if horizon not in CANARY_PROOF_MARK_HORIZONS:
        return False
    if observation.get("session_bucket") in CANARY_PROOF_EXCLUDED_SESSION_BUCKETS:
        return False
    raw_ret = float(observation.get("return_1m") or 0.0)
    ret = abs(raw_ret)
    if horizon <= 0 or raw_ret == 0.0:
        return False
    strategy = str(observation.get("strategy") or "").lower()
    symbol = str(observation.get("symbol") or "")
    reversion_sleeve = (
        horizon == 60
        and symbol in CANARY_REVERSION_60M_SYMBOLS
        and "liquidity_shock_reversion" in strategy
        and raw_ret < 0.0
    )
    momentum_sleeve = (
        horizon == 15
        and symbol in CANARY_MOMENTUM_15M_SYMBOLS
        and "momentum" in strategy
        and raw_ret > 0.0
    )
    if not (reversion_sleeve or momentum_sleeve):
        return False
    entry = float(observation.get("entry_price") or 0.0)
    if entry <= 0.0:
        return False
    notional_usd = 1.0
    quantity = notional_usd / entry
    spread = float(observation.get("spread") or 0.0)
    spread_cost = spread * 1.5 * quantity
    slippage_cost = entry * quantity * 0.5 / 10000.0
    fee_cost = entry * quantity * 0.5 / 10000.0
    cost_hurdle = spread_cost + slippage_cost + fee_cost
    expected_move_notional = ret * notional_usd
    return expected_move_notional > cost_hurdle


def _canary_side_for_observation(observation: dict[str, Any]) -> str | None:
    strategy = str(observation.get("strategy") or "").lower()
    ret = float(observation.get("return_1m") or 0.0)
    if ret == 0.0:
        return None
    if "liquidity_shock_reversion" in strategy:
        return "buy" if ret < 0.0 else None
    if "momentum" in strategy:
        if ret > 0.0 and (ret > 0.001 or observation.get("session_bucket") == "session_0"):
            return "buy"
        return None
    if "reversion" in strategy or "reversal" in strategy or "snapback" in strategy:
        return "buy" if ret < 0.0 else None
    return None


def write_crypto_canary_grade_intents_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_crypto_canary_grade_intents(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_intents.json",
        md_name="latest_intents.md",
        title="Crypto Canary-Grade Intents",
        summary="Large-sample fake-money no-transmit crypto intents.",
    )
    update_state_from_payload(output_root=output_root, payload=payload)
    return payload
