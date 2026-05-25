from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from quant_os.readiness.canary_readiness_common import (
    load_gate_payload,
    safety_payload,
    write_json_markdown_report,
)

REPORT_DIR = Path("reports/live_market_paper_rehearsal/fills")
STATE_JSON = Path("reports/live_market_paper_rehearsal/state/latest_state.json")


def apply_fake_fill_model(
    *,
    intent: dict[str, Any] | None,
    observation: dict[str, Any] | None,
    max_spread: float = 0.05,
) -> dict[str, Any]:
    blockers: list[str] = []
    market = (observation or {}).get("market") or {}
    if not intent:
        status = "FAKE_NO_FILL"
        fake_fill = None
        confidence = 0.0
    elif float(market.get("spread") or 0.0) > max_spread:
        status = "FAKE_FILL_BLOCKED"
        blockers.append("SPREAD_TOO_WIDE_FOR_FAKE_FILL")
        fake_fill = None
        confidence = 0.0
    elif float(intent.get("limit_price") or 0.0) < float(market.get("yes_ask") or 1.0):
        status = "FAKE_NO_FILL"
        fake_fill = None
        confidence = 0.15
    else:
        filled_contracts = min(int(intent.get("fake_contracts") or 1), 1)
        status = "FAKE_FILL_APPLIED"
        confidence = 0.55 if float(market.get("liquidity") or 0.0) >= 5.0 else 0.35
        fake_fill = {
            "fake_fill_id": _fake_fill_id(intent, observation),
            "fake_client_order_id": intent.get("fake_client_order_id"),
            "market_ticker": intent.get("market_ticker"),
            "filled_contracts": filled_contracts,
            "fill_price": float(market.get("yes_ask") or intent.get("limit_price") or 0.0),
            "latency_penalty": 0.01,
            "adverse_selection_stress": 0.02,
            "conservative_partial_fill": filled_contracts < int(intent.get("fake_contracts") or 1),
        }
    return safety_payload(
        schema_version="live_market_fake_fill_v1",
        status=status,
        allowed_statuses=[
            "FAKE_FILL_APPLIED",
            "FAKE_NO_FILL",
            "FAKE_FILL_BLOCKED",
            "FILL_MODEL_TOO_OPTIMISTIC",
        ],
        observation_id=(observation or {}).get("observation_id"),
        fake_fill=fake_fill,
        guaranteed_fill=False,
        fake_fill_confidence=confidence,
        fill_model="conservative_public_book_cross_with_latency_penalty",
        blockers=blockers,
        api_keys_loaded=False,
        private_keys_loaded=False,
        next_action="Update fake paper ledger.",
    )


def build_live_market_fake_fill(*, output_root: str | Path = ".") -> dict[str, Any]:
    intents_payload = load_gate_payload(
        "reports/live_market_paper_rehearsal/intents/latest_intents.json",
        output_root=output_root,
    ) or {}
    observer = load_gate_payload(
        "reports/live_market_paper_rehearsal/observer/latest_observer.json",
        output_root=output_root,
    ) or {}
    return apply_fake_fill_model(
        intent=intents_payload.get("intent"),
        observation=observer.get("observation"),
    )


def write_live_market_fake_fill_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_live_market_fake_fill(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_fake_fills.json",
        md_name="latest_fake_fills.md",
        title="Live Market Fake Fill",
        summary="Conservative fake fill/no-fill model using public book evidence only.",
    )
    _merge_state(output_root=output_root, fake_fills=1 if payload["status"] == "FAKE_FILL_APPLIED" else 0)
    return payload


def _fake_fill_id(intent: dict[str, Any], observation: dict[str, Any] | None) -> str:
    raw = json.dumps({"intent": intent, "observation": observation}, sort_keys=True, default=str)
    return f"fakefill_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _merge_state(*, output_root: str | Path, **updates: Any) -> None:
    path = Path(output_root) / STATE_JSON
    if not path.exists():
        return
    state = json.loads(path.read_text(encoding="utf-8"))
    state.update(updates)
    path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
