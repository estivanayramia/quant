from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.research.replay_candidates.pm_crypto_updown_allowed_intent_diagnostics import (
    evaluate_pm_crypto_updown_allowed_intent_diagnostics,
)
from quant_os.research.replay_candidates.pm_crypto_updown_allowed_intent_progress import (
    evaluate_pm_crypto_updown_allowed_intent_progress,
    summarize_pm_crypto_updown_allowed_intent_import_roots,
)
from quant_os.research.replay_candidates.pm_crypto_updown_baseline_placebo_attribution import (
    evaluate_pm_crypto_updown_baseline_placebo_attribution,
)
from quant_os.research.replay_candidates.pm_crypto_updown_discriminators import (
    evaluate_pm_crypto_updown_discriminators,
)
from quant_os.research.replay_candidates.pm_crypto_updown_overfit_guard import (
    evaluate_pm_crypto_updown_overfit_guard,
)
from quant_os.research.replay_candidates.pm_crypto_updown_policy_replay_eval import (
    MIN_ALLOWED_SHADOW_INTENTS,
)
from quant_os.research.replay_candidates.pm_crypto_updown_schema import CANDIDATE_ID
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

CAPTURE_REPORT_ROOT = Path("reports/sequence46/allowed_intent_capture")
PROGRESS_REPORT_ROOT = Path("reports/sequence46/allowed_intent_progress")
BASELINE_REPORT_ROOT = Path("reports/sequence46/baseline_placebo")
OVERFIT_REPORT_ROOT = Path("reports/sequence46/overfit_guard")
DISCRIMINATOR_REPORT_ROOT = Path("reports/sequence46/discriminators")
DEFAULT_CAPTURE_ROOT = Path("data/external/manual_captures/pm_crypto_updown")
DEFAULT_FIXTURE_ROOT = Path("tests/fixtures/replay_candidates/pm_crypto_updown")
TARGET_ALLOWED_REAL_CACHED_INTENTS = 3


def evaluate_pm_crypto_updown_allowed_intent_capture_pass(
    *,
    run_id: str = "pm_crypto_updown_manual_046",
    capture_run_root: str | Path | None = None,
    baseline_real_cached_artifact_roots: list[str | Path] | None = None,
    previous_diagnostics: dict[str, Any] | None = None,
    rows: list[dict[str, Any]] | None = None,
    signal_report: dict[str, Any] | None = None,
    imported_row_ids: list[str] | None = None,
    fixture_root: str | Path | None = None,
    progress_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    run_root = Path(capture_run_root) if capture_run_root is not None else DEFAULT_CAPTURE_ROOT / run_id
    baseline_roots = list(baseline_real_cached_artifact_roots or [])
    all_roots = baseline_roots + [run_root]
    capture_summary = summarize_pm_crypto_updown_allowed_intent_import_roots(
        real_cached_artifact_roots=[run_root],
    )
    if progress_payload is None:
        previous_diagnostics = previous_diagnostics or evaluate_pm_crypto_updown_allowed_intent_diagnostics(
            fixture_root=fixture_root or DEFAULT_FIXTURE_ROOT,
            real_cached_artifact_roots=baseline_roots,
        )
        progress_payload = evaluate_pm_crypto_updown_allowed_intent_progress(
            previous_diagnostics=previous_diagnostics,
            rows=rows,
            signal_report=signal_report,
            imported_row_ids=imported_row_ids or capture_summary["new_imported_row_ids"],
            fixture_root=fixture_root or DEFAULT_FIXTURE_ROOT,
            real_cached_artifact_roots=all_roots if rows is None else None,
        )
    before_primary = int(progress_payload["previous_allowed_primary_intents"])
    before_real_cached = int(progress_payload["previous_allowed_real_cached_intents"])
    after_primary = int(progress_payload["current_allowed_primary_intents"])
    after_real_cached = int(progress_payload["current_allowed_real_cached_intents"])
    if rows is not None and imported_row_ids is not None:
        after_primary = before_primary + int(progress_payload["new_allowed_primary_intents"])
        after_real_cached = before_real_cached + int(
            progress_payload["new_allowed_real_cached_intents"]
        )
    threshold_passed = (
        after_primary >= MIN_ALLOWED_SHADOW_INTENTS
        and after_real_cached >= TARGET_ALLOWED_REAL_CACHED_INTENTS
    )
    manifest_exists = (run_root / "manifest.json").exists()
    artifacts_accepted = int(capture_summary["newly_imported_artifacts"])
    artifacts_rejected = int(capture_summary["rejected_artifact_count"])
    rows_imported = int(capture_summary["newly_imported_rows"])
    windows_imported = int(capture_summary["newly_imported_windows"])
    source_coverage_missing = (
        not threshold_passed
        or artifacts_accepted == 0
        or windows_imported == 0
        or rows_imported == 0
    )
    blocker_before = _blocker_from_counts(before_primary, before_real_cached)
    blocker_after = _blocker_from_counts(after_primary, after_real_cached)
    exact_next_command = _exact_next_import_command(
        baseline_roots=baseline_roots,
        run_root=run_root,
    )
    return {
        "schema_version": "pm_crypto_updown_allowed_intent_capture_pass_v1",
        "sequence": "46",
        "candidate_id": CANDIDATE_ID,
        "run_id": run_id,
        "capture_attempted": bool(manifest_exists or artifacts_accepted or progress_payload),
        "network_attempted": False,
        "auth_used": False,
        "wallet_used": False,
        "order_endpoints_used": False,
        "order_placement_allowed": False,
        "order_cancellation_allowed": False,
        "capture_run_root": str(run_root).replace("\\", "/"),
        "baseline_real_cached_artifact_roots": [
            str(Path(root)).replace("\\", "/") for root in baseline_roots
        ],
        "artifacts_accepted": artifacts_accepted,
        "artifacts_rejected": artifacts_rejected,
        "capture_root_summaries": capture_summary["root_summaries"],
        "windows_captured_or_imported": windows_imported,
        "rows_imported": rows_imported,
        "allowed_primary_intents_before": before_primary,
        "allowed_primary_intents_after": after_primary,
        "allowed_primary_intent_delta": after_primary - before_primary,
        "allowed_real_cached_intents_before": before_real_cached,
        "allowed_real_cached_intents_after": after_real_cached,
        "allowed_real_cached_intent_delta": after_real_cached - before_real_cached,
        "new_allowed_primary_intents": int(progress_payload["new_allowed_primary_intents"]),
        "new_allowed_real_cached_intents": int(
            progress_payload["new_allowed_real_cached_intents"]
        ),
        "new_allowed_primary_row_ids": progress_payload.get("new_allowed_primary_row_ids", []),
        "new_allowed_real_cached_row_ids": progress_payload.get(
            "new_allowed_real_cached_row_ids",
            [],
        ),
        "blocker_before": blocker_before,
        "blocker_after": blocker_after,
        "allowed_intent_threshold_passed": threshold_passed,
        "source_coverage_still_missing": source_coverage_missing,
        "exact_next_command_if_still_blocked": "" if threshold_passed else exact_next_command,
        "missing_coverage": _missing_coverage(after_primary, after_real_cached),
        "progress": progress_payload,
        "capture_import_summary": capture_summary,
        "synthetic_rows_counted_as_primary": bool(
            progress_payload.get("synthetic_rows_counted_as_primary", False)
        ),
        "source_quality_separation": progress_payload.get("source_quality_separation", {}),
        "network_fetch_attempted": False,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_pm_crypto_updown_allowed_intent_capture_pass_report(
    *,
    run_id: str = "pm_crypto_updown_manual_046",
    capture_run_root: str | Path | None = None,
    baseline_real_cached_artifact_roots: list[str | Path] | None = None,
    previous_diagnostics: dict[str, Any] | None = None,
    rows: list[dict[str, Any]] | None = None,
    signal_report: dict[str, Any] | None = None,
    imported_row_ids: list[str] | None = None,
    fixture_root: str | Path | None = None,
    progress_payload: dict[str, Any] | None = None,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    payload = evaluate_pm_crypto_updown_allowed_intent_capture_pass(
        run_id=run_id,
        capture_run_root=capture_run_root,
        baseline_real_cached_artifact_roots=baseline_real_cached_artifact_roots,
        previous_diagnostics=previous_diagnostics,
        rows=rows,
        signal_report=signal_report,
        imported_row_ids=imported_row_ids,
        fixture_root=fixture_root,
        progress_payload=progress_payload,
    )
    payload["report_paths"] = _write_capture_report(payload, output_root=output_root)
    return payload


def write_pm_crypto_updown_phase46_allowed_intent_progress_report(
    *,
    fixture_root: str | Path | None = None,
    real_cached_artifact_roots: list[str | Path] | None = None,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    payload = evaluate_pm_crypto_updown_allowed_intent_progress(
        fixture_root=fixture_root or DEFAULT_FIXTURE_ROOT,
        real_cached_artifact_roots=real_cached_artifact_roots,
    )
    payload = {**payload, "sequence": "46"}
    payload["report_paths"] = _write_progress_report(payload, output_root=output_root)
    return payload


def write_pm_crypto_updown_phase46_discriminator_update_report(
    *,
    fixture_root: str | Path | None = None,
    real_cached_artifact_roots: list[str | Path] | None = None,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    diagnostics = evaluate_pm_crypto_updown_allowed_intent_diagnostics(
        fixture_root=fixture_root or DEFAULT_FIXTURE_ROOT,
        real_cached_artifact_roots=real_cached_artifact_roots,
    )
    payload = evaluate_pm_crypto_updown_discriminators(diagnostics=diagnostics)
    payload = {
        **payload,
        "sequence": "46",
        "update_status": "DISCRIMINATORS_EVALUATED",
    }
    payload["report_paths"] = _write_json_only(
        payload,
        output_root=output_root,
        report_root=DISCRIMINATOR_REPORT_ROOT,
        filename="latest_discriminator_update.json",
    )
    return payload


def write_pm_crypto_updown_phase46_overfit_guard_update_report(
    *,
    fixture_root: str | Path | None = None,
    real_cached_artifact_roots: list[str | Path] | None = None,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    diagnostics = evaluate_pm_crypto_updown_allowed_intent_diagnostics(
        fixture_root=fixture_root or DEFAULT_FIXTURE_ROOT,
        real_cached_artifact_roots=real_cached_artifact_roots,
    )
    discriminators = evaluate_pm_crypto_updown_discriminators(diagnostics=diagnostics)
    payload = evaluate_pm_crypto_updown_overfit_guard(
        diagnostics=diagnostics,
        discriminator_report=discriminators,
    )
    payload = {
        **payload,
        "sequence": "46",
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


def write_pm_crypto_updown_phase46_baseline_placebo_update_report(
    *,
    fixture_root: str | Path | None = None,
    real_cached_artifact_roots: list[str | Path] | None = None,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    diagnostics = evaluate_pm_crypto_updown_allowed_intent_diagnostics(
        fixture_root=fixture_root or DEFAULT_FIXTURE_ROOT,
        real_cached_artifact_roots=real_cached_artifact_roots,
    )
    payload = evaluate_pm_crypto_updown_baseline_placebo_attribution(diagnostics=diagnostics)
    payload = {
        **payload,
        "sequence": "46",
        "update_status": payload["active_blocker"],
        "allowed_primary_intent_count": diagnostics["allowed_primary_intent_count"],
        "allowed_real_cached_intent_count": diagnostics["allowed_real_cached_intent_count"],
    }
    payload["report_paths"] = _write_baseline_report(payload, output_root=output_root)
    return payload


def _blocker_from_counts(primary: int, real_cached: int) -> str:
    if primary < MIN_ALLOWED_SHADOW_INTENTS:
        return "NEEDS_MORE_ALLOWED_INTENTS"
    if real_cached < TARGET_ALLOWED_REAL_CACHED_INTENTS:
        return "NEEDS_MORE_ALLOWED_INTENTS"
    return "NONE"


def _missing_coverage(primary: int, real_cached: int) -> dict[str, Any]:
    return {
        "required_additional_allowed_primary_intents": max(
            MIN_ALLOWED_SHADOW_INTENTS - primary,
            0,
        ),
        "required_additional_allowed_real_cached_intents": max(
            TARGET_ALLOWED_REAL_CACHED_INTENTS - real_cached,
            0,
        ),
        "required_artifact_groups": [
            "pm_market_window",
            "pm_clob_snapshot",
            "spot_snapshot_or_candle",
            "pm_window_label_or_resolution_label",
        ],
    }


def _exact_next_import_command(
    *,
    baseline_roots: list[str | Path],
    run_root: Path,
) -> str:
    roots = [*baseline_roots, run_root]
    if not roots:
        roots = [run_root]
    parts = ["python -m quant_os.cli data pm-crypto-updown-real-cached-import"]
    parts.extend(f"--real-cached-root {str(Path(root))}" for root in roots)
    return " ".join(parts)


def _write_capture_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / CAPTURE_REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_allowed_intent_capture_pass.json"
    md_path = root / "latest_allowed_intent_capture_pass.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 46 Allowed Intent Capture Pass",
        "",
        "Read-only/manual capture and import pass for allowed-intent evidence.",
        "",
        f"Run ID: {payload['run_id']}",
        f"Capture attempted: {payload['capture_attempted']}",
        f"Network attempted: {payload['network_attempted']}",
        f"Artifacts accepted: {payload['artifacts_accepted']}",
        f"Rows imported: {payload['rows_imported']}",
        f"Allowed primary intents: {payload['allowed_primary_intents_before']} -> {payload['allowed_primary_intents_after']}",
        f"Allowed real-cached intents: {payload['allowed_real_cached_intents_before']} -> {payload['allowed_real_cached_intents_after']}",
        f"Blocker after: {payload['blocker_after']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        "",
        "## Exact Next Command",
        payload["exact_next_command_if_still_blocked"] or "None",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def _write_progress_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / PROGRESS_REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_allowed_intent_progress.json"
    md_path = root / "latest_allowed_intent_progress.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 46 Allowed Intent Progress",
        "",
        f"Status: {payload['progress_status']}",
        f"Current allowed primary intents: {payload['current_allowed_primary_intents']}",
        f"Current allowed real-cached intents: {payload['current_allowed_real_cached_intents']}",
        f"New allowed primary intents: {payload['new_allowed_primary_intents']}",
        f"New allowed real-cached intents: {payload['new_allowed_real_cached_intents']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def _write_baseline_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / BASELINE_REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_baseline_placebo_update.json"
    md_path = root / "latest_baseline_placebo_update.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 46 Baseline/Placebo Update",
        "",
        f"Status: {payload['active_blocker']}",
        f"Candidate beats market baseline: {payload['candidate_beats_market_baseline']}",
        f"Candidate beats no-skill baseline: {payload['candidate_beats_no_skill_baseline']}",
        f"Candidate separates from placebos: {payload['candidate_beats_or_separates_from_placebos']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
    ]
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
