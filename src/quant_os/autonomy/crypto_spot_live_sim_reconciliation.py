from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.autonomy.live_market_sim_common import load_json
from quant_os.autonomy.multi_market_live_sim_common import ROOT, safe_report_payload
from quant_os.readiness.canary_readiness_common import write_json_markdown_report

REPORT_DIR = ROOT / "crypto_spot"


def build_crypto_spot_live_sim_reconciliation(*, output_root: str | Path = ".") -> dict[str, Any]:
    observer = load_json(
        "reports/multi_market_live_sim/crypto_spot/latest_crypto_observer.json",
        output_root=output_root,
    ) or {}
    intents = load_json(
        "reports/multi_market_live_sim/crypto_spot/latest_crypto_intents.json",
        output_root=output_root,
    ) or {}
    fills = load_json(
        "reports/multi_market_live_sim/crypto_spot/latest_crypto_fills.json",
        output_root=output_root,
    ) or {}
    ledger = load_json(
        "reports/multi_market_live_sim/crypto_spot/latest_crypto_ledger.json",
        output_root=output_root,
    ) or {}
    pnl = load_json(
        "reports/multi_market_live_sim/crypto_spot/latest_crypto_pnl.json",
        output_root=output_root,
    ) or {}
    comparison = load_json(
        "reports/multi_market_live_sim/crypto_spot/latest_crypto_comparison.json",
        output_root=output_root,
    ) or {}
    blockers: list[str] = []
    if observer.get("status") != "CRYPTO_OBSERVER_READY":
        blockers.append("OBSERVER_NOT_READY")
    if len(intents.get("intents", []) or []) < len(fills.get("fake_fills", []) or []):
        blockers.append("FILL_WITHOUT_INTENT")
    if len(fills.get("fake_fills", []) or []) != len(ledger.get("ledger_entries", []) or []):
        blockers.append("LEDGER_FILL_MISMATCH")
    if len(ledger.get("ledger_entries", []) or []) != len(pnl.get("pnl_rows", []) or []):
        blockers.append("PNL_LEDGER_MISMATCH")
    if comparison.get("status") != "CRYPTO_LIVE_SIM_BASELINES_BEATEN":
        blockers.append("COMPARISON_NOT_PASSED")
    status = "CRYPTO_LIVE_SIM_RECONCILIATION_PASSED" if not blockers else "CRYPTO_LIVE_SIM_RECONCILIATION_BLOCKED"
    return safe_report_payload(
        schema_version="crypto_spot_live_sim_reconciliation_v1",
        status=status,
        allowed_statuses=[
            "CRYPTO_LIVE_SIM_RECONCILIATION_PASSED",
            "CRYPTO_LIVE_SIM_RECONCILIATION_BLOCKED",
        ],
        observation_count=int(observer.get("observation_count") or 0),
        eligible_intent_count=int(intents.get("eligible_intent_count") or 0),
        fake_fill_count=int(fills.get("fake_fill_count") or 0),
        completed_mark_count=int(pnl.get("completed_mark_count") or 0),
        fake_net_pnl=float(pnl.get("fake_net_pnl") or 0.0),
        baseline_beaten=bool(comparison.get("baseline_beaten")),
        placebo_beaten=bool(comparison.get("placebo_beaten")),
        blockers=blockers,
        next_action="Run crypto spot profitability readiness gate." if not blockers else "Repair blocked reconciliation evidence.",
    )


def write_crypto_spot_live_sim_reconciliation_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_crypto_spot_live_sim_reconciliation(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_crypto_reconciliation.json",
        md_name="latest_crypto_reconciliation.md",
        title="Crypto Spot Live Sim Reconciliation",
        summary="Fake-money reconciliation for crypto spot live simulation.",
    )
    return payload
