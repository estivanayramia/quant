from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from quant_os.proving.paper_proving_harness import (
    build_default_paper_proving_input,
    run_paper_proving,
)
from quant_os.proving.paper_proving_models import PAPER_PROVING_SAFETY, decimal_value

REPORT_ROOT = Path("reports/sequence49/profit_claim_guard")

ALLOWED_CLAIM_STATUSES = [
    "PAPER_PROFIT_DIAGNOSTIC_ONLY",
    "PAPER_PROFIT_CANDIDATE",
    "PAPER_PROFIT_BLOCKED",
    "NO_PROFIT_CLAIM_ALLOWED",
]


def evaluate_profit_claim_guard(paper_report: dict[str, Any]) -> dict[str, Any]:
    blockers = _guard_blockers(paper_report)
    net = decimal_value(paper_report.get("net_simulated_pnl_after_costs"))
    claim_status = _claim_status(blockers=blockers, net=net)
    return {
        "schema_version": "profit_claim_guard_v1",
        "sequence": "49",
        "lane_id": paper_report.get("lane_id"),
        "claim_status": claim_status,
        "allowed_statuses": ALLOWED_CLAIM_STATUSES,
        "blockers": blockers,
        "net_simulated_pnl_after_costs": paper_report.get("net_simulated_pnl_after_costs"),
        "paper_readiness_status": paper_report.get("readiness_status"),
        "profitable_label_allowed": False,
        "live_ready_label_allowed": False,
        "blocked_label_families": [
            "profit_certainty_language",
            "guarantee_language",
            "live_or_canary_readiness_language",
        ],
        "profit_claim_made": False,
        **PAPER_PROVING_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_profit_claim_guard_report(
    *,
    output_root: str | Path = ".",
    paper_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    paper_report = paper_report or run_paper_proving(build_default_paper_proving_input())
    payload = evaluate_profit_claim_guard(paper_report)
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _guard_blockers(paper_report: dict[str, Any]) -> list[str]:
    blockers = []
    if paper_report.get("source_quality_tier") == "SYNTHETIC_ONLY":
        blockers.append("SYNTHETIC_ONLY_DATA")
    if "SAMPLE_TOO_THIN" in paper_report.get("sample_warnings", []):
        blockers.append("SAMPLE_TOO_THIN")
    if not paper_report.get("costs_included"):
        blockers.append("COST_MODEL_MISSING")
    if not paper_report.get("fill_assumptions_included"):
        blockers.append("FILL_MODEL_MISSING")
    if not paper_report.get("baseline_comparison", {}).get("included"):
        blockers.append("BASELINE_COMPARISON_MISSING")
    if not paper_report.get("placebo_comparison", {}).get("included"):
        blockers.append("PLACEBO_COMPARISON_MISSING")
    if paper_report.get("oos_walk_forward_status") == "OOS_WALK_FORWARD_MISSING":
        blockers.append("OOS_WALK_FORWARD_MISSING")
    if paper_report.get("one_row_dominance", {}).get("detected"):
        blockers.append("ONE_ROW_DOMINANCE")
    if paper_report.get("source_quality_tier") in {"UNKNOWN", "WEAK", None}:
        blockers.append("SOURCE_QUALITY_TOO_WEAK")
    if paper_report.get("synthetic_rows_counted_as_profit_evidence") is True:
        blockers.append("SYNTHETIC_ROWS_COUNTED_AS_EVIDENCE")
    if paper_report.get("execution_authority") != "NONE":
        blockers.append("EXECUTION_AUTHORITY_PRESENT")
    if paper_report.get("live_trading_enabled") is True:
        blockers.append("LIVE_TRADING_ENABLED")
    if paper_report.get("wallet_signing_enabled") is True:
        blockers.append("WALLET_SIGNING_ENABLED")
    if paper_report.get("copy_trading_enabled") is True:
        blockers.append("COPY_TRADE_OR_WALLET_MIRRORING_PRESENT")
    if paper_report.get("requires_private_or_authenticated_data") is True:
        blockers.append("PRIVATE_OR_AUTHENTICATED_DATA_DEPENDENCY")
    return _dedupe(blockers)


def _claim_status(*, blockers: list[str], net: Decimal) -> str:
    if blockers:
        return "NO_PROFIT_CLAIM_ALLOWED"
    if net <= 0:
        return "PAPER_PROFIT_BLOCKED"
    return "PAPER_PROFIT_CANDIDATE"


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_profit_claim_guard.json"
    md_path = root / "latest_profit_claim_guard.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 49 Profit Claim Guard",
        "",
        "Blocks unsupported paper-profit language. No live or canary readiness claim.",
        "",
        f"Status: {payload['claim_status']}",
        f"Lane: {payload['lane_id']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        f"Execution authority: {payload['execution_authority']}",
        "",
        "## Blockers",
    ]
    lines.extend(f"- {item}" for item in payload["blockers"] or ["None"])
    lines.extend(["", "## Blocked Label Families"])
    lines.extend(f"- {item}" for item in payload["blocked_label_families"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped = []
    for item in items:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped
