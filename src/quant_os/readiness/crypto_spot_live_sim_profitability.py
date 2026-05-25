from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.autonomy.live_market_sim_common import load_json
from quant_os.autonomy.multi_market_live_sim_common import (
    ROOT,
    family_from_payload,
    load_multi_market_state,
    safe_report_payload,
    write_multi_market_state,
)
from quant_os.readiness.canary_readiness_common import write_json_markdown_report

REPORT_DIR = ROOT / "crypto_spot"


def build_crypto_spot_live_sim_profitability(
    *,
    output_root: str | Path = ".",
    observer: dict[str, Any] | None = None,
    intents: dict[str, Any] | None = None,
    fills: dict[str, Any] | None = None,
    pnl: dict[str, Any] | None = None,
    comparison: dict[str, Any] | None = None,
    reconciliation: dict[str, Any] | None = None,
    min_observations: int = 20,
    min_intents: int = 5,
    min_fills: int = 3,
    min_completed_marks: int = 5,
) -> dict[str, Any]:
    observer = observer or load_json("reports/multi_market_live_sim/crypto_spot/latest_crypto_observer.json", output_root=output_root) or {}
    intents = intents or load_json("reports/multi_market_live_sim/crypto_spot/latest_crypto_intents.json", output_root=output_root) or {}
    fills = fills or load_json("reports/multi_market_live_sim/crypto_spot/latest_crypto_fills.json", output_root=output_root) or {}
    pnl = pnl or load_json("reports/multi_market_live_sim/crypto_spot/latest_crypto_pnl.json", output_root=output_root) or {}
    comparison = comparison or load_json("reports/multi_market_live_sim/crypto_spot/latest_crypto_comparison.json", output_root=output_root) or {}
    reconciliation = reconciliation or load_json(
        "reports/multi_market_live_sim/crypto_spot/latest_crypto_reconciliation.json",
        output_root=output_root,
    ) or {}
    observation_count = int(observer.get("observation_count") or 0)
    intent_count = int(intents.get("eligible_intent_count") or 0)
    fill_count = int(fills.get("fake_fill_count") or 0)
    completed_marks = int(pnl.get("completed_mark_count") or 0)
    net = float(pnl.get("fake_net_pnl") or 0.0)
    blockers: list[str] = []
    if observation_count < min_observations:
        blockers.append("MIN_CRYPTO_OBSERVATIONS_NOT_MET")
    if intent_count < min_intents:
        blockers.append("MIN_CRYPTO_ELIGIBLE_INTENTS_NOT_MET")
    if fill_count < min_fills:
        blockers.append("MIN_CRYPTO_FAKE_FILLS_NOT_MET")
    if completed_marks < min_completed_marks:
        blockers.append("MIN_CRYPTO_COMPLETED_MARKS_NOT_MET")
    if blockers:
        status = "CRYPTO_LIVE_SIM_NEEDS_MORE_OBSERVATIONS"
    else:
        if net <= 0:
            blockers.append("FAKE_NET_PNL_NOT_POSITIVE")
        if not comparison.get("baseline_beaten"):
            blockers.append("BASELINE_NOT_BEATEN")
        if not comparison.get("placebo_beaten"):
            blockers.append("PLACEBO_NOT_BEATEN")
        if reconciliation.get("status") != "CRYPTO_LIVE_SIM_RECONCILIATION_PASSED":
            blockers.append("RECONCILIATION_NOT_PASSED")
        status = "CRYPTO_LIVE_SIM_PROFITABILITY_PROVEN" if not blockers else "CRYPTO_LIVE_SIM_NOT_PROVEN"
    payload = safe_report_payload(
        schema_version="crypto_spot_live_sim_profitability_v1",
        status=status,
        allowed_statuses=[
            "CRYPTO_LIVE_SIM_PROFITABILITY_PROVEN",
            "CRYPTO_LIVE_SIM_PENDING_MARKS",
            "CRYPTO_LIVE_SIM_NEEDS_MORE_OBSERVATIONS",
            "CRYPTO_LIVE_SIM_NOT_PROVEN",
            "CRYPTO_LIVE_SIM_BLOCKED",
        ],
        active_instruments=observer.get("active_instruments", []),
        observation_count=observation_count,
        eligible_intent_count=intent_count,
        fake_fill_count=fill_count,
        fake_no_fill_count=int(fills.get("fake_no_fill_count") or 0),
        completed_mark_count=completed_marks,
        pending_mark_count=int(pnl.get("pending_mark_count") or 0),
        fake_gross_pnl=float(pnl.get("fake_gross_pnl") or 0.0),
        fake_net_pnl=net,
        baseline_pnl=float(comparison.get("baseline_pnl") or 0.0),
        placebo_pnl=float(comparison.get("placebo_pnl") or 0.0),
        baseline_beaten=bool(comparison.get("baseline_beaten")),
        placebo_beaten=bool(comparison.get("placebo_beaten")),
        reconciliation_status=reconciliation.get("status"),
        blockers=blockers,
        next_action="Aggregate multi-market profitability."
        if status == "CRYPTO_LIVE_SIM_PROFITABILITY_PROVEN"
        else "Continue bounded crypto spot observation/mark loop.",
    )
    return payload


def write_crypto_spot_live_sim_profitability_report(
    *,
    output_root: str | Path = ".",
    min_observations: int = 20,
    min_intents: int = 5,
    min_fills: int = 3,
    min_completed_marks: int = 5,
) -> dict[str, Any]:
    payload = build_crypto_spot_live_sim_profitability(
        output_root=output_root,
        min_observations=min_observations,
        min_intents=min_intents,
        min_fills=min_fills,
        min_completed_marks=min_completed_marks,
    )
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_crypto_profitability.json",
        md_name="latest_crypto_profitability.md",
        title="Crypto Spot Live Sim Profitability",
        summary="Crypto spot fake-money live simulated profitability gate.",
    )
    state = load_multi_market_state(output_root=output_root)
    families = dict(state.get("market_families") or {})
    families["crypto_spot"] = family_from_payload("crypto_spot", payload)
    write_multi_market_state(output_root=output_root, market_families=families)
    return payload
