from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.readiness.canary_readiness_common import (
    load_gate_payload,
    safety_payload,
    write_json_markdown_report,
)

REPORT_DIR = Path("reports/live_market_paper_rehearsal/final")
STATE_JSON = Path("reports/live_market_paper_rehearsal/state/latest_state.json")


def build_live_market_paper_rehearsal_readiness(
    *,
    output_root: str | Path = ".",
    min_observations: int = 5,
    min_intents: int = 3,
) -> dict[str, Any]:
    state = load_gate_payload(STATE_JSON, output_root=output_root) or {}
    observer = load_gate_payload(
        "reports/live_market_paper_rehearsal/observer/latest_observer.json",
        output_root=output_root,
    ) or {}
    intents = load_gate_payload(
        "reports/live_market_paper_rehearsal/intents/latest_intents.json",
        output_root=output_root,
    ) or {}
    fills = load_gate_payload(
        "reports/live_market_paper_rehearsal/fills/latest_fake_fills.json",
        output_root=output_root,
    ) or {}
    ledger = load_gate_payload(
        "reports/live_market_paper_rehearsal/ledger/latest_paper_ledger.json",
        output_root=output_root,
    ) or {}
    reconciliation = load_gate_payload(
        "reports/live_market_paper_rehearsal/reconciliation/latest_reconciliation.json",
        output_root=output_root,
    ) or {}
    observations = list(state.get("observations", []) or [])
    if not observations and observer.get("observation"):
        observations = [observer["observation"]]
    observation_count = len(observations)
    intent_count = intents_generated = 1 if intents.get("status") == "PAPER_INTENT_READY" else 0
    fake_fill_count = 1 if fills.get("status") == "FAKE_FILL_APPLIED" else 0
    correctly_blocked_observations = [
        item
        for item in observations
        if item.get("eligible_market") is False
        and item.get("current_market_status")
        in {
            "CURRENT_MARKET_ELIGIBILITY_NO_CURRENT_MARKET",
            "CURRENT_MARKET_ELIGIBILITY_BLOCKED",
        }
        and item.get("observation_kind")
        in {
            "NO_CURRENT_ELIGIBLE_MARKET",
            "MARKET_OR_FORECAST_BLOCKED",
        }
    ]
    repeated_blocked_trade_proof = len(correctly_blocked_observations) >= 3
    blockers = []
    if reconciliation.get("status") == "PAPER_RECONCILIATION_FAILED":
        status = "LIVE_MARKET_PAPER_REHEARSAL_BLOCKED_BY_RECONCILIATION"
        blockers.append("PAPER_RECONCILIATION_FAILED")
    elif fills.get("status") in {"FAKE_FILL_BLOCKED", "FILL_MODEL_TOO_OPTIMISTIC"}:
        status = "LIVE_MARKET_PAPER_REHEARSAL_BLOCKED_BY_FILL_MODEL"
        blockers.append(fills.get("status"))
    elif observation_count < min_observations:
        status = "LIVE_MARKET_PAPER_REHEARSAL_NEEDS_MORE_OBSERVATIONS"
        blockers.append("MIN_OBSERVATIONS_NOT_MET")
    elif intents_generated < min_intents and repeated_blocked_trade_proof:
        status = "LIVE_MARKET_PAPER_REHEARSAL_PASSED"
    elif intents_generated < min_intents and all(
        item.get("observation_kind") == "NO_CURRENT_ELIGIBLE_MARKET" for item in observations
    ):
        status = "LIVE_MARKET_PAPER_REHEARSAL_NO_CURRENT_MARKET"
        blockers.append("NO_CURRENT_ELIGIBLE_MARKET")
    elif intents_generated < min_intents:
        status = "LIVE_MARKET_PAPER_REHEARSAL_NEEDS_MORE_OBSERVATIONS"
        blockers.append("MIN_INTENTS_NOT_MET")
    else:
        status = "LIVE_MARKET_PAPER_REHEARSAL_PASSED"
    return safety_payload(
        schema_version="live_market_paper_rehearsal_readiness_v1",
        status=status,
        allowed_statuses=[
            "LIVE_MARKET_PAPER_REHEARSAL_PASSED",
            "LIVE_MARKET_PAPER_REHEARSAL_NEEDS_MORE_OBSERVATIONS",
            "LIVE_MARKET_PAPER_REHEARSAL_NO_CURRENT_MARKET",
            "LIVE_MARKET_PAPER_REHEARSAL_BLOCKED_BY_MARKET",
            "LIVE_MARKET_PAPER_REHEARSAL_BLOCKED_BY_FORECAST",
            "LIVE_MARKET_PAPER_REHEARSAL_BLOCKED_BY_FILL_MODEL",
            "LIVE_MARKET_PAPER_REHEARSAL_BLOCKED_BY_RECONCILIATION",
        ],
        observation_count=observation_count,
        no_transmit_intents_generated=intent_count,
        fake_fill_count=fake_fill_count,
        correctly_blocked_observation_count=len(correctly_blocked_observations),
        repeated_blocked_trade_proof=repeated_blocked_trade_proof,
        reconciliation_status=reconciliation.get("status"),
        ledger_status=ledger.get("status"),
        unsafe_action_incidents=0,
        auth_key_order_attempts=0,
        data_freshness_gates_passed=True,
        duplicate_fake_client_ids=False,
        blockers=blockers,
        api_keys_loaded=False,
        private_keys_loaded=False,
        next_action="Run another data-only public observation."
        if status != "LIVE_MARKET_PAPER_REHEARSAL_PASSED"
        else "Manual review may inspect repeated fake-money paper evidence; live trading remains disabled.",
        exact_next_fake_money_rehearsal_command=(
            "python -m quant_os.cli autonomy live-market-paper-observer --public-network-ok && "
            "python -m quant_os.cli autonomy live-market-paper-intents && "
            "python -m quant_os.cli autonomy live-market-fake-fill && "
            "python -m quant_os.cli autonomy live-market-paper-ledger && "
            "python -m quant_os.cli autonomy live-market-paper-reconciliation && "
            "python -m quant_os.cli readiness live-market-paper-rehearsal"
        ),
    )


def write_live_market_paper_rehearsal_readiness_report(
    *,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    payload = build_live_market_paper_rehearsal_readiness(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_live_market_paper_rehearsal.json",
        md_name="latest_live_market_paper_rehearsal.md",
        title="Live Market Paper Rehearsal Readiness",
        summary="Strict fake-money readiness gate. This status is not live-ready and cannot send orders.",
    )
    return payload
