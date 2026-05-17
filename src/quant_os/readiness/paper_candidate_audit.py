from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.readiness.canary_readiness_common import (
    load_dataset_payload,
    load_paper_payload,
    load_profit_payload,
    safety_payload,
    update_canary_state,
    write_json_markdown_report,
)

REPORT_DIR = Path("reports/canary_readiness/paper_candidate_audit")
JSON_NAME = "latest_paper_candidate_audit.json"
MD_NAME = "latest_paper_candidate_audit.md"


def evaluate_paper_candidate_audit(
    *,
    output_root: str | Path = ".",
    profit_campaign_payload: dict[str, Any] | None = None,
    dataset_payload: dict[str, Any] | None = None,
    paper_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    blockers: list[str] = []
    if profit_campaign_payload is None:
        profit_campaign_payload = load_profit_payload(output_root=output_root)
        if profit_campaign_payload is None:
            blockers.append("MISSING_PROFIT_CAMPAIGN_REPORT")
            profit_campaign_payload = {}
    if dataset_payload is None:
        dataset_payload = load_dataset_payload(output_root=output_root) or {}
        if not dataset_payload:
            blockers.append("MISSING_WEATHER_DATASET_REPORT")
    if paper_payload is None:
        paper_payload = load_paper_payload(output_root=output_root) or {}
        if not paper_payload:
            blockers.append("MISSING_WEATHER_PAPER_PROVING_REPORT")

    found = (
        profit_campaign_payload.get("campaign_status") == "PAPER_PROFIT_CANDIDATE_FOUND"
        or profit_campaign_payload.get("paper_profit_status") == "PAPER_PROFIT_CANDIDATE_FOUND"
    )
    if not found:
        blockers.append("PAPER_PROFIT_CANDIDATE_FOUND_MISSING")
    if paper_payload.get("readiness_status") != "PAPER_PROFIT_CANDIDATE":
        blockers.append("PAPER_REPORT_NOT_CANDIDATE")
    if int(paper_payload.get("proof_row_count", 0) or 0) < 30:
        blockers.append("PAPER_CANDIDATE_TOO_THIN")
    if paper_payload.get("source_quality_tier") in {"UNKNOWN", "WEAK", "SYNTHETIC_ONLY", None}:
        blockers.append("PAPER_CANDIDATE_SOURCE_WEAK")
    if paper_payload.get("execution_authority") != "NONE":
        blockers.append("EXECUTION_AUTHORITY_PRESENT")
    if paper_payload.get("live_trading_enabled") is True:
        blockers.append("LIVE_TRADING_ENABLED")

    if any(item.startswith("MISSING_") for item in blockers) or (
        "PAPER_PROFIT_CANDIDATE_FOUND_MISSING" in blockers
    ):
        status = "PAPER_CANDIDATE_NOT_REPRODUCIBLE"
    elif "PAPER_CANDIDATE_SOURCE_WEAK" in blockers:
        status = "PAPER_CANDIDATE_SOURCE_WEAK"
    elif "PAPER_CANDIDATE_TOO_THIN" in blockers:
        status = "PAPER_CANDIDATE_TOO_THIN"
    elif blockers:
        status = "PAPER_CANDIDATE_NOT_REPRODUCIBLE"
    else:
        status = "PAPER_CANDIDATE_AUDIT_PASSED"

    rows = dataset_payload.get("rows", []) or []
    payload = safety_payload(
        schema_version="paper_candidate_audit_v1",
        status=status,
        allowed_statuses=[
            "PAPER_CANDIDATE_AUDIT_PASSED",
            "PAPER_CANDIDATE_AUDIT_FAILED",
            "PAPER_CANDIDATE_NOT_REPRODUCIBLE",
            "PAPER_CANDIDATE_SOURCE_WEAK",
            "PAPER_CANDIDATE_TOO_THIN",
        ],
        candidate_id=paper_payload.get("candidate_id", "pm_weather_forecast_market_mismatch"),
        lane_family="weather / Kalshi weather-market mismatch using historical IEM MOS forecasts",
        source_data_paths=[
            "reports/profit_campaign/latest_profit_campaign.json",
            "reports/sequence52/weather_resolved_dataset/latest_weather_resolved_dataset.json",
            "reports/sequence52/weather_batch_paper_proving/latest_weather_batch_paper_proving.json",
        ],
        proof_row_count=int(paper_payload.get("proof_row_count", 0) or 0),
        sample_period={
            "start": min((row.get("orderbook_ts", "") for row in rows), default=None),
            "end": max((row.get("resolution_ts", "") for row in rows), default=None),
        },
        forecast_source="iem_mos_historical_forecast",
        market_source="kalshi_public_market_data",
        label_source="nws_climatological_report",
        no_lookahead_rule="forecast_ts <= known_at_ts <= orderbook_ts < resolution_ts",
        cost_model=paper_payload.get("cost_model", {}),
        fill_model=paper_payload.get("fill_model", {}),
        baselines=paper_payload.get("baseline_comparison", {}),
        placebos=paper_payload.get("placebo_comparison", {}),
        one_row_dominance_result=paper_payload.get("one_row_dominance", {}),
        oos_walk_forward_status=paper_payload.get("oos_walk_forward_status"),
        source_quality_status=paper_payload.get("source_quality_tier"),
        profit_claim_guard_status="PAPER_PROFIT_CANDIDATE" if not blockers else "NO_PROFIT_CLAIM_ALLOWED",
        reproducibility_command="python -m quant_os.cli readiness paper-candidate-audit",
        blockers=sorted(set(blockers)),
        next_action="Run weather lineage audit." if status == "PAPER_CANDIDATE_AUDIT_PASSED" else "Fix missing candidate evidence.",
    )
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name=JSON_NAME,
        md_name=MD_NAME,
        title="Paper Candidate Audit",
        summary="Audits the stored PAPER_PROFIT_CANDIDATE before canary gates.",
    )
    passed = ["paper_candidate_audit"] if status == "PAPER_CANDIDATE_AUDIT_PASSED" else []
    failed = [] if passed else ["paper_candidate_audit"]
    update_canary_state(
        output_root=output_root,
        gate="paper_candidate_audit",
        gate_status=status,
        evidence_paths=payload["report_paths"],
        gates_passed=passed,
        gates_failed=failed,
        blocker=payload["blockers"][0] if payload["blockers"] else None,
        next_action=payload["next_action"],
    )
    return payload


def write_paper_candidate_audit_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    return evaluate_paper_candidate_audit(output_root=output_root)
