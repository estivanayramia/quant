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
        intents.append(
            {
                "fake_client_order_id": f"cgint_{cg_hash(observation)}",
                "observation_id": observation["observation_id"],
                "symbol": observation["symbol"],
                "strategy": observation["strategy"],
                "venue": observation["venue"],
                "side": "buy",
                "quantity": 1.0,
                "limit_price": round(float(observation["entry_price"]) + float(observation["spread"]) / 2, 8),
                "entry_timestamp": observation["entry_timestamp"],
                "mark_timestamp": observation["mark_timestamp"],
                "mark_price": observation["mark_price"],
                "regime": observation["regime"],
                "walk_forward_window": observation["walk_forward_window"],
                "session_bucket": observation["session_bucket"],
                "fake_money": True,
                "no_transmit": True,
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
