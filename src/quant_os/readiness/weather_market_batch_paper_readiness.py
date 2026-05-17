from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.proving.weather_market_batch_paper_proving import (
    run_weather_market_batch_paper_proving,
)
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

REPORT_ROOT = Path("reports/sequence52/weather_batch_readiness")

ALLOWED_PHASE52_STATUSES = [
    "PAPER_PROFIT_CANDIDATE",
    "PAPER_PROFIT_DIAGNOSTIC_ONLY",
    "SELECTED_LANE_NEEDS_MORE_DATA",
    "RESOLVED_WEATHER_BATCH_READY",
    "WEATHER_PROOF_ROWS_BUILT",
    "RESOLUTION_LABELS_MISSING",
    "WEATHER_MARKET_BACKFILL_BLOCKED",
    "MARKET_DATA_CAPTURE_BLOCKED",
    "PAPER_PROFIT_BLOCKED_BY_SAMPLE",
    "PAPER_PROFIT_BLOCKED_BY_BASELINE",
    "PAPER_PROFIT_BLOCKED_BY_PLACEBO",
    "PAPER_PROFIT_BLOCKED_BY_COSTS",
    "PAPER_PROFIT_BLOCKED_BY_FILLS",
    "NO_PROFIT_CLAIM_ALLOWED",
]


def evaluate_weather_market_batch_paper_readiness(
    *,
    dataset_payload: dict[str, Any] | None = None,
    paper_payload: dict[str, Any] | None = None,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    dataset_payload = dataset_payload or {
        "dataset_status": "WEATHER_MARKET_BACKFILL_BLOCKED",
        "rows": [],
        "real_public_row_count": 0,
        "proof_row_count": 0,
        "fixture_row_count": 0,
        "blockers": ["NO_RESOLVED_WEATHER_BATCH"],
    }
    paper_payload = paper_payload or run_weather_market_batch_paper_proving(
        dataset_payload.get("rows", []),
        output_root=output_root,
    )
    blockers = _blockers(dataset_payload=dataset_payload, paper_payload=paper_payload)
    readiness_status = _readiness_status(
        dataset_payload=dataset_payload,
        paper_payload=paper_payload,
        blockers=blockers,
    )
    candidate = readiness_status == "PAPER_PROFIT_CANDIDATE" and not blockers
    payload = {
        "schema_version": "weather_market_batch_paper_readiness_v1",
        "sequence": "52",
        "candidate_id": "pm_weather_forecast_market_mismatch",
        "readiness_status": readiness_status,
        "paper_profit_status": "PAPER_PROFIT_CANDIDATE"
        if candidate
        else "NO_PROFIT_CLAIM_ALLOWED",
        "allowed_statuses": ALLOWED_PHASE52_STATUSES,
        "paper_profit_candidate": candidate,
        "blockers": blockers,
        "dataset_status": dataset_payload.get("dataset_status"),
        "paper_proving_status": paper_payload.get("readiness_status"),
        "row_count": len(dataset_payload.get("rows", []))
        + len(dataset_payload.get("pending_rows", [])),
        "real_public_row_count": dataset_payload.get("real_public_row_count", 0),
        "proof_row_count": dataset_payload.get("proof_row_count", 0),
        "fixture_row_count": dataset_payload.get("fixture_row_count", 0),
        "sample_warnings": paper_payload.get("sample_warnings", []),
        "oos_walk_forward_status": paper_payload.get("oos_walk_forward_status"),
        "source_quality_warnings": paper_payload.get("source_quality_warnings", []),
        "profitable_label_allowed": False,
        "live_ready_label_allowed": False,
        "canary_ready": False,
        "live_ready": False,
        "canary_readiness_claimed": False,
        "live_readiness_claimed": False,
        "autonomy_milestones": _autonomy_milestones(
            dataset_payload=dataset_payload,
            paper_payload=paper_payload,
            readiness_status=readiness_status,
        ),
        "exact_next_commands": _next_commands(readiness_status),
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
        **SOCIAL_INTAKE_SAFETY,
    }
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def write_weather_market_batch_paper_readiness_report(
    *,
    output_root: str | Path = ".",
    dataset_payload: dict[str, Any] | None = None,
    paper_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if dataset_payload is None:
        from quant_os.research.replay_candidates.weather_market_resolved_dataset_builder import (
            write_weather_market_resolved_dataset_report,
        )

        dataset_payload = write_weather_market_resolved_dataset_report(output_root=output_root)
    if paper_payload is None:
        paper_payload = run_weather_market_batch_paper_proving(
            dataset_payload.get("rows", []),
            output_root=output_root,
        )
    return evaluate_weather_market_batch_paper_readiness(
        dataset_payload=dataset_payload,
        paper_payload=paper_payload,
        output_root=output_root,
    )


def _blockers(*, dataset_payload: dict[str, Any], paper_payload: dict[str, Any]) -> list[str]:
    blockers = set(dataset_payload.get("blockers", []))
    fixture_rows = int(dataset_payload.get("fixture_row_count", 0) or 0)
    real_rows = int(dataset_payload.get("real_public_row_count", 0) or 0)
    proof_rows = int(dataset_payload.get("proof_row_count", 0) or 0)
    if fixture_rows and not real_rows:
        blockers.add("FIXTURE_ROWS_CANNOT_SUPPORT_PROOF")
    if real_rows == 0:
        blockers.add("NO_REAL_PUBLIC_ROWS")
    if proof_rows == 0 and real_rows:
        blockers.add("RESOLUTION_LABELS_MISSING")
    if proof_rows and proof_rows < 30:
        blockers.add("SAMPLE_TOO_THIN")
    if paper_payload.get("oos_walk_forward_status") != "OOS_WALK_FORWARD_AVAILABLE":
        blockers.add("OOS_WALK_FORWARD_MISSING")
    if paper_payload.get("costs_included") is not True:
        blockers.add("COST_MODEL_MISSING")
    if paper_payload.get("fill_assumptions_included") is not True:
        blockers.add("FILL_MODEL_MISSING")
    if not paper_payload.get("baseline_comparison", {}).get("included"):
        blockers.add("BASELINE_COMPARISON_MISSING")
    elif paper_payload.get("baseline_comparison", {}).get("paper_beats_comparison") is not True:
        blockers.add("BASELINE_COMPARISON_NOT_BEATEN")
    if not paper_payload.get("placebo_comparison", {}).get("included"):
        blockers.add("PLACEBO_COMPARISON_MISSING")
    elif paper_payload.get("placebo_comparison", {}).get("paper_beats_comparison") is not True:
        blockers.add("PLACEBO_COMPARISON_NOT_BEATEN")
    if paper_payload.get("one_row_dominance", {}).get("detected"):
        blockers.add("ONE_ROW_DOMINANCE")
    if paper_payload.get("synthetic_rows_counted_as_profit_evidence") is True:
        blockers.add("SYNTHETIC_ROWS_COUNTED_AS_EVIDENCE")
    if paper_payload.get("execution_authority") != "NONE":
        blockers.add("EXECUTION_AUTHORITY_PRESENT")
    if paper_payload.get("live_trading_enabled") is True:
        blockers.add("LIVE_TRADING_ENABLED")
    return sorted(blockers)


def _readiness_status(
    *,
    dataset_payload: dict[str, Any],
    paper_payload: dict[str, Any],
    blockers: list[str],
) -> str:
    dataset_status = dataset_payload.get("dataset_status")
    if dataset_status == "WEATHER_MARKET_BACKFILL_BLOCKED":
        return "WEATHER_MARKET_BACKFILL_BLOCKED"
    if dataset_status == "MARKET_DATA_CAPTURE_BLOCKED":
        return "MARKET_DATA_CAPTURE_BLOCKED"
    if "FIXTURE_ROWS_CANNOT_SUPPORT_PROOF" in blockers and not dataset_payload.get(
        "real_public_row_count",
        0,
    ):
        return "NO_PROFIT_CLAIM_ALLOWED"
    if "RESOLUTION_LABELS_MISSING" in blockers:
        return "RESOLUTION_LABELS_MISSING"
    if "SAMPLE_TOO_THIN" in blockers:
        return "PAPER_PROFIT_BLOCKED_BY_SAMPLE"
    if "BASELINE_COMPARISON_MISSING" in blockers:
        return "PAPER_PROFIT_BLOCKED_BY_BASELINE"
    if "BASELINE_COMPARISON_NOT_BEATEN" in blockers:
        return "PAPER_PROFIT_BLOCKED_BY_BASELINE"
    if "PLACEBO_COMPARISON_MISSING" in blockers:
        return "PAPER_PROFIT_BLOCKED_BY_PLACEBO"
    if "PLACEBO_COMPARISON_NOT_BEATEN" in blockers:
        return "PAPER_PROFIT_BLOCKED_BY_PLACEBO"
    if "COST_MODEL_MISSING" in blockers:
        return "PAPER_PROFIT_BLOCKED_BY_COSTS"
    if "FILL_MODEL_MISSING" in blockers:
        return "PAPER_PROFIT_BLOCKED_BY_FILLS"
    if blockers:
        return "PAPER_PROFIT_DIAGNOSTIC_ONLY"
    if paper_payload.get("readiness_status") == "PAPER_PROFIT_CANDIDATE":
        return "PAPER_PROFIT_CANDIDATE"
    return "SELECTED_LANE_NEEDS_MORE_DATA"


def _autonomy_milestones(
    *,
    dataset_payload: dict[str, Any],
    paper_payload: dict[str, Any],
    readiness_status: str,
) -> dict[str, str]:
    real_rows = int(dataset_payload.get("real_public_row_count", 0))
    proof_rows = int(dataset_payload.get("proof_row_count", 0))
    return {
        "weather_lane_selected": "met",
        "single_public_capture": "met",
        "resolved_weather_batch_acquisition": "met" if real_rows else "blocked",
        "proof_rows": "met" if proof_rows else "partial" if real_rows else "blocked",
        "paper_proving_with_proof_rows": "met" if proof_rows else "blocked",
        "paper_profit_candidate": "met"
        if readiness_status == "PAPER_PROFIT_CANDIDATE"
        else "blocked",
        "bounded_shadow_rehearsal": "blocked",
        "canary_live": "blocked",
        "source_quality": "partial"
        if paper_payload.get("source_quality_warnings")
        else "met",
    }


def _next_commands(readiness_status: str) -> list[str]:
    if readiness_status in {"WEATHER_MARKET_BACKFILL_BLOCKED", "MARKET_DATA_CAPTURE_BLOCKED"}:
        return [
            "python -m quant_os.cli data weather-resolved-market-discovery --public-network-ok",
            "python -m quant_os.cli data weather-market-batch-capture --public-network-ok",
        ]
    if readiness_status == "RESOLUTION_LABELS_MISSING":
        return [
            "python -m quant_os.cli data weather-resolution-labels --public-network-ok",
            "python -m quant_os.cli data weather-pending-resolution-monitor",
        ]
    return ["python -m quant_os.cli readiness weather-batch-paper-readiness"]


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_weather_batch_readiness.json"
    md_path = root / "latest_weather_batch_readiness.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 52 Weather Batch Paper Readiness",
        "",
        "Blocks unsupported paper-profit, canary, and live-readiness claims.",
        "",
        f"Status: {payload['readiness_status']}",
        f"Paper profit status: {payload['paper_profit_status']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        f"Execution authority: {payload['execution_authority']}",
        "",
        "## Blockers",
    ]
    lines.extend(f"- {item}" for item in payload["blockers"] or ["None"])
    lines.extend(["", "## Next Commands"])
    lines.extend(f"- `{item}`" for item in payload["exact_next_commands"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
