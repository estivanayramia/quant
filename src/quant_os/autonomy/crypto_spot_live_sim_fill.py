from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.autonomy.live_market_sim_common import load_json
from quant_os.autonomy.multi_market_live_sim_common import ROOT, mm_hash, safe_report_payload
from quant_os.readiness.canary_readiness_common import write_json_markdown_report

REPORT_DIR = ROOT / "crypto_spot"


def apply_crypto_spot_live_sim_fill_model(
    *,
    intents: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    max_spread: float = 0.10,
) -> dict[str, Any]:
    by_id = {item.get("observation_id"): item for item in observations}
    fills: list[dict[str, Any]] = []
    no_fills: list[dict[str, Any]] = []
    blockers: list[str] = []
    for intent in intents:
        observation = by_id.get(intent.get("observation_id"), {})
        spread = float(observation.get("spread") or 0.0)
        ask_size = float(observation.get("ask_size") or 0.0)
        entry = float(observation.get("entry_price") or intent.get("limit_price") or 0.0)
        if spread > max_spread + 0.0000001:
            no_fills.append({"fake_client_order_id": intent["fake_client_order_id"], "status": "SPREAD_TOO_WIDE"})
            blockers.append("SPREAD_TOO_WIDE")
            continue
        if ask_size <= 0 or float(intent.get("limit_price") or 0.0) < entry:
            no_fills.append({"fake_client_order_id": intent["fake_client_order_id"], "status": "NO_PUBLIC_LIQUIDITY"})
            continue
        quantity = min(float(intent.get("quantity") or 1.0), max(ask_size / 4.0, 0.0), 1.0)
        if quantity <= 0:
            no_fills.append({"fake_client_order_id": intent["fake_client_order_id"], "status": "ZERO_CONSERVATIVE_SIZE"})
            continue
        fill = {
            "fake_fill_id": f"cslf_{mm_hash({'intent': intent, 'observation': observation})}",
            "fake_client_order_id": intent["fake_client_order_id"],
            "observation_id": intent["observation_id"],
            "symbol": intent["symbol"],
            "side": intent["side"],
            "quantity": round(quantity, 8),
            "entry_timestamp": intent["entry_timestamp"],
            "entry_price": entry,
            "mark_timestamp": intent["mark_timestamp"],
            "mark_price": float(intent["mark_price"]),
            "spread_cost": round(spread * quantity, 8),
            "slippage_cost": round(max(entry * 0.0001, 0.01) * quantity, 8),
            "fee_cost": 0.0,
            "fee_assumption": "fee_disabled_for_public_data_sim_spread_and_slippage_charged",
            "conservative_partial_fill": quantity < float(intent.get("quantity") or 1.0),
            "guaranteed_fill": False,
            "evidence_hash": mm_hash({"fill": intent, "spread": spread, "ask_size": ask_size}),
        }
        fills.append(fill)
    return safe_report_payload(
        schema_version="crypto_spot_live_sim_fill_v1",
        status="CRYPTO_LIVE_SIM_FILLS_APPLIED" if fills else "CRYPTO_LIVE_SIM_NO_FILLS",
        allowed_statuses=["CRYPTO_LIVE_SIM_FILLS_APPLIED", "CRYPTO_LIVE_SIM_NO_FILLS"],
        fake_fills=fills,
        fake_no_fills=no_fills,
        fake_fill_count=len(fills),
        fake_no_fill_count=len(no_fills),
        guaranteed_fill=False,
        fill_model="conservative_public_spot_no_better_than_entry_with_spread_slippage_fee",
        blockers=list(dict.fromkeys(blockers)),
        next_action="Update fake crypto spot ledger." if fills else "Collect more crypto observations.",
    )


def build_crypto_spot_live_sim_fill(*, output_root: str | Path = ".") -> dict[str, Any]:
    intents_payload = load_json(
        "reports/multi_market_live_sim/crypto_spot/latest_crypto_intents.json",
        output_root=output_root,
    ) or {}
    observer = load_json(
        "reports/multi_market_live_sim/crypto_spot/latest_crypto_observer.json",
        output_root=output_root,
    ) or {}
    return apply_crypto_spot_live_sim_fill_model(
        intents=list(intents_payload.get("intents", []) or []),
        observations=list(observer.get("observations", []) or []),
    )


def write_crypto_spot_live_sim_fill_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_crypto_spot_live_sim_fill(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_crypto_fills.json",
        md_name="latest_crypto_fills.md",
        title="Crypto Spot Live Sim Fill",
        summary="Conservative fake fill/no-fill model from public spot observations.",
    )
    return payload
