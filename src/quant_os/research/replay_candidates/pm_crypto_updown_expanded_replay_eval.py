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
from quant_os.research.replay_candidates.pm_crypto_updown_evidence_quality import (
    write_pm_crypto_updown_evidence_quality_report,
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

REPORT_ROOT = Path("reports/sequence38/expanded_replay_eval")


def evaluate_pm_crypto_updown_expanded_replay(
    *,
    fixture_root: str | Path = DEFAULT_FIXTURE_ROOT,
    output_root: str | Path = ".",
    capture_root: str | Path | None = None,
) -> dict[str, Any]:
    quality = write_pm_crypto_updown_evidence_quality_report(
        fixture_root=fixture_root,
        output_root=output_root,
        capture_root=capture_root,
    )
    rows = quality["dataset_report"]["rows"]
    primary_rows = quality["dataset_report"]["primary_rows"]
    fixture_rows = [row for row in rows if row["source_quality"] == "fixture_real_shaped"]
    synthetic_rows = [row for row in rows if row["source_quality"] == "synthetic_stress"]
    real_cached_rows = [row for row in rows if row["source_quality"] == "real_cached"]

    primary_result = _evaluate_row_group(primary_rows)
    fixture_result = _evaluate_row_group(fixture_rows)
    synthetic_result = _evaluate_row_group(synthetic_rows)
    real_cached_result = _evaluate_row_group(real_cached_rows)
    blockers = list(quality["blockers"])
    return {
        "schema_version": "pm_crypto_updown_expanded_replay_eval_v1",
        "sequence": "38",
        "candidate_id": CANDIDATE_ID,
        "evaluation_status": quality["candidate_status"],
        "evidence_expansion_status": quality["evidence_expansion_status"],
        "minimum_primary_replay_ready_rows": quality["minimum_primary_replay_ready_rows"],
        "row_count": quality["row_count"],
        "replay_ready_row_count": quality["replay_ready_row_count"],
        "primary_evidence_row_count": quality["primary_evidence_row_count"],
        "primary_result": primary_result,
        "real_cached_result": real_cached_result,
        "fixture_diagnostic_result": fixture_result,
        "synthetic_stress_result": synthetic_result,
        "synthetic_rows_counted_as_primary": any(
            row["source_quality"] == "synthetic_stress" for row in primary_rows
        ),
        "readiness_blockers": blockers,
        "evidence_quality_report_path": quality.get("report_paths", {}).get("json"),
        "evidence_quality": quality,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_pm_crypto_updown_expanded_replay_eval_report(
    *,
    fixture_root: str | Path = DEFAULT_FIXTURE_ROOT,
    output_root: str | Path = ".",
    capture_root: str | Path | None = None,
) -> dict[str, Any]:
    payload = evaluate_pm_crypto_updown_expanded_replay(
        fixture_root=fixture_root,
        output_root=output_root,
        capture_root=capture_root,
    )
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _evaluate_row_group(rows: list[dict[str, Any]]) -> dict[str, Any]:
    signals = score_pm_crypto_updown_signals(rows)
    baselines = evaluate_pm_crypto_updown_baselines(rows=rows, signal_report=signals)
    placebos = run_pm_crypto_updown_placebos(rows=rows, signal_report=signals)
    costs = apply_pm_crypto_updown_cost_stress(rows=rows, signal_report=signals)
    fills = apply_pm_crypto_updown_fill_stress(rows=rows, cost_report=costs)
    return {
        "row_count": len(rows),
        "replay_ready_row_count": len([row for row in rows if is_replay_ready_row(row)]),
        "signal_report": signals,
        "baseline_metrics": baselines,
        "placebo_metrics": placebos,
        "cost_adjusted_metrics": costs,
        "fill_adjusted_metrics": fills,
    }


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_expanded_replay_eval.json"
    md_path = root / "latest_expanded_replay_eval.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 38 Expanded Replay Evaluation",
        "",
        "Expanded replay eval split by primary, real-cached, fixture, and synthetic rows.",
        "",
        f"Status: {payload['evaluation_status']}",
        f"Primary evidence rows: {payload['primary_evidence_row_count']}",
        f"Primary result rows: {payload['primary_result']['row_count']}",
        f"Fixture diagnostic rows: {payload['fixture_diagnostic_result']['row_count']}",
        f"Synthetic stress rows: {payload['synthetic_stress_result']['row_count']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        "",
        "## Blockers",
    ]
    lines.extend(f"- {item}" for item in (payload["readiness_blockers"] or ["None"]))
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
