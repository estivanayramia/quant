from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.research.strategy_factory.campaign_common import (
    load_report,
    safe_payload,
    write_json_md,
)


def build_thousand_strategy_public_forward_evidence(
    *,
    candidate: dict[str, Any] | None = None,
    live_sim_summary: dict[str, Any] | None = None,
    reconciliation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    candidate = candidate or {}
    live_sim_summary = live_sim_summary or {}
    reconciliation = reconciliation or {}
    candidate_id = str(candidate.get("id") or "")
    selected_strategy_id = str(live_sim_summary.get("selected_strategy_id") or "")
    data_sources = [str(source) for source in live_sim_summary.get("data_sources", [])]
    observation_count = int(live_sim_summary.get("observation_count") or 0)
    eligible_intent_count = int(live_sim_summary.get("eligible_intent_count") or 0)
    completed_mark_count = int(live_sim_summary.get("completed_mark_count") or 0)
    fake_net_pnl = float(live_sim_summary.get("fake_net_pnl") or 0.0)
    blockers: list[str] = []

    if not candidate_id:
        blockers.append("NO_SELECTED_CANDIDATE")
    if selected_strategy_id != candidate_id:
        blockers.append("SELECTED_STRATEGY_ID_MISMATCH")
    if live_sim_summary.get("status") != "VARIANT_LIVE_SIM_SUMMARY_READY":
        blockers.append("PUBLIC_FORWARD_LIVE_SIM_NOT_READY")
    if not data_sources:
        blockers.append("PUBLIC_FORWARD_DATA_SOURCE_MISSING")
    if any("fixture" in source.lower() for source in data_sources):
        blockers.append("FIXTURE_DATA_NOT_PUBLIC_FORWARD_EVIDENCE")
    if live_sim_summary.get("evidence_source") != "public_forward_live_sim":
        blockers.append("PUBLIC_FORWARD_EVIDENCE_SOURCE_MISSING")
    if live_sim_summary.get("public_forward_evidence_proven") is not True:
        blockers.append("PUBLIC_FORWARD_EVIDENCE_NOT_PROVEN")
    if observation_count < 1000:
        blockers.append("PUBLIC_FORWARD_OBSERVATION_COUNT_TOO_LOW")
    if eligible_intent_count < 300:
        blockers.append("PUBLIC_FORWARD_INTENT_COUNT_TOO_LOW")
    if completed_mark_count < 150:
        blockers.append("PUBLIC_FORWARD_COMPLETED_MARK_COUNT_TOO_LOW")
    if fake_net_pnl <= 0:
        blockers.append("PUBLIC_FORWARD_FAKE_NET_PNL_NOT_POSITIVE")
    if reconciliation.get("status") != "VARIANT_LIVE_SIM_RECONCILIATION_PASSED":
        blockers.append("PUBLIC_FORWARD_RECONCILIATION_NOT_PASSED")

    passed = not blockers
    return safe_payload(
        status="PUBLIC_FORWARD_EVIDENCE_PASSED" if passed else "PUBLIC_FORWARD_EVIDENCE_BLOCKED",
        blockers=blockers,
        selected_strategy_id=selected_strategy_id,
        candidate_id=candidate_id,
        data_sources=data_sources,
        observation_count=observation_count,
        eligible_intent_count=eligible_intent_count,
        completed_mark_count=completed_mark_count,
        fake_net_pnl=round(fake_net_pnl, 8),
        candidate_evidence=(
            {
                "public_forward_evidence_proven": True,
                "evidence_source": "public_forward_live_sim",
            }
            if passed
            else {
                "public_forward_evidence_proven": False,
                "evidence_source": str(live_sim_summary.get("evidence_source") or "unproven"),
            }
        ),
    )


def write_thousand_strategy_public_forward_evidence_report(
    *,
    output_root: str | Path = ".",
    candidate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    tournament = load_report(
        output_root=output_root,
        report_dir="tournament",
        json_name="latest_tournament.json",
    )
    live_sim_summary = load_report(
        output_root=output_root,
        report_dir="live_sim",
        json_name="latest_live_sim_summary.json",
    )
    reconciliation = load_report(
        output_root=output_root,
        report_dir="live_sim",
        json_name="latest_reconciliation.json",
    )
    payload = build_thousand_strategy_public_forward_evidence(
        candidate=candidate or tournament.get("current_best_candidate"),
        live_sim_summary=live_sim_summary,
        reconciliation=reconciliation,
    )
    return write_json_md(
        payload,
        output_root=output_root,
        report_dir="public_forward_evidence",
        json_name="latest_public_forward_evidence.json",
        md_name="latest_public_forward_evidence.md",
        title="Thousand Strategy Public Forward Evidence",
        lines=[
            f"Status: {payload['status']}",
            f"Blockers: {', '.join(payload['blockers']) if payload['blockers'] else 'None'}",
            f"Selected strategy: {payload['selected_strategy_id']}",
            f"Fake net PnL: {payload['fake_net_pnl']}",
        ],
    )
