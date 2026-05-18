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


def apply_crypto_canary_grade_fill_model(
    *,
    intents: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    spread_multiplier: float = 1.5,
    slippage_bps: float = 0.5,
    fee_bps: float = 0.5,
) -> dict[str, Any]:
    by_id = {item["observation_id"]: item for item in observations}
    fills: list[dict[str, Any]] = []
    no_fills: list[dict[str, Any]] = []
    for intent in intents:
        observation = by_id.get(intent["observation_id"])
        if not observation:
            no_fills.append({"fake_client_order_id": intent["fake_client_order_id"], "status": "MISSING_OBSERVATION"})
            continue
        entry = float(observation["entry_price"])
        spread = float(observation.get("spread") or 0.0) * spread_multiplier
        ask_size = float(observation.get("ask_size") or 0.0)
        if ask_size <= 0:
            no_fills.append({"fake_client_order_id": intent["fake_client_order_id"], "status": "NO_PUBLIC_LIQUIDITY"})
            continue
        quantity = min(float(intent.get("quantity") or 1.0), max(ask_size / 10.0, 0.0), 1.0)
        if quantity <= 0:
            no_fills.append({"fake_client_order_id": intent["fake_client_order_id"], "status": "ZERO_CONSERVATIVE_SIZE"})
            continue
        fills.append(
            {
                "fake_fill_id": f"cgfill_{cg_hash({'intent': intent, 'observation': observation})}",
                "fake_client_order_id": intent["fake_client_order_id"],
                "observation_id": intent["observation_id"],
                "symbol": intent["symbol"],
                "strategy": intent["strategy"],
                "venue": intent["venue"],
                "side": intent["side"],
                "quantity": round(quantity, 8),
                "entry_timestamp": intent["entry_timestamp"],
                "entry_price": entry,
                "mark_timestamp": intent["mark_timestamp"],
                "mark_price": float(intent["mark_price"]),
                "regime": intent["regime"],
                "walk_forward_window": intent["walk_forward_window"],
                "session_bucket": intent["session_bucket"],
                "spread": spread,
                "spread_cost": round(spread * quantity, 8),
                "slippage_cost": round(entry * quantity * slippage_bps / 10000.0, 8),
                "fee_cost": round(entry * quantity * fee_bps / 10000.0, 8),
                "latency_penalty_bps": 0.5,
                "adverse_selection_stress_bps": 0.5,
                "public_depth_notional": float(observation.get("public_depth_notional") or 0.0),
                "guaranteed_fill": False,
                "conservative_partial_fill": quantity < float(intent.get("quantity") or 1.0),
                "evidence_hash": cg_hash({"fill": intent, "spread": spread, "ask_size": ask_size}),
            }
        )
    payload = canary_safe_payload(
        schema_version="crypto_canary_grade_fill_v1",
        status="CANARY_GRADE_FILLS_APPLIED" if fills else "CANARY_GRADE_NO_FILLS",
        fake_fills=fills,
        fake_no_fills=no_fills,
        fake_fill_count=len(fills),
        fake_no_fill_count=len(no_fills),
        guaranteed_fill=False,
        fill_model="conservative_public_depth_partial_fill_with_spread_slippage_fee_latency_adverse_stress",
        blockers=[],
        next_action="Update canary-grade fake ledger.",
    )
    return payload


def build_crypto_canary_grade_fill(*, output_root: str | Path = ".") -> dict[str, Any]:
    intents = load_json("reports/canary_grade_live_sim/crypto/latest_intents.json", output_root=output_root) or {}
    observer = load_json("reports/canary_grade_live_sim/crypto/latest_observer.json", output_root=output_root) or {}
    return apply_crypto_canary_grade_fill_model(
        intents=list(intents.get("intents", []) or []),
        observations=list(observer.get("observations", []) or []),
    )


def write_crypto_canary_grade_fill_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_crypto_canary_grade_fill(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_fills.json",
        md_name="latest_fills.md",
        title="Crypto Canary-Grade Fill",
        summary="Conservative fake fill/no-fill model for canary-grade crypto simulation.",
    )
    update_state_from_payload(output_root=output_root, payload=payload)
    return payload
