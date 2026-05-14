from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.research.replay_candidates.pm_crypto_updown_dataset_builder import (
    MIN_PRIMARY_REPLAY_READY_ROWS,
)
from quant_os.research.replay_candidates.pm_crypto_updown_expanded_replay_eval import (
    _evaluate_row_group,
)
from quant_os.research.replay_candidates.pm_crypto_updown_schema import CANDIDATE_ID
from quant_os.research.replay_candidates.pm_crypto_updown_threshold_progress import (
    write_pm_crypto_updown_threshold_progress_report,
)
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

REPORT_ROOT = Path("reports/sequence39/real_cached_replay_eval")


def evaluate_pm_crypto_updown_real_cached_replay(
    *,
    fixture_root: str | Path,
    output_root: str | Path = ".",
    real_cached_artifact_roots: list[str | Path] | None = None,
) -> dict[str, Any]:
    progress = write_pm_crypto_updown_threshold_progress_report(
        fixture_root=fixture_root,
        output_root=output_root,
        real_cached_artifact_roots=real_cached_artifact_roots,
    )
    dataset = progress["dataset_report"]
    rows = dataset["rows"]
    primary_rows = dataset["primary_rows"]
    fixture_rows = [row for row in rows if row["source_quality"] == "fixture_real_shaped"]
    synthetic_rows = [row for row in rows if row["source_quality"] == "synthetic_stress"]
    real_cached_rows = [row for row in rows if row["source_quality"] == "real_cached"]
    primary_result = _evaluate_row_group(primary_rows)
    return {
        "schema_version": "pm_crypto_updown_real_cached_replay_eval_v1",
        "sequence": "39",
        "candidate_id": CANDIDATE_ID,
        "evaluation_status": (
            "READY_FOR_EXPANDED_SHADOW_REPLAY"
            if progress["row_gap"] == 0
            else "CANDIDATE_REMAINS_BLOCKED"
        ),
        "minimum_primary_replay_ready_rows": MIN_PRIMARY_REPLAY_READY_ROWS,
        "previous_primary_row_count": progress["previous_primary_row_count"],
        "primary_evidence_row_count": progress["current_primary_row_count"],
        "real_cached_replay_ready_row_count": progress["current_real_cached_row_count"],
        "row_gap": progress["row_gap"],
        "primary_result": primary_result,
        "real_cached_result": _evaluate_row_group(real_cached_rows),
        "fixture_diagnostic_result": _evaluate_row_group(fixture_rows),
        "synthetic_stress_result": _evaluate_row_group(synthetic_rows),
        "synthetic_rows_counted_as_primary": any(
            row["source_quality"] == "synthetic_stress" for row in primary_rows
        ),
        "readiness_blockers": progress["blockers"],
        "threshold_progress_report_path": progress.get("report_paths", {}).get("json"),
        "threshold_progress": progress,
        "network_fetch_attempted": False,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_pm_crypto_updown_real_cached_replay_eval_report(
    *,
    fixture_root: str | Path,
    output_root: str | Path = ".",
    real_cached_artifact_roots: list[str | Path] | None = None,
) -> dict[str, Any]:
    payload = evaluate_pm_crypto_updown_real_cached_replay(
        fixture_root=fixture_root,
        output_root=output_root,
        real_cached_artifact_roots=real_cached_artifact_roots,
    )
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_real_cached_replay_eval.json"
    md_path = root / "latest_real_cached_replay_eval.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 39 Real-Cached Replay Evaluation",
        "",
        "Replay evaluation split by primary, real-cached, fixture, and synthetic rows.",
        "",
        f"Status: {payload['evaluation_status']}",
        f"Primary rows: {payload['primary_evidence_row_count']}",
        f"Real-cached rows: {payload['real_cached_replay_ready_row_count']}",
        f"Row gap: {payload['row_gap']}",
        f"Synthetic rows counted as primary: {payload['synthetic_rows_counted_as_primary']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        "",
        "## Blockers",
    ]
    lines.extend(f"- {item}" for item in (payload["readiness_blockers"] or ["None"]))
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
