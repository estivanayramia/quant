from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.autonomy.live_market_sim_common import load_json
from quant_os.autonomy.multi_market_live_sim_common import ROOT, mm_hash, safe_report_payload
from quant_os.readiness.canary_readiness_common import write_json_markdown_report

REPORT_DIR = ROOT / "crypto_spot"


def build_crypto_spot_live_sim_intents(
    *,
    observer: dict[str, Any] | None = None,
    output_root: str | Path = ".",
    max_intents: int = 10,
) -> dict[str, Any]:
    observer = observer or load_json(
        "reports/multi_market_live_sim/crypto_spot/latest_crypto_observer.json",
        output_root=output_root,
    ) or {}
    blockers: list[str] = []
    intents: list[dict[str, Any]] = []
    for observation in list(observer.get("observations", []) or []):
        if not observation.get("eligible"):
            continue
        intent = {
            "fake_client_order_id": f"csli_{mm_hash(observation)}",
            "observation_id": observation["observation_id"],
            "strategy": observation["strategy"],
            "symbol": observation["symbol"],
            "side": "buy",
            "quantity": 1.0,
            "limit_price": round(float(observation["entry_price"]) + float(observation["spread"]) / 2, 8),
            "entry_timestamp": observation["entry_timestamp"],
            "mark_timestamp": observation["mark_timestamp"],
            "mark_price": observation["mark_price"],
            "fake_money": True,
            "no_transmit": True,
            "dry_run_only": True,
            "order_transmission_enabled": False,
            "authenticated_requests_enabled": False,
            "request_signing_enabled": False,
            "contains_signed_headers": False,
            "contains_private_key_path": False,
            "contains_executable_submission_code": False,
            "blocked_endpoints": ["disabled_private_add_order", "disabled_portfolio_order_submission"],
            "evidence_hash": mm_hash({"intent_observation": observation}),
        }
        intents.append(intent)
        if len(intents) >= max_intents:
            break
    if observer.get("status") != "CRYPTO_OBSERVER_READY":
        blockers.append("OBSERVER_NOT_READY")
    status = "CRYPTO_LIVE_SIM_INTENTS_READY" if intents else "CRYPTO_LIVE_SIM_NO_ELIGIBLE_INTENTS"
    return safe_report_payload(
        schema_version="crypto_spot_live_sim_intents_v1",
        status=status,
        allowed_statuses=["CRYPTO_LIVE_SIM_INTENTS_READY", "CRYPTO_LIVE_SIM_NO_ELIGIBLE_INTENTS"],
        intents=intents,
        eligible_intent_count=len(intents),
        fake_money=True,
        no_transmit=True,
        blockers=blockers,
        next_action="Apply conservative fake crypto spot fill model."
        if intents
        else "Collect more public crypto observations.",
    )


def write_crypto_spot_live_sim_intents_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_crypto_spot_live_sim_intents(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_crypto_intents.json",
        md_name="latest_crypto_intents.md",
        title="Crypto Spot Live Sim Intents",
        summary="Fake-money no-transmit crypto spot intents. No orders can be routed.",
    )
    return payload
