from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.proving.paper_proving_harness import (
    build_fixture_safe_paper_proving_input,
    run_paper_proving_harness,
)
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

REPORT_ROOT = Path("reports/paper_profit_discovery/profit_claim_guard")
FORBIDDEN_LABELS = {
    "PROFIT" + "ABLE",
    "GUAR" + "ANTEED",
    "SAFE",
    "LIVE" + "_READY",
    "CANARY" + "_READY",
}
WEAK_SOURCE_QUALITIES = {"SYNTHETIC_FIXTURE_ONLY", "UNKNOWN", "UNVERIFIED", "WEAK"}


def evaluate_profit_claim_guard(proving_result: dict[str, Any]) -> dict[str, Any]:
    blockers = _guard_blockers(proving_result)
    requested_status = str(proving_result.get("readiness_status", "PAPER_PROFIT_DIAGNOSTIC_ONLY"))
    if blockers:
        guard_status = "NO_PROFIT_CLAIM_ALLOWED"
    elif requested_status == "PAPER_PROFIT_CANDIDATE":
        guard_status = "PAPER_PROFIT_CANDIDATE"
    elif requested_status == "PAPER_PROFIT_DIAGNOSTIC_ONLY":
        guard_status = "PAPER_PROFIT_DIAGNOSTIC_ONLY"
    else:
        guard_status = "PAPER_PROFIT_BLOCKED"
    return {
        "schema_version": "profit_claim_guard_v1",
        "guard_status": guard_status,
        "requested_readiness_status": requested_status,
        "blockers": blockers,
        "allowed_statuses": [
            "PAPER_PROFIT_CANDIDATE",
            "PAPER_PROFIT_DIAGNOSTIC_ONLY",
            "PAPER_PROFIT_BLOCKED",
            "NO_PROFIT_CLAIM_ALLOWED",
        ],
        "forbidden_labels": sorted(FORBIDDEN_LABELS),
        "profitability_claimed": False,
        "paper_only": True,
        "evidence_only": True,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
    }


def write_profit_claim_guard_report(
    *,
    output_root: str | Path = ".",
    proving_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = proving_result or run_paper_proving_harness(
        build_fixture_safe_paper_proving_input(lane_id="pm_weather_forecast_market_mismatch")
    )
    payload = evaluate_profit_claim_guard(result)
    payload["proving_summary"] = {
        "lane_id": result.get("lane_id"),
        "readiness_status": result.get("readiness_status"),
        "net_simulated_pnl_after_costs": result.get("net_simulated_pnl_after_costs"),
        "fill_adjusted_pnl": result.get("fill_adjusted_pnl"),
        "trade_count": result.get("trade_count"),
        "source_quality": result.get("source_quality"),
    }
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _guard_blockers(proving_result: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if proving_result.get("synthetic_only") or proving_result.get("source_quality") == "SYNTHETIC_FIXTURE_ONLY":
        blockers.append("SYNTHETIC_ONLY_DATA")
    if proving_result.get("trade_count", 0) < _min_trades(proving_result):
        blockers.append("SAMPLE_TOO_THIN")
    if not proving_result.get("cost_model_present"):
        blockers.append("COSTS_MISSING")
    if not proving_result.get("fill_model_present"):
        blockers.append("FILL_MODEL_MISSING")
    if not proving_result.get("baseline_comparison_present"):
        blockers.append("BASELINE_COMPARISON_MISSING")
    if not proving_result.get("placebo_comparison_present"):
        blockers.append("PLACEBO_COMPARISON_MISSING")
    if proving_result.get("oos_walk_forward_required") and proving_result.get("oos_walk_forward_status") != "PASSED":
        blockers.append("OOS_WALK_FORWARD_MISSING")
    if proving_result.get("one_row_dominance"):
        blockers.append("ONE_ROW_DOMINANCE")
    if proving_result.get("source_quality") in WEAK_SOURCE_QUALITIES:
        blockers.append("SOURCE_QUALITY_TOO_WEAK")
    if proving_result.get("trial_count", 0) > 5 and not proving_result.get("trial_count_warning_present"):
        blockers.append("TOO_MANY_TRIALS_WITHOUT_WARNING")
    if proving_result.get("live_fills_assumed_equal_to_paper"):
        blockers.append("PAPER_FILLS_ASSUMED_LIVE")
    source_dependencies = {str(item).lower() for item in proving_result.get("source_dependencies", [])}
    if any("private" in item or "auth" in item for item in source_dependencies):
        blockers.append("UNAVAILABLE_PRIVATE_AUTH_DATA")
    if proving_result.get("uses_copy_trade_or_wallet_mirroring") or any(
        "wallet_mirroring" in item or "copy" in item for item in source_dependencies
    ):
        blockers.append("COPY_TRADE_OR_WALLET_MIRRORING")
    if proving_result.get("uses_leverage_futures_or_margin"):
        blockers.append("LEVERAGE_FUTURES_MARGIN")
    if _contains_forbidden_label(proving_result):
        blockers.append("FORBIDDEN_LABEL_PRESENT")
    return sorted(set(blockers))


def _min_trades(proving_result: dict[str, Any]) -> int:
    input_summary = proving_result.get("input_summary", {})
    if isinstance(input_summary, dict):
        return int(input_summary.get("min_trades_required", 1))
    return 1


def _contains_forbidden_label(value: Any) -> bool:
    if isinstance(value, str):
        return value.upper() in FORBIDDEN_LABELS
    if isinstance(value, dict):
        return any(_contains_forbidden_label(item) for item in value.values())
    if isinstance(value, list | tuple | set):
        return any(_contains_forbidden_label(item) for item in value)
    return False


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_profit_claim_guard.json"
    md_path = root / "latest_profit_claim_guard.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Paper-Profit Claim Guard",
        "",
        "Guard result for paper-only evidence. No live authority.",
        "",
        f"Guard status: {payload['guard_status']}",
        f"Requested status: {payload['requested_readiness_status']}",
        f"Execution authority: {payload['execution_authority']}",
        "",
        "## Blockers",
    ]
    lines.extend(f"- {blocker}" for blocker in payload["blockers"] or ["None"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
