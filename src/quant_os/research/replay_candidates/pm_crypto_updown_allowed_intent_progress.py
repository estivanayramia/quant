from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from quant_os.execution.pm_crypto_updown_shadow_policy import (
    evaluate_pm_crypto_updown_shadow_policy,
)
from quant_os.research.replay_candidates.pm_crypto_updown_allowed_intent_diagnostics import (
    PRIMARY_SOURCE_QUALITIES,
    evaluate_pm_crypto_updown_allowed_intent_diagnostics,
)
from quant_os.research.replay_candidates.pm_crypto_updown_baseline_placebo_attribution import (
    evaluate_pm_crypto_updown_baseline_placebo_attribution,
)
from quant_os.research.replay_candidates.pm_crypto_updown_dataset_builder import (
    build_pm_crypto_updown_expanded_dataset,
)
from quant_os.research.replay_candidates.pm_crypto_updown_discriminators import (
    evaluate_pm_crypto_updown_discriminators,
)
from quant_os.research.replay_candidates.pm_crypto_updown_overfit_guard import (
    evaluate_pm_crypto_updown_overfit_guard,
)
from quant_os.research.replay_candidates.pm_crypto_updown_real_cached_import import (
    _load_valid_artifacts_from_roots,
    _normalize_artifacts,
)
from quant_os.research.replay_candidates.pm_crypto_updown_schema import CANDIDATE_ID
from quant_os.research.replay_candidates.pm_crypto_updown_signals import (
    is_replay_ready_row,
    score_pm_crypto_updown_signals,
)
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

PROGRESS_REPORT_ROOT = Path("reports/sequence45/allowed_intent_progress")
DISCRIMINATOR_REPORT_ROOT = Path("reports/sequence45/discriminators")
OVERFIT_REPORT_ROOT = Path("reports/sequence45/overfit_guard")
BASELINE_REPORT_ROOT = Path("reports/sequence45/baseline_placebo")


def summarize_pm_crypto_updown_allowed_intent_import_roots(
    *,
    real_cached_artifact_roots: list[str | Path] | None = None,
) -> dict[str, Any]:
    roots = list(real_cached_artifact_roots or [])
    artifacts, rejected, dedupe_dropped, root_summaries = _load_valid_artifacts_from_roots(
        roots,
    )
    normalized = _normalize_artifacts(
        artifacts,
        source_name="phase45_allowed_intent_import_roots",
    )
    rows = normalized["rows"]
    replay_ready = [row for row in rows if is_replay_ready_row(row)]
    real_cached_rows = [
        row
        for row in replay_ready
        if row.get("source_quality") == "real_cached"
        and row.get("label_status") == "RESOLVED"
        and row.get("resolved_outcome") is not None
    ]
    return {
        "schema_version": "pm_crypto_updown_allowed_intent_import_root_summary_v1",
        "sequence": "45",
        "candidate_id": CANDIDATE_ID,
        "import_root_count": len(roots),
        "import_roots": [str(Path(root)).replace("\\", "/") for root in roots],
        "root_summaries": root_summaries,
        "newly_imported_artifacts": len(artifacts),
        "rejected_artifact_count": len(rejected),
        "dedupe_dropped_artifact_count": dedupe_dropped,
        "rejected_by_reason": dict(sorted(Counter(item["reason"] for item in rejected).items())),
        "newly_imported_windows": len(
            {item.market_id for item in artifacts if item.artifact_type == "pm_market_window"}
        ),
        "newly_imported_rows": len(rows),
        "new_primary_rows": len(real_cached_rows),
        "new_real_cached_rows": len(real_cached_rows),
        "new_imported_row_ids": [row["clob_snapshot_id"] for row in rows],
        "local_files_only": True,
        "network_fetch_attempted": False,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def evaluate_pm_crypto_updown_allowed_intent_progress(
    *,
    previous_diagnostics: dict[str, Any] | None = None,
    rows: list[dict[str, Any]] | None = None,
    signal_report: dict[str, Any] | None = None,
    imported_row_ids: list[str] | None = None,
    fixture_root: str | Path | None = None,
    real_cached_artifact_roots: list[str | Path] | None = None,
) -> dict[str, Any]:
    import_summary = summarize_pm_crypto_updown_allowed_intent_import_roots(
        real_cached_artifact_roots=real_cached_artifact_roots,
    )
    if rows is None:
        dataset = build_pm_crypto_updown_expanded_dataset(
            fixture_root=fixture_root or Path("tests/fixtures/replay_candidates/pm_crypto_updown"),
            real_cached_artifact_roots=real_cached_artifact_roots,
        )
        rows = dataset["rows"]
    else:
        dataset = None
    signal_report = signal_report or score_pm_crypto_updown_signals(rows)
    previous_diagnostics = previous_diagnostics or evaluate_pm_crypto_updown_allowed_intent_diagnostics(
        fixture_root=fixture_root,
        real_cached_artifact_roots=None,
    )
    current = evaluate_pm_crypto_updown_allowed_intent_diagnostics(
        rows=rows,
        signal_report=signal_report,
        fixture_root=fixture_root,
        real_cached_artifact_roots=real_cached_artifact_roots,
    )
    imported_ids = set(imported_row_ids or import_summary["new_imported_row_ids"])
    imported_rows = [row for row in rows if str(row["clob_snapshot_id"]) in imported_ids]
    imported_primary_rows = [_primary_row(row) for row in imported_rows]
    imported_primary_rows = [row for row in imported_primary_rows if row is not None]
    imported_real_cached_rows = [
        row for row in imported_primary_rows if row.get("source_quality") == "real_cached"
    ]
    allowed_primary_ids = set(current["allowed_primary_row_ids"])
    allowed_real_cached_ids = set(current["allowed_real_cached_row_ids"])
    new_allowed_primary_ids = sorted(imported_ids & allowed_primary_ids)
    new_allowed_real_cached_ids = sorted(imported_ids & allowed_real_cached_ids)
    policy = evaluate_pm_crypto_updown_shadow_policy(
        rows=rows,
        signal_report=signal_report,
    )
    blocked_by_policy = [
        _policy_block_record(item)
        for item in policy["intents"]
        if str(item["row_id"]) in imported_ids and item["decision"] == "BLOCK_SHADOW_INTENT"
    ]
    attribution = evaluate_pm_crypto_updown_baseline_placebo_attribution(
        diagnostics=current,
    )
    discriminators = evaluate_pm_crypto_updown_discriminators(diagnostics=current)
    overfit = evaluate_pm_crypto_updown_overfit_guard(
        diagnostics=current,
        discriminator_report=discriminators,
    )
    return {
        "schema_version": "pm_crypto_updown_allowed_intent_progress_v1",
        "sequence": "45",
        "candidate_id": CANDIDATE_ID,
        "progress_status": _progress_status(current),
        "previous_allowed_primary_intents": previous_diagnostics[
            "allowed_primary_intent_count"
        ],
        "current_allowed_primary_intents": current["allowed_primary_intent_count"],
        "previous_allowed_real_cached_intents": previous_diagnostics[
            "allowed_real_cached_intent_count"
        ],
        "current_allowed_real_cached_intents": current["allowed_real_cached_intent_count"],
        "allowed_primary_intent_delta": current["allowed_primary_intent_count"]
        - previous_diagnostics["allowed_primary_intent_count"],
        "allowed_real_cached_intent_delta": current["allowed_real_cached_intent_count"]
        - previous_diagnostics["allowed_real_cached_intent_count"],
        "newly_imported_artifacts": import_summary["newly_imported_artifacts"],
        "newly_imported_windows": import_summary["newly_imported_windows"],
        "newly_imported_rows": len(imported_rows),
        "new_primary_rows": len(imported_primary_rows),
        "new_real_cached_rows": len(imported_real_cached_rows),
        "new_allowed_primary_intents": len(new_allowed_primary_ids),
        "new_allowed_real_cached_intents": len(new_allowed_real_cached_ids),
        "new_allowed_primary_row_ids": new_allowed_primary_ids,
        "new_allowed_real_cached_row_ids": new_allowed_real_cached_ids,
        "rejected_candidate_rows_with_reasons": _rejected_candidate_rows(imported_rows),
        "rows_blocked_by_policy": blocked_by_policy,
        "rows_failing_baseline_placebo_or_overfit_guard": _gate_blockers(
            attribution=attribution,
            overfit=overfit,
        ),
        "source_quality_separation": _source_quality_separation(rows),
        "real_cached_import_summary": import_summary,
        "diagnostics": current,
        "baseline_placebo_attribution": attribution,
        "anti_overfit_guard": overfit,
        "dataset_report": dataset,
        "synthetic_rows_counted_as_primary": False,
        "network_fetch_attempted": False,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_pm_crypto_updown_allowed_intent_progress_report(
    *,
    previous_diagnostics: dict[str, Any] | None = None,
    rows: list[dict[str, Any]] | None = None,
    signal_report: dict[str, Any] | None = None,
    imported_row_ids: list[str] | None = None,
    fixture_root: str | Path | None = None,
    real_cached_artifact_roots: list[str | Path] | None = None,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    payload = evaluate_pm_crypto_updown_allowed_intent_progress(
        previous_diagnostics=previous_diagnostics,
        rows=rows,
        signal_report=signal_report,
        imported_row_ids=imported_row_ids,
        fixture_root=fixture_root,
        real_cached_artifact_roots=real_cached_artifact_roots,
    )
    payload["report_paths"] = _write_progress_report(payload, output_root=output_root)
    return payload


def write_pm_crypto_updown_discriminator_update_report(
    *,
    fixture_root: str | Path | None = None,
    real_cached_artifact_roots: list[str | Path] | None = None,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    diagnostics = evaluate_pm_crypto_updown_allowed_intent_diagnostics(
        fixture_root=fixture_root,
        real_cached_artifact_roots=real_cached_artifact_roots,
    )
    payload = evaluate_pm_crypto_updown_discriminators(diagnostics=diagnostics)
    payload = {
        **payload,
        "sequence": "45",
        "update_status": "DISCRIMINATORS_EVALUATED",
        "diagnostics_allowed_primary_intent_count": diagnostics[
            "allowed_primary_intent_count"
        ],
    }
    payload["report_paths"] = _write_json_only(
        payload,
        output_root=output_root,
        report_root=DISCRIMINATOR_REPORT_ROOT,
        filename="latest_discriminator_update.json",
    )
    return payload


def write_pm_crypto_updown_overfit_guard_update_report(
    *,
    fixture_root: str | Path | None = None,
    real_cached_artifact_roots: list[str | Path] | None = None,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    diagnostics = evaluate_pm_crypto_updown_allowed_intent_diagnostics(
        fixture_root=fixture_root,
        real_cached_artifact_roots=real_cached_artifact_roots,
    )
    discriminators = evaluate_pm_crypto_updown_discriminators(diagnostics=diagnostics)
    payload = evaluate_pm_crypto_updown_overfit_guard(
        diagnostics=diagnostics,
        discriminator_report=discriminators,
    )
    payload = {
        **payload,
        "sequence": "45",
        "update_status": payload["status"],
        "discriminator_update": discriminators,
    }
    payload["report_paths"] = _write_json_only(
        payload,
        output_root=output_root,
        report_root=OVERFIT_REPORT_ROOT,
        filename="latest_overfit_guard_update.json",
    )
    return payload


def write_pm_crypto_updown_baseline_placebo_update_report(
    *,
    fixture_root: str | Path | None = None,
    real_cached_artifact_roots: list[str | Path] | None = None,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    diagnostics = evaluate_pm_crypto_updown_allowed_intent_diagnostics(
        fixture_root=fixture_root,
        real_cached_artifact_roots=real_cached_artifact_roots,
    )
    payload = evaluate_pm_crypto_updown_baseline_placebo_attribution(
        diagnostics=diagnostics,
    )
    payload = {
        **payload,
        "sequence": "45",
        "update_status": payload["active_blocker"],
        "allowed_primary_intent_count": diagnostics["allowed_primary_intent_count"],
        "allowed_real_cached_intent_count": diagnostics["allowed_real_cached_intent_count"],
        "more_allowed_intents_required": diagnostics["allowed_primary_intent_count"] < 5,
    }
    payload["report_paths"] = _write_baseline_report(payload, output_root=output_root)
    return payload


def _primary_row(row: dict[str, Any]) -> dict[str, Any] | None:
    if (
        row.get("source_quality") in PRIMARY_SOURCE_QUALITIES
        and is_replay_ready_row(row)
        and row.get("label_status") == "RESOLVED"
        and row.get("resolved_outcome") is not None
    ):
        return row
    return None


def _policy_block_record(intent: dict[str, Any]) -> dict[str, Any]:
    return {
        "row_id": intent["row_id"],
        "source_quality": intent.get("source_quality"),
        "blocker_reason": intent["blocker_reason"],
        "blocker_reasons": intent["blocker_reasons"],
    }


def _rejected_candidate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rejected = []
    for row in rows:
        reasons = []
        if row.get("source_quality") not in PRIMARY_SOURCE_QUALITIES:
            reasons.append("NON_PRIMARY_SOURCE_QUALITY")
        if not is_replay_ready_row(row):
            reasons.append("ROW_NOT_REPLAY_READY")
        if row.get("label_status") != "RESOLVED" or row.get("resolved_outcome") is None:
            reasons.append("UNRESOLVED_LABEL")
        if reasons:
            rejected.append(
                {
                    "row_id": row["clob_snapshot_id"],
                    "source_quality": row.get("source_quality"),
                    "reasons": reasons,
                }
            )
    return rejected


def _gate_blockers(*, attribution: dict[str, Any], overfit: dict[str, Any]) -> list[dict[str, Any]]:
    blockers = []
    if attribution["active_blocker"] == "BASELINE_OR_PLACEBO_BLOCKED":
        blockers.append(
            {
                "gate": "baseline_placebo",
                "blockers": attribution.get("baselines_beating_or_tying_candidate", [])
                + attribution.get("placebos_beating_or_tying_candidate", []),
            }
        )
    if not overfit["passes"]:
        blockers.append({"gate": "anti_overfit", "blockers": overfit["blockers"]})
    return blockers


def _source_quality_separation(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(row.get("source_quality", "unknown") for row in rows)
    primary = sum(counts.get(quality, 0) for quality in PRIMARY_SOURCE_QUALITIES)
    return {
        "source_quality_counts": dict(sorted(counts.items())),
        "primary_source_qualities": sorted(PRIMARY_SOURCE_QUALITIES),
        "primary_rows": primary,
        "synthetic_rows": counts.get("synthetic_stress", 0),
        "synthetic_counted_as_primary": False,
    }


def _progress_status(diagnostics: dict[str, Any]) -> str:
    if diagnostics["allowed_primary_intent_count"] < 5:
        return "NEEDS_MORE_ALLOWED_INTENTS"
    if diagnostics["allowed_real_cached_intent_count"] < 3:
        return "NEEDS_MORE_REAL_CACHED_EVIDENCE"
    return "ALLOWED_INTENT_THRESHOLD_REACHED"


def _write_progress_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / PROGRESS_REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_allowed_intent_progress.json"
    md_path = root / "latest_allowed_intent_progress.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 45 Allowed Intent Progress",
        "",
        "Reports whether imported real-cached rows became allowed primary intents.",
        "",
        f"Status: {payload['progress_status']}",
        f"New allowed primary intents: {payload['new_allowed_primary_intents']}",
        f"New allowed real-cached intents: {payload['new_allowed_real_cached_intents']}",
        f"Current allowed primary intents: {payload['current_allowed_primary_intents']}",
        f"Current allowed real-cached intents: {payload['current_allowed_real_cached_intents']}",
        f"Synthetic rows counted as primary: {payload['synthetic_rows_counted_as_primary']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        "",
        "## Policy Blocked Imported Rows",
    ]
    if payload["rows_blocked_by_policy"]:
        lines.extend(
            "- {row_id}: {reason}".format(
                row_id=item["row_id"],
                reason=",".join(item["blocker_reasons"]),
            )
            for item in payload["rows_blocked_by_policy"]
        )
    else:
        lines.append("- None")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def _write_json_only(
    payload: dict[str, Any],
    *,
    output_root: str | Path,
    report_root: Path,
    filename: str,
) -> dict[str, str]:
    root = Path(output_root) / report_root
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / filename
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return {"json": str(json_path)}


def _write_baseline_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / BASELINE_REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_baseline_placebo_update.json"
    md_path = root / "latest_baseline_placebo_update.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 45 Baseline/Placebo Update",
        "",
        "Re-runs baseline and placebo attribution on updated allowed primary intents.",
        "",
        f"Status: {payload['active_blocker']}",
        f"Candidate beats market baseline: {payload['candidate_beats_market_baseline']}",
        f"Candidate beats no-skill baseline: {payload['candidate_beats_no_skill_baseline']}",
        f"Candidate separates from placebos: {payload['candidate_beats_or_separates_from_placebos']}",
        f"More allowed intents required: {payload['more_allowed_intents_required']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
