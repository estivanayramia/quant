from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

from quant_os.research.replay_candidates.pm_crypto_updown_dataset_builder import (
    MIN_PRIMARY_REPLAY_READY_ROWS,
    build_pm_crypto_updown_expanded_dataset,
)
from quant_os.research.replay_candidates.pm_crypto_updown_schema import CANDIDATE_ID
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

REPORT_ROOT = Path("reports/sequence39/threshold_progress")


def evaluate_pm_crypto_updown_threshold_progress(
    *,
    fixture_root: str | Path,
    real_cached_artifact_roots: list[str | Path] | None = None,
) -> dict[str, Any]:
    dataset = build_pm_crypto_updown_expanded_dataset(
        fixture_root=fixture_root,
        real_cached_artifact_roots=real_cached_artifact_roots,
    )
    previous_primary = dataset["phase38_primary_evidence_row_count"]
    current_primary = dataset["primary_evidence_row_count"]
    real_cached_rows = dataset["real_cached_replay_ready_row_count"]
    row_gap = max(MIN_PRIMARY_REPLAY_READY_ROWS - current_primary, 0)
    source_coverage = _source_coverage(dataset, row_gap=row_gap)
    blockers = _blockers(dataset, row_gap=row_gap, source_coverage=source_coverage)
    return {
        "schema_version": "pm_crypto_updown_threshold_progress_v1",
        "sequence": "39",
        "candidate_id": CANDIDATE_ID,
        "previous_primary_row_count": previous_primary,
        "current_primary_row_count": current_primary,
        "current_real_cached_row_count": real_cached_rows,
        "target_primary_row_count": MIN_PRIMARY_REPLAY_READY_ROWS,
        "row_gap": row_gap,
        "primary_rows_moved_toward_20": current_primary > previous_primary,
        "threshold_status": _threshold_status(previous_primary, current_primary),
        "readiness_status": (
            "READY_FOR_EXPANDED_SHADOW_REPLAY"
            if row_gap == 0
            else "PRIMARY_EVIDENCE_STILL_TOO_THIN"
        ),
        "added_rows_by_source_mode": _added_rows_by_source_mode(dataset),
        "rejected_rows_by_reason": _rejected_rows_by_reason(dataset),
        "source_bottleneck": _source_bottleneck(dataset, row_gap=row_gap),
        "source_coverage": source_coverage,
        "next_operator_action": _next_operator_action(
            dataset,
            row_gap=row_gap,
            source_coverage=source_coverage,
        ),
        "phase40_can_run_expanded_shadow_replay": row_gap == 0,
        "blockers": blockers,
        "dataset_report": dataset,
        "network_fetch_attempted": False,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_pm_crypto_updown_threshold_progress_report(
    *,
    fixture_root: str | Path,
    output_root: str | Path = ".",
    real_cached_artifact_roots: list[str | Path] | None = None,
) -> dict[str, Any]:
    payload = evaluate_pm_crypto_updown_threshold_progress(
        fixture_root=fixture_root,
        real_cached_artifact_roots=real_cached_artifact_roots,
    )
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _threshold_status(previous_primary: int, current_primary: int) -> str:
    if current_primary >= MIN_PRIMARY_REPLAY_READY_ROWS:
        return "READY_FOR_EXPANDED_SHADOW_REPLAY"
    if current_primary > previous_primary:
        return "PRIMARY_EVIDENCE_EXPANDED"
    return "PRIMARY_EVIDENCE_STILL_TOO_THIN"


def _blockers(
    dataset: dict[str, Any],
    *,
    row_gap: int,
    source_coverage: dict[str, Any],
) -> list[str]:
    blockers = []
    flags = Counter(
        flag for row in dataset["rows"] for flag in row.get("data_quality_flags", [])
    )
    if flags.get("MISSING_CLOB_SNAPSHOT"):
        blockers.append("BLOCKED_MISSING_CLOB_COVERAGE")
    if flags.get("MISSING_SPOT_SNAPSHOT"):
        blockers.append("BLOCKED_MISSING_SPOT_COVERAGE")
    if flags.get("MISSING_WINDOW_LABELS") or flags.get("LABEL_UNRESOLVED"):
        blockers.append("BLOCKED_MISSING_LABEL_COVERAGE")
    if row_gap:
        blockers.append(
            f"PRIMARY_ROWS_{dataset['primary_evidence_row_count']}_LT_"
            f"{MIN_PRIMARY_REPLAY_READY_ROWS}"
        )
    if source_coverage["coverage_status"] != "REAL_CACHED_SOURCE_COVERAGE_SUFFICIENT":
        blockers.append(
            "SOURCE_COVERAGE_REAL_CACHED_ROWS_"
            f"{source_coverage['real_cached_replay_ready_row_count']}_LT_REQUIRED_"
            f"{source_coverage['required_real_cached_replay_ready_rows']}"
        )
    return blockers


def _added_rows_by_source_mode(dataset: dict[str, Any]) -> dict[str, int]:
    counts = Counter()
    for row in dataset["real_cached_rows"]:
        for mode in row.get("source_capture_modes") or ["real_cached_unknown"]:
            counts[mode] += 1
    return dict(sorted(counts.items()))


def _rejected_rows_by_reason(dataset: dict[str, Any]) -> dict[str, int]:
    counts = Counter()
    for source in dataset["real_cached_imports"]:
        for reason, count in source.get("rejected_by_reason", {}).items():
            counts[reason] += count
    return dict(sorted(counts.items()))


def _source_bottleneck(dataset: dict[str, Any], *, row_gap: int) -> str:
    rows = dataset["real_cached_rows"] or dataset["rows"]
    flags = Counter(
        flag for row in rows for flag in row.get("data_quality_flags", [])
    )
    if flags.get("MISSING_CLOB_SNAPSHOT"):
        return "CLOB/orderbook"
    if flags.get("MISSING_SPOT_SNAPSHOT"):
        return "spot"
    if flags.get("MISSING_WINDOW_LABELS") or flags.get("LABEL_UNRESOLVED"):
        return "labels/window metadata"
    if flags.get("WIDE_SPREAD") or flags.get("LOW_LIQUIDITY"):
        return "liquidity/spread"
    if row_gap:
        return "real_cached_rows"
    return "none"


def _source_coverage(dataset: dict[str, Any], *, row_gap: int) -> dict[str, Any]:
    roots = [_source_root_coverage(source) for source in dataset["real_cached_imports"]]
    accepted_artifacts = sum(root["accepted_artifact_count"] for root in roots)
    real_cached_ready = dataset["real_cached_replay_ready_row_count"]
    fixture_primary = dataset["primary_evidence_row_count"] - real_cached_ready
    required_real_cached = max(MIN_PRIMARY_REPLAY_READY_ROWS - fixture_primary, 0)
    if row_gap == 0:
        status = "REAL_CACHED_SOURCE_COVERAGE_SUFFICIENT"
    elif real_cached_ready == 0:
        status = "REAL_CACHED_SOURCE_COVERAGE_MISSING"
    else:
        status = "REAL_CACHED_SOURCE_COVERAGE_INCOMPLETE"
    return {
        "coverage_status": status,
        "accepted_artifact_count": accepted_artifacts,
        "real_cached_replay_ready_row_count": real_cached_ready,
        "fixture_primary_row_count": fixture_primary,
        "required_real_cached_replay_ready_rows": required_real_cached,
        "additional_primary_rows_needed": row_gap,
        "additional_two_token_windows_needed_estimate": math.ceil(row_gap / 2),
        "real_cached_roots": roots,
    }


def _source_root_coverage(source: dict[str, Any]) -> dict[str, Any]:
    missing = _missing_replay_artifact_types(source)
    if source["real_cached_replay_ready_row_count"] > 0:
        status = "REPLAY_READY_ROWS_AVAILABLE"
    elif source["accepted_artifact_count"] > 0:
        status = "INCOMPLETE_REPLAY_ARTIFACT_COVERAGE"
    else:
        status = "NO_REPLAY_ARTIFACTS_FOUND"
    return {
        "source_name": source["source_name"],
        "import_root": source["import_root"],
        "coverage_status": status,
        "accepted_artifact_count": source["accepted_artifact_count"],
        "rejected_artifact_count": source["rejected_artifact_count"],
        "rejected_by_reason": source.get("rejected_by_reason", {}),
        "real_cached_replay_ready_row_count": source["real_cached_replay_ready_row_count"],
        "market_window_count": source["market_window_count"],
        "clob_snapshot_count": source["clob_snapshot_count"],
        "spot_snapshot_count": source["spot_snapshot_count"],
        "window_label_count": source["window_label_count"],
        "missing_replay_artifact_types": missing,
    }


def _missing_replay_artifact_types(source: dict[str, Any]) -> list[str]:
    missing = []
    if source["clob_snapshot_count"] <= 0:
        missing.append("pm_clob_snapshot")
    if source["market_window_count"] <= 0:
        missing.append("pm_market_window")
    if source["window_label_count"] <= 0:
        missing.append("pm_window_label_or_pm_resolution_label")
    if source["spot_snapshot_count"] <= 0:
        missing.append("spot_snapshot_or_spot_candle")
    return missing


def _next_operator_action(
    dataset: dict[str, Any],
    *,
    row_gap: int,
    source_coverage: dict[str, Any],
) -> str:
    if row_gap == 0:
        return "Run python -m quant_os.cli readiness real-cached-replay-readiness and then expanded shadow replay."
    return (
        "Run python -m quant_os.cli data pm-crypto-updown-capture-plan, then collect at least "
        f"{source_coverage['additional_primary_rows_needed']} additional primary "
        "replay-ready rows (about "
        f"{source_coverage['additional_two_token_windows_needed_estimate']} two-token "
        "UP/DOWN windows) with market window, CLOB snapshot, near-time spot snapshot, "
        "and resolved label artifacts; then run python -m quant_os.cli data "
        "pm-crypto-updown-real-cached-import --import-root <run_root>."
    )


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_threshold_progress.json"
    md_path = root / "latest_threshold_progress.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 39 Threshold Progress",
        "",
        "Evidence-gap report for pm_crypto_updown_repricing_lag.",
        "",
        f"Previous primary rows: {payload['previous_primary_row_count']}",
        f"Current primary rows: {payload['current_primary_row_count']}",
        f"Real-cached rows: {payload['current_real_cached_row_count']}",
        f"Target primary rows: {payload['target_primary_row_count']}",
        f"Row gap: {payload['row_gap']}",
        f"Readiness status: {payload['readiness_status']}",
        f"Source bottleneck: {payload['source_bottleneck']}",
        f"Source coverage: {payload['source_coverage']['coverage_status']}",
        f"Additional primary rows needed: {payload['source_coverage']['additional_primary_rows_needed']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        "",
        "## Next Operator Action",
        payload["next_operator_action"],
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
