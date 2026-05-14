from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.research.replay_candidates.pm_crypto_updown_alignment import DEFAULT_FIXTURE_ROOT
from quant_os.research.replay_candidates.pm_crypto_updown_baselines import (
    evaluate_pm_crypto_updown_baselines,
)
from quant_os.research.replay_candidates.pm_crypto_updown_costs import (
    apply_pm_crypto_updown_cost_stress,
)
from quant_os.research.replay_candidates.pm_crypto_updown_dataset_report import (
    write_pm_crypto_updown_dataset_report,
)
from quant_os.research.replay_candidates.pm_crypto_updown_fill_stress import (
    apply_pm_crypto_updown_fill_stress,
)
from quant_os.research.replay_candidates.pm_crypto_updown_placebos import (
    run_pm_crypto_updown_placebos,
)
from quant_os.research.replay_candidates.pm_crypto_updown_schema import CANDIDATE_ID
from quant_os.research.replay_candidates.pm_crypto_updown_signals import (
    is_replay_ready_row,
    score_pm_crypto_updown_signals,
)
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

REPORT_ROOT = Path("reports/sequence37/replay_eval")


def evaluate_pm_crypto_updown_replay(
    *,
    fixture_root: str | Path = DEFAULT_FIXTURE_ROOT,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    dataset_report = write_pm_crypto_updown_dataset_report(
        fixture_root=fixture_root,
        output_root=output_root,
    )
    rows = dataset_report["rows"]
    signals = score_pm_crypto_updown_signals(rows)
    baselines = evaluate_pm_crypto_updown_baselines(rows=rows, signal_report=signals)
    placebos = run_pm_crypto_updown_placebos(rows=rows, signal_report=signals)
    costs = apply_pm_crypto_updown_cost_stress(rows=rows, signal_report=signals)
    fills = apply_pm_crypto_updown_fill_stress(rows=rows, cost_report=costs)
    primary_rows = [
        row
        for row in rows
        if is_replay_ready_row(row)
        and row.get("label_status") == "RESOLVED"
        and row.get("resolved_outcome") is not None
    ]
    excluded_rows = [row for row in rows if row not in primary_rows]
    warnings = _confidence_warnings(
        baseline_warnings=baselines["warnings"],
        placebo_warnings=placebos["warnings"],
        primary_row_count=len(primary_rows),
    )
    return {
        "schema_version": "pm_crypto_updown_replay_eval_v1",
        "sequence": "37",
        "candidate_id": CANDIDATE_ID,
        "dataset_readiness_status": dataset_report["readiness_status"],
        "row_count": dataset_report["row_count"],
        "replay_ready_row_count": dataset_report["replay_ready_row_count"],
        "primary_evidence_row_count": len(primary_rows),
        "market_count": dataset_report["market_count"],
        "label_count": dataset_report["resolved_label_count"],
        "candidate_signal_count": signals["candidate_signal_count"],
        "blocked_row_count": len(excluded_rows),
        "primary_rows": primary_rows,
        "excluded_rows": excluded_rows,
        "signal_report": signals,
        "baseline_metrics": baselines,
        "placebo_metrics": placebos,
        "cost_adjusted_metrics": costs,
        "fill_adjusted_metrics": fills,
        "confidence_warnings": warnings,
        "evaluation_status": _evaluation_status(baselines, placebos, costs, fills, warnings),
        "source_dataset_report_path": dataset_report.get("report_paths", {}).get("json"),
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_pm_crypto_updown_replay_eval_report(
    *,
    fixture_root: str | Path = DEFAULT_FIXTURE_ROOT,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    payload = evaluate_pm_crypto_updown_replay(
        fixture_root=fixture_root,
        output_root=output_root,
    )
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _confidence_warnings(
    *,
    baseline_warnings: list[str],
    placebo_warnings: list[str],
    primary_row_count: int,
) -> list[str]:
    warnings = set(baseline_warnings) | set(placebo_warnings)
    if primary_row_count < 20:
        warnings.add("SAMPLE_TOO_THIN_FOR_CONFIDENCE")
    return sorted(warnings)


def _evaluation_status(
    baselines: dict[str, Any],
    placebos: dict[str, Any],
    costs: dict[str, Any],
    fills: dict[str, Any],
    warnings: list[str],
) -> str:
    if "SAMPLE_TOO_THIN_FOR_CONFIDENCE" in warnings:
        return "CANDIDATE_REPLAY_TOO_THIN"
    if not baselines["candidate_beats_market_baseline"] or not baselines["candidate_beats_no_skill"]:
        return "BASELINES_NOT_BEATEN"
    if not placebos["candidate_beats_placebos_for_readiness"]:
        return "PLACEBO_NOT_BEATEN"
    if costs["costs_destroy_edge"]:
        return "COSTS_DESTROY_EDGE"
    if fills["fill_realism_blocks_edge"]:
        return "FILL_REALISM_BLOCKS_EDGE"
    return "READY_FOR_EXPANDED_SHADOW_REPLAY"


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_pm_crypto_updown_replay_eval.json"
    md_path = root / "latest_pm_crypto_updown_replay_eval.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 37 PM Crypto UP/DOWN Replay Evaluation",
        "",
        "Candidate replay evaluation with baselines, placebos, cost stress, and fill stress.",
        "",
        f"Status: {payload['evaluation_status']}",
        f"Rows: {payload['row_count']}",
        f"Replay-ready rows: {payload['replay_ready_row_count']}",
        f"Primary evidence rows: {payload['primary_evidence_row_count']}",
        f"Candidate signals: {payload['candidate_signal_count']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        "",
        "## Warnings",
    ]
    lines.extend(f"- {item}" for item in (payload["confidence_warnings"] or ["None"]))
    lines.extend(
        [
            "",
            "## Baselines",
            "- Candidate beats market baseline: "
            f"{payload['baseline_metrics']['candidate_beats_market_baseline']}",
            "- Candidate beats no-skill: "
            f"{payload['baseline_metrics']['candidate_beats_no_skill']}",
            "",
            "## Placebos",
            f"- Status: {payload['placebo_metrics']['placebo_comparison_status']}",
            "",
            "## Cost and Fill",
            f"- Costs destroy edge: {payload['cost_adjusted_metrics']['costs_destroy_edge']}",
            "- Fill realism blocks edge: "
            f"{payload['fill_adjusted_metrics']['fill_realism_blocks_edge']}",
        ]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
