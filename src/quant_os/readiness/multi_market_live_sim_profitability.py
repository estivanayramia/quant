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

REPORT_DIR = ROOT / "final"


def build_weather_live_sim_profitability(
    *, sequence60_payload: dict[str, Any] | None = None, output_root: str | Path = "."
) -> dict[str, Any]:
    sequence60_payload = sequence60_payload or load_json(
        "reports/live_market_sim_profitability/final/latest_live_market_sim_profitability.json",
        output_root=output_root,
    ) or {}
    status = sequence60_payload.get("status", "WEATHER_LIVE_SIM_PENDING_OUTCOMES")
    if status == "LIVE_MARKET_SIMULATED_PROFITABILITY_PROVEN":
        mapped = "WEATHER_LIVE_SIM_PROFITABILITY_PROVEN"
    elif "PENDING" in status:
        mapped = "WEATHER_LIVE_SIM_PENDING_OUTCOMES"
    elif "NEEDS_MORE" in status:
        mapped = "WEATHER_LIVE_SIM_NEEDS_MORE_OBSERVATIONS"
    else:
        mapped = "WEATHER_LIVE_SIM_NOT_PROVEN"
    return safe_report_payload(
        schema_version="weather_live_sim_profitability_continuation_v1",
        status=mapped,
        observation_count=int(sequence60_payload.get("observation_count") or 0),
        eligible_intent_count=int(sequence60_payload.get("eligible_intent_count") or 0),
        fake_fill_count=int(sequence60_payload.get("fake_fill_count") or 0),
        pending_outcome_count=int(sequence60_payload.get("pending_outcome_count") or 0),
        resolved_outcome_count=int(sequence60_payload.get("resolved_outcome_count") or 0),
        fake_gross_pnl=float(sequence60_payload.get("fake_gross_pnl") or 0.0),
        fake_net_pnl=0.0 if mapped == "WEATHER_LIVE_SIM_PENDING_OUTCOMES" else float(sequence60_payload.get("fake_net_pnl") or 0.0),
        baseline_pnl=float(sequence60_payload.get("baseline_pnl") or 0.0),
        placebo_pnl=float(sequence60_payload.get("placebo_pnl") or 0.0),
        reconciliation_status=sequence60_payload.get("reconciliation_status"),
        blockers=["WEATHER_OUTCOMES_PENDING"] if mapped == "WEATHER_LIVE_SIM_PENDING_OUTCOMES" else [],
        next_action="Recheck public weather outcomes later; continue other market families.",
    )


def build_prediction_market_structural_profitability(
    *,
    relations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    relations = relations or []
    blockers: list[str] = []
    if not relations:
        blockers.append("NO_MACHINE_VERIFIABLE_PUBLIC_RELATIONS")
    for relation in relations:
        if relation.get("relation_confidence") != "machine_verifiable":
            blockers.append("AMBIGUOUS_RELATION_MAPPING")
    status = "PM_STRUCTURAL_LIVE_SIM_BLOCKED" if blockers else "PM_STRUCTURAL_LIVE_SIM_NOT_PROVEN"
    return safe_report_payload(
        schema_version="pm_structural_live_sim_profitability_v1",
        status=status,
        allowed_statuses=[
            "PM_STRUCTURAL_LIVE_SIM_PROFITABILITY_PROVEN",
            "PM_STRUCTURAL_LIVE_SIM_PENDING_OUTCOMES",
            "PM_STRUCTURAL_LIVE_SIM_NOT_PROVEN",
            "PM_STRUCTURAL_LIVE_SIM_BLOCKED",
        ],
        relations=relations,
        fake_net_pnl=0.0,
        baseline_pnl=0.0,
        placebo_pnl=0.0,
        blockers=list(dict.fromkeys(blockers)),
        next_action="Continue only when public, machine-verifiable relations and outcome path exist.",
    )


def evaluate_etf_equity_source_policy(source_policy: dict[str, Any] | None = None) -> dict[str, Any]:
    source_policy = source_policy or {}
    approved = source_policy.get("policy") == "approved_public_read_only"
    status = "ETF_LIVE_SIM_NOT_PROVEN" if approved else "ETF_LIVE_SIM_NEEDS_APPROVED_SOURCE"
    blockers = [] if approved else ["APPROVED_PUBLIC_SOURCE_POLICY_REQUIRED"]
    return safe_report_payload(
        schema_version="etf_equity_live_sim_profitability_v1",
        status=status,
        allowed_statuses=[
            "ETF_LIVE_SIM_PROFITABILITY_PROVEN",
            "ETF_LIVE_SIM_NEEDS_APPROVED_SOURCE",
            "ETF_LIVE_SIM_NOT_PROVEN",
            "ETF_LIVE_SIM_BLOCKED",
        ],
        source_policy=source_policy,
        fake_net_pnl=0.0,
        baseline_pnl=0.0,
        placebo_pnl=0.0,
        blockers=blockers,
        next_action="Provide approved no-auth public ETF/equity data source policy before using this lane.",
    )


def build_multi_market_live_sim_profitability(
    *,
    output_root: str | Path = ".",
    crypto: dict[str, Any] | None = None,
    weather: dict[str, Any] | None = None,
    prediction_market_structural: dict[str, Any] | None = None,
    etf_equity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    crypto = crypto or load_json(
        "reports/multi_market_live_sim/crypto_spot/latest_crypto_profitability.json",
        output_root=output_root,
    ) or {}
    weather = weather or build_weather_live_sim_profitability(output_root=output_root)
    prediction_market_structural = prediction_market_structural or build_prediction_market_structural_profitability()
    etf_equity = etf_equity or evaluate_etf_equity_source_policy()
    families = {
        "crypto_spot": crypto,
        "weather_prediction_markets": weather,
        "prediction_market_structural": prediction_market_structural,
        "etf_equity": etf_equity,
    }
    proven = [
        name
        for name, payload in families.items()
        if payload.get("status")
        in {
            "CRYPTO_LIVE_SIM_PROFITABILITY_PROVEN",
            "WEATHER_LIVE_SIM_PROFITABILITY_PROVEN",
            "PM_STRUCTURAL_LIVE_SIM_PROFITABILITY_PROVEN",
            "ETF_LIVE_SIM_PROFITABILITY_PROVEN",
        }
        and float(payload.get("fake_net_pnl") or 0.0) > 0
        and bool(payload.get("baseline_beaten", True))
        and bool(payload.get("placebo_beaten", True))
    ]
    if proven:
        status = "MULTI_MARKET_LIVE_SIM_PROFITABILITY_PROVEN"
    elif any("PENDING" in str(payload.get("status")) for payload in families.values()):
        status = "MULTI_MARKET_LIVE_SIM_PENDING_OUTCOMES"
    elif any("NEEDS_MORE" in str(payload.get("status")) for payload in families.values()):
        status = "MULTI_MARKET_LIVE_SIM_NEEDS_MORE_OBSERVATIONS"
    else:
        status = "MULTI_MARKET_LIVE_SIM_CHECKPOINTED_NOT_COMPLETE"
    payload = safe_report_payload(
        schema_version="multi_market_live_sim_profitability_v1",
        status=status,
        allowed_statuses=[
            "MULTI_MARKET_LIVE_SIM_PROFITABILITY_PROVEN",
            "MULTI_MARKET_LIVE_SIM_PENDING_OUTCOMES",
            "MULTI_MARKET_LIVE_SIM_NEEDS_MORE_OBSERVATIONS",
            "MULTI_MARKET_LIVE_SIM_NOT_PROVEN",
            "MULTI_MARKET_LIVE_SIM_CHECKPOINTED_NOT_COMPLETE",
            "HUMAN_DATA_OR_CREDENTIAL_BOUNDARY_REACHED",
        ],
        proven_market_families=proven,
        fake_pnl_by_family={name: float(item.get("fake_net_pnl") or 0.0) for name, item in families.items()},
        baseline_pnl_by_family={name: float(item.get("baseline_pnl") or 0.0) for name, item in families.items()},
        placebo_pnl_by_family={name: float(item.get("placebo_pnl") or 0.0) for name, item in families.items()},
        reconciliation_status_by_family={
            name: item.get("reconciliation_status") or item.get("status") for name, item in families.items()
        },
        market_families={name: family_from_payload(name, item) for name, item in families.items()},
        blockers=[],
        next_action="Stop: fake-money profitability proven under guardrails."
        if proven
        else "Run scheduler/resume loop for more public observations or outcome marks.",
        exact_resume_command=".\\make.cmd multi-market-live-sim-smoke",
    )
    return payload


def write_multi_market_live_sim_profitability_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_multi_market_live_sim_profitability(output_root=output_root)
    family_reports = {
        "weather_prediction_markets": (
            ROOT / "weather",
            "latest_weather_profitability.json",
            "latest_weather_profitability.md",
            "Weather Live Sim Profitability",
        ),
        "prediction_market_structural": (
            ROOT / "prediction_market_structural",
            "latest_pm_structural_profitability.json",
            "latest_pm_structural_profitability.md",
            "Prediction-Market Structural Live Sim Profitability",
        ),
        "etf_equity": (
            ROOT / "etf_equity",
            "latest_etf_profitability.json",
            "latest_etf_profitability.md",
            "ETF/Equity Paper-Only Live Sim Profitability",
        ),
    }
    for family, (report_dir, json_name, md_name, title) in family_reports.items():
        write_json_markdown_report(
            payload["market_families"][family],
            output_root=output_root,
            report_dir=report_dir,
            json_name=json_name,
            md_name=md_name,
            title=title,
            summary="Family-level public-data fake-money live simulation checkpoint.",
        )
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_multi_market_live_sim_profitability.json",
        md_name="latest_multi_market_live_sim_profitability.md",
        title="Multi-Market Live Simulated Profitability",
        summary="Aggregate fake-money live simulated profitability gate across safe public-data market families.",
    )
    state = load_multi_market_state(output_root=output_root)
    write_multi_market_state(
        output_root=output_root,
        status=payload["status"],
        market_families=payload["market_families"] or state.get("market_families"),
    )
    return payload
