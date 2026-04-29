from __future__ import annotations

import json
from typing import Any

import pandas as pd

from quant_os.data.dataset_splits import split_frame_ranges, walk_forward_ranges
from quant_os.data.historical_cache import NORMALIZED_LATEST, REPORT_ROOT, now_utc
from quant_os.data.historical_import import import_historical_csv
from quant_os.data.historical_manifest import build_historical_manifest
from quant_os.data.historical_quality import run_historical_quality
from quant_os.data.leakage_checks import ordered_before, ranges_overlap
from quant_os.projections.evidence_projection import rebuild_historical_evidence_projection
from quant_os.projections.historical_data_projection import rebuild_historical_data_projection


def build_historical_splits(write: bool = True) -> dict[str, Any]:
    if not NORMALIZED_LATEST.exists():
        import_historical_csv()
    manifest = build_historical_manifest()
    frame = pd.read_parquet(NORMALIZED_LATEST)
    items = []
    for (symbol, timeframe), group in frame.groupby(["symbol", "timeframe"]):
        data = group.sort_values("timestamp").reset_index(drop=True)
        items.append(
            {
                "symbol": str(symbol),
                "timeframe": str(timeframe),
                "rows": int(len(data)),
                "splits": split_frame_ranges(data, purge_gap_bars=1),
                "walk_forward": walk_forward_ranges(data, min_splits=3, purge_gap_bars=1),
            }
        )
    payload = {
        "generated_at": now_utc(),
        "status": "PASS" if items else "UNAVAILABLE",
        "dataset_id": manifest["dataset_id"],
        "items": items,
        "live_trading_enabled": False,
    }
    if write:
        _write_evidence_file("latest_splits", payload, "Historical Splits")
    return payload


def run_historical_leakage_check(
    write: bool = True, splits_payload: dict[str, Any] | None = None
) -> dict[str, Any]:
    splits = splits_payload or build_historical_splits(write=True)
    failures: list[str] = []
    warnings: list[str] = []
    for item in splits.get("items", []):
        ranges = item["splits"]
        if ranges_overlap(ranges["train"], ranges["validation"]):
            failures.append(f"TRAIN_VALIDATION_OVERLAP:{item['symbol']}:{item['timeframe']}")
        if ranges_overlap(ranges["validation"], ranges["test"]):
            failures.append(f"VALIDATION_TEST_OVERLAP:{item['symbol']}:{item['timeframe']}")
        if ranges_overlap(ranges["train"], ranges["test"]):
            failures.append(f"TRAIN_TEST_OVERLAP:{item['symbol']}:{item['timeframe']}")
        for window in item.get("walk_forward", []):
            if not ordered_before(window["train"], window["test"]):
                failures.append(f"WALK_FORWARD_ORDER:{item['symbol']}:{item['timeframe']}")
        if not item.get("walk_forward"):
            warnings.append(f"NO_WALK_FORWARD_WINDOWS:{item['symbol']}:{item['timeframe']}")
    payload = {
        "generated_at": now_utc(),
        "status": "FAIL" if failures else "WARN" if warnings else "PASS",
        "failures": failures,
        "warnings": warnings,
        "target_leakage": "NOT_APPLICABLE",
        "feature_leakage": "NO_TARGET_COLUMNS_PRESENT",
        "live_trading_enabled": False,
    }
    if write:
        _write_evidence_file("latest_leakage_check", payload, "Historical Leakage Check")
    return payload


def calculate_historical_evidence_score(write: bool = True) -> dict[str, Any]:
    manifest = build_historical_manifest()
    quality = run_historical_quality()
    splits = build_historical_splits()
    leakage = run_historical_leakage_check(splits_payload=splits)
    symbols = len(manifest["symbols"])
    timeframes = len(manifest["timeframes"])
    row_score = min(float(manifest["rows"]) / 500.0, 1.0)
    symbol_score = min(symbols / 3.0, 1.0)
    timeframe_score = min(timeframes / 2.0, 1.0)
    wf_counts = [len(item.get("walk_forward", [])) for item in splits.get("items", [])]
    walk_forward_score = min((min(wf_counts) if wf_counts else 0) / 3.0, 1.0)
    quality_score = 1.0 if quality["status"] == "PASS" else 0.6 if quality["status"] == "WARN" else 0.0
    leakage_score = 1.0 if leakage["status"] == "PASS" else 0.6 if leakage["status"] == "WARN" else 0.0
    manifest_score = 1.0 if manifest.get("raw_sha256") and manifest.get("normalized_sha256") else 0.0
    blockers = []
    if quality["status"] == "FAIL":
        blockers.append("HISTORICAL_QUALITY_FAILED")
    if leakage["status"] == "FAIL":
        blockers.append("HISTORICAL_LEAKAGE_FAILED")
    if not manifest.get("license_note"):
        blockers.append("LICENSE_NOTE_MISSING")
    raw_score = (
        quality_score
        + leakage_score
        + manifest_score
        + row_score
        + symbol_score
        + timeframe_score
        + walk_forward_score
    ) / 7.0
    status = _historical_status(raw_score, blockers)
    payload = {
        "generated_at": now_utc(),
        "source_credibility_metadata": {
            "source_type": manifest["source_type"],
            "source_name": manifest["source_name"],
            "license_note_present": bool(manifest.get("license_note")),
        },
        "manifest_completeness": manifest_score,
        "quality_status": quality["status"],
        "row_coverage_score": row_score,
        "symbol_coverage_score": symbol_score,
        "timeframe_coverage_score": timeframe_score,
        "split_status": splits["status"],
        "leakage_status": leakage["status"],
        "out_of_sample_available": splits["status"] == "PASS",
        "walk_forward_score": walk_forward_score,
        "strategy_research_compatibility": quality["status"] in {"PASS", "WARN"}
        and leakage["status"] in {"PASS", "WARN"},
        "overfit_penalty": 0.15 if manifest["rows"] < 500 else 0.0,
        "raw_score": raw_score,
        "final_evidence_status": status,
        "live_promotion_status": "LIVE_BLOCKED",
        "live_ready": False,
        "blockers": blockers + ["LIVE_PROMOTION_DISABLED"],
        "warnings": quality.get("warnings", []) + leakage.get("warnings", []),
    }
    if write:
        _write_historical_evidence_score(payload)
        rebuild_historical_data_projection()
        rebuild_historical_evidence_projection(payload)
    return payload


def _historical_status(score: float, blockers: list[str]) -> str:
    if blockers:
        return "HISTORICAL_INSUFFICIENT"
    if score >= 0.85:
        return "HISTORICAL_DRY_RUN_READY"
    if score >= 0.72:
        return "HISTORICAL_SHADOW_READY"
    if score >= 0.55:
        return "HISTORICAL_RESEARCH_READY"
    if score >= 0.35:
        return "HISTORICAL_WEAK"
    return "HISTORICAL_INSUFFICIENT"


def _write_evidence_file(stem: str, payload: dict[str, Any], title: str) -> None:
    root = REPORT_ROOT / "evidence"
    root.mkdir(parents=True, exist_ok=True)
    (root / f"{stem}.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8"
    )
    lines = [
        f"# {title}",
        "",
        "Historical data evidence metadata. No live trading.",
        "",
        f"Status: {payload['status']}",
    ]
    (root / f"{stem}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_historical_evidence_score(payload: dict[str, Any]) -> None:
    root = REPORT_ROOT / "evidence"
    root.mkdir(parents=True, exist_ok=True)
    (root / "latest_historical_evidence_score.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8"
    )
    lines = [
        "# Historical Evidence Score",
        "",
        "Historical evidence scoring. Live promotion is blocked.",
        "",
        f"Evidence status: {payload['final_evidence_status']}",
        f"Live promotion: {payload['live_promotion_status']}",
        f"Raw score: {payload['raw_score']:.3f}",
        "",
        "## Blockers",
    ]
    lines.extend(f"- {blocker}" for blocker in payload["blockers"])
    lines.extend(["", "## Warnings"])
    lines.extend(f"- {warning}" for warning in (payload["warnings"] or ["None"]))
    (root / "latest_historical_evidence_score.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
