from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from quant_os.proving.paper_proving_models import PAPER_PROVING_SAFETY, decimal_value
from quant_os.proving.profit_claim_guard import evaluate_profit_claim_guard

REPORT_ROOT = Path("reports/profit_campaign/profit_guard")


def evaluate_relentless_profit_guard(paper_report: dict[str, Any]) -> dict[str, Any]:
    base_guard = evaluate_profit_claim_guard(paper_report)
    blockers = _dedupe([*base_guard.get("blockers", []), *_strict_blockers(paper_report)])
    net = decimal_value(paper_report.get("net_simulated_pnl_after_costs"))
    base_approved = base_guard.get("claim_status") == "PAPER_PROFIT_CANDIDATE"
    candidate = not blockers and net > Decimal("0") and base_approved
    return {
        "schema_version": "relentless_profit_guard_v1",
        "lane_id": paper_report.get("lane_id"),
        "claim_status": "PAPER_PROFIT_CANDIDATE" if candidate else "NO_PROFIT_CLAIM_ALLOWED",
        "paper_profit_candidate": candidate,
        "all_required_gates_passed": candidate,
        "base_profit_claim_guard_status": base_guard.get("claim_status"),
        "blockers": blockers,
        "required_gates": _required_gates(paper_report, blockers=blockers),
        "profitable_label_allowed": False,
        "live_ready_label_allowed": False,
        "canary_ready": False,
        "live_ready": False,
        "canary_readiness_claimed": False,
        "live_readiness_claimed": False,
        "profit_claim_made": False,
        **PAPER_PROVING_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_relentless_profit_guard_report(
    *,
    output_root: str | Path = ".",
    paper_report: dict[str, Any],
) -> dict[str, Any]:
    payload = evaluate_relentless_profit_guard(paper_report)
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _strict_blockers(paper_report: dict[str, Any]) -> list[str]:
    blockers = []
    source_quality = paper_report.get("source_quality_tier")
    if source_quality in {"SYNTHETIC_ONLY", "UNKNOWN", "WEAK", None}:
        blockers.append("SOURCE_QUALITY_TOO_WEAK")
    if source_quality == "SYNTHETIC_ONLY":
        blockers.append("SYNTHETIC_ONLY_DATA")
    sample_count = _sample_count(paper_report)
    minimum_sample_size = int(paper_report.get("minimum_sample_size", 30) or 30)
    if sample_count < minimum_sample_size:
        blockers.append("SAMPLE_TOO_THIN")
    if paper_report.get("no_lookahead") is not True:
        blockers.append("NO_LOOKAHEAD_NOT_PROVEN")
    if paper_report.get("labels_valid", True) is not True:
        blockers.append("LABELS_OR_RESOLUTION_INVALID")
    if paper_report.get("costs_included") is not True:
        blockers.append("COST_MODEL_MISSING")
    if not _spread_and_slippage_included(paper_report.get("cost_model")):
        blockers.append("SPREAD_SLIPPAGE_MODEL_MISSING")
    if paper_report.get("fill_assumptions_included") is not True:
        blockers.append("FILL_MODEL_MISSING")
    baseline = paper_report.get("baseline_comparison", {})
    if not baseline.get("included"):
        blockers.append("BASELINE_COMPARISON_MISSING")
    elif baseline.get("paper_beats_comparison") is not True:
        blockers.append("BASELINE_COMPARISON_NOT_BEATEN")
    placebo = paper_report.get("placebo_comparison", {})
    if not placebo.get("included"):
        blockers.append("PLACEBO_COMPARISON_MISSING")
    elif placebo.get("paper_beats_comparison") is not True:
        blockers.append("PLACEBO_COMPARISON_NOT_BEATEN")
    if paper_report.get("one_row_dominance", {}).get("detected") is True:
        blockers.append("ONE_ROW_DOMINANCE")
    if (
        sample_count >= minimum_sample_size
        and paper_report.get("oos_walk_forward_status") != "OOS_WALK_FORWARD_AVAILABLE"
    ):
        blockers.append("OOS_WALK_FORWARD_MISSING")
    if paper_report.get("requires_private_or_authenticated_data") is True:
        blockers.append("PRIVATE_OR_AUTHENTICATED_DATA_DEPENDENCY")
    if paper_report.get("copy_trading_enabled") is True:
        blockers.append("COPY_TRADE_OR_WALLET_MIRRORING_PRESENT")
    if paper_report.get("wallet_signing_enabled") is True:
        blockers.append("WALLET_SIGNING_ENABLED")
    if (
        paper_report.get("requires_leverage") is True
        or paper_report.get("requires_futures_or_margin") is True
        or paper_report.get("requires_options") is True
    ):
        blockers.append("LEVERAGE_FUTURES_MARGIN_OR_OPTIONS_DEPENDENCY")
    if paper_report.get("live_trading_enabled") is True:
        blockers.append("LIVE_TRADING_ENABLED")
    if paper_report.get("execution_authority") != "NONE":
        blockers.append("EXECUTION_AUTHORITY_PRESENT")
    if paper_report.get("synthetic_rows_counted_as_profit_evidence") is True:
        blockers.append("SYNTHETIC_ROWS_COUNTED_AS_EVIDENCE")
    if not paper_report.get("reproducible_commands"):
        blockers.append("REPRODUCIBLE_COMMANDS_MISSING")
    return blockers


def _required_gates(paper_report: dict[str, Any], *, blockers: list[str]) -> dict[str, bool]:
    failed = set(blockers)
    return {
        "non_fixture_public_data": "SOURCE_QUALITY_TOO_WEAK" not in failed
        and "SYNTHETIC_ONLY_DATA" not in failed,
        "sample_above_minimum": "SAMPLE_TOO_THIN" not in failed,
        "no_lookahead": "NO_LOOKAHEAD_NOT_PROVEN" not in failed,
        "labels_valid": "LABELS_OR_RESOLUTION_INVALID" not in failed,
        "costs_spreads_slippage_included": "COST_MODEL_MISSING" not in failed
        and "SPREAD_SLIPPAGE_MODEL_MISSING" not in failed,
        "fill_model_included": "FILL_MODEL_MISSING" not in failed,
        "baseline_passed": "BASELINE_COMPARISON_MISSING" not in failed
        and "BASELINE_COMPARISON_NOT_BEATEN" not in failed,
        "placebo_passed": "PLACEBO_COMPARISON_MISSING" not in failed
        and "PLACEBO_COMPARISON_NOT_BEATEN" not in failed,
        "one_row_dominance_passed": "ONE_ROW_DOMINANCE" not in failed,
        "oos_walk_forward_passed": "OOS_WALK_FORWARD_MISSING" not in failed,
        "public_unrestricted_data_only": "PRIVATE_OR_AUTHENTICATED_DATA_DEPENDENCY" not in failed,
        "no_wallet_or_mirroring": "COPY_TRADE_OR_WALLET_MIRRORING_PRESENT" not in failed
        and "WALLET_SIGNING_ENABLED" not in failed,
        "no_leverage_futures_margin_options": (
            "LEVERAGE_FUTURES_MARGIN_OR_OPTIONS_DEPENDENCY" not in failed
        ),
        "live_authority_false": "LIVE_TRADING_ENABLED" not in failed
        and "EXECUTION_AUTHORITY_PRESENT" not in failed,
        "reproducible": "REPRODUCIBLE_COMMANDS_MISSING" not in failed,
        "net_positive": decimal_value(paper_report.get("net_simulated_pnl_after_costs")) > 0,
    }


def _sample_count(paper_report: dict[str, Any]) -> int:
    return int(
        paper_report.get("proof_row_count")
        or paper_report.get("trade_count")
        or paper_report.get("row_count")
        or 0
    )


def _spread_and_slippage_included(cost_model: Any) -> bool:
    if not isinstance(cost_model, dict):
        return False
    spread = decimal_value(cost_model.get("spread_bps") or cost_model.get("adverse_selection_bps"))
    slippage = decimal_value(cost_model.get("slippage_bps"))
    return spread > 0 and slippage > 0


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_relentless_profit_guard.json"
    md_path = root / "latest_relentless_profit_guard.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Relentless Profit Guard",
        "",
        "Strict PAPER_PROFIT_CANDIDATE gate. No live or canary readiness claim.",
        "",
        f"Status: {payload['claim_status']}",
        f"Lane: {payload['lane_id']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        f"Execution authority: {payload['execution_authority']}",
        "",
        "## Blockers",
    ]
    lines.extend(f"- {item}" for item in payload["blockers"] or ["None"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def _dedupe(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result
