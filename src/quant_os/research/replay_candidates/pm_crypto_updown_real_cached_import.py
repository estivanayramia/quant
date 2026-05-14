from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from quant_os.data.crypto_spot_snapshots import parse_utc, utc_string
from quant_os.research.replay_candidates.pm_crypto_updown_alignment import (
    align_pm_crypto_updown_rows,
)
from quant_os.research.replay_candidates.pm_crypto_updown_schema import CANDIDATE_ID
from quant_os.research.replay_candidates.pm_crypto_updown_signals import is_replay_ready_row
from quant_os.research.replay_candidates.real_cached_artifact_models import (
    CAPTURE_MODES,
    RealCachedArtifact,
)
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

REPORT_ROOT = Path("reports/sequence39/real_cached_import")


def build_pm_crypto_updown_real_cached_source(
    *,
    import_root: str | Path,
    source_name: str = "real_cached_import",
) -> dict[str, Any]:
    artifacts, rejected, dedupe_dropped = _load_valid_artifacts(import_root)
    normalized = _normalize_artifacts(artifacts, source_name=source_name)
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
        "source_name": source_name,
        "source_type": "real_cached_import",
        "source_quality": "real_cached",
        "import_root": str(Path(import_root)).replace("\\", "/"),
        "accepted_artifact_count": len(artifacts),
        "rejected_artifact_count": len(rejected),
        "dedupe_dropped_artifact_count": dedupe_dropped,
        "rejected_artifacts": rejected,
        "rejected_by_reason": dict(sorted(Counter(item["reason"] for item in rejected).items())),
        "source_mode_counts": dict(sorted(Counter(item.capture_mode for item in artifacts).items())),
        "artifact_type_counts": dict(sorted(Counter(item.artifact_type for item in artifacts).items())),
        "normalized_source": normalized,
        "rows": rows,
        "imported_replay_ready_row_count": len(replay_ready),
        "real_cached_replay_ready_row_count": len(real_cached_rows),
        "real_cached_primary_rows": real_cached_rows,
    }


def import_pm_crypto_updown_real_cached_artifacts(
    *,
    import_root: str | Path,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    source = build_pm_crypto_updown_real_cached_source(import_root=import_root)
    payload = {
        "schema_version": "pm_crypto_updown_real_cached_import_v1",
        "sequence": "39",
        "candidate_id": CANDIDATE_ID,
        "import_status": _import_status(source),
        "accepted_artifact_count": source["accepted_artifact_count"],
        "rejected_artifact_count": source["rejected_artifact_count"],
        "dedupe_dropped_artifact_count": source["dedupe_dropped_artifact_count"],
        "rejected_artifacts": source["rejected_artifacts"],
        "rejected_by_reason": source["rejected_by_reason"],
        "source_mode_counts": source["source_mode_counts"],
        "artifact_type_counts": source["artifact_type_counts"],
        "normalized_source": _summarize_normalized_source(source["normalized_source"]),
        "imported_replay_ready_row_count": source["imported_replay_ready_row_count"],
        "real_cached_replay_ready_row_count": source["real_cached_replay_ready_row_count"],
        "real_cached_rows_imported": source["real_cached_replay_ready_row_count"],
        "local_files_only": True,
        "network_fetch_attempted": False,
        "raw_unvalidated_artifacts_replay_ready": False,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _load_valid_artifacts(import_root: str | Path) -> tuple[list[RealCachedArtifact], list[dict[str, Any]], int]:
    accepted: list[RealCachedArtifact] = []
    rejected: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()
    seen_keys: set[tuple[str, str, str, str]] = set()
    dedupe_dropped = 0
    for index, raw in enumerate(_iter_raw_artifacts(import_root), start=1):
        reason = _precheck_reject_reason(raw)
        if reason is not None:
            rejected.append({"index": index, "reason": reason, "source_id": raw.get("source_id")})
            continue
        try:
            artifact = RealCachedArtifact.model_validate(raw)
        except ValidationError as exc:
            rejected.append(
                {
                    "index": index,
                    "reason": _validation_reject_reason(raw, exc),
                    "source_id": raw.get("source_id"),
                }
            )
            continue
        if artifact.normalized_hash in seen_hashes or artifact.artifact_key in seen_keys:
            dedupe_dropped += 1
            continue
        seen_hashes.add(artifact.normalized_hash)
        seen_keys.add(artifact.artifact_key)
        accepted.append(artifact)
    return accepted, rejected, dedupe_dropped


def _iter_raw_artifacts(import_root: str | Path) -> list[dict[str, Any]]:
    root = Path(import_root)
    if not root.exists():
        return []
    paths = [root] if root.is_file() else sorted(root.rglob("*.jsonl")) + sorted(root.rglob("*.json"))
    raws: list[dict[str, Any]] = []
    for path in paths:
        if path.suffix == ".jsonl":
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    raws.append(json.loads(line))
        elif path.suffix == ".json":
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                raws.extend(raw)
            elif isinstance(raw, dict) and "artifacts" in raw:
                raws.extend(raw["artifacts"])
            elif isinstance(raw, dict):
                raws.append(raw)
    return raws


def _precheck_reject_reason(raw: dict[str, Any]) -> str | None:
    if raw.get("capture_mode") not in CAPTURE_MODES:
        return "UNSUPPORTED_CAPTURE_MODE"
    if not raw.get("event_ts"):
        return "MISSING_TIMESTAMP"
    if not raw.get("captured_at"):
        return "MISSING_TIMESTAMP"
    return None


def _validation_reject_reason(raw: dict[str, Any], exc: ValidationError) -> str:
    text = str(exc)
    if "UNSUPPORTED_CAPTURE_MODE" in text or raw.get("capture_mode") not in CAPTURE_MODES:
        return "UNSUPPORTED_CAPTURE_MODE"
    if "event_ts" in text or "captured_at" in text:
        return "MISSING_TIMESTAMP"
    return "MALFORMED_ARTIFACT"


def _normalize_artifacts(
    artifacts: list[RealCachedArtifact],
    *,
    source_name: str,
) -> dict[str, Any]:
    spot_snapshots = [_spot_snapshot(item) for item in artifacts if item.artifact_type == "spot_snapshot"]
    spot_snapshots.extend(_spot_candle_snapshot(item) for item in artifacts if item.artifact_type == "spot_candle")
    market_windows = [
        _market_window(item) for item in artifacts if item.artifact_type == "pm_market_window"
    ]
    clob_snapshots = [
        _clob_snapshot(item) for item in artifacts if item.artifact_type == "pm_clob_snapshot"
    ]
    window_labels = {
        item.market_id: _window_label(item)
        for item in artifacts
        if item.artifact_type in {"pm_window_label", "pm_resolution_label"}
    }
    rows = align_pm_crypto_updown_rows(
        spot_snapshots=sorted(spot_snapshots, key=lambda item: (item["symbol"], item["timestamp_utc"])),
        market_windows=sorted(market_windows, key=lambda item: item["market_id"]),
        clob_snapshots=sorted(
            clob_snapshots,
            key=lambda item: (item["market_id"], item["token_id"], item["event_ts"]),
        ),
        window_labels=dict(sorted(window_labels.items())),
    )
    market_quality = {item["market_id"]: item["source_quality"] for item in market_windows}
    market_capture_modes = _market_capture_modes(artifacts)
    quality_flags_by_market, quality_flags_by_source, quality_flags_by_clob = _quality_flag_maps(artifacts)
    annotated_rows = []
    for row in rows:
        flags = set(row.get("data_quality_flags", []))
        flags.update(quality_flags_by_market.get(row["market_id"], []))
        flags.update(quality_flags_by_clob.get(row["clob_snapshot_id"], []))
        for source_id in row.get("source_ids", []):
            flags.update(quality_flags_by_source.get(source_id, []))
        item = {
            **row,
            "source_name": source_name,
            "source_type": "real_cached_import",
            "source_quality": market_quality.get(row["market_id"], "real_cached"),
            "source_capture_modes": sorted(market_capture_modes.get(row["market_id"], [])),
            "data_quality_flags": sorted(flags),
        }
        annotated_rows.append(item)
    return {
        "source_name": source_name,
        "source_type": "real_cached_import",
        "source_quality": "real_cached",
        "spot_snapshots": spot_snapshots,
        "market_windows": market_windows,
        "clob_snapshots": clob_snapshots,
        "window_labels": list(window_labels.values()),
        "rows": annotated_rows,
        "market_quality": market_quality,
        "market_capture_modes": {key: sorted(value) for key, value in market_capture_modes.items()},
    }


def _spot_snapshot(item: RealCachedArtifact) -> dict[str, Any]:
    return {
        "timestamp_utc": utc_string(parse_utc(item.event_ts)),
        "symbol": item.spot_symbol,
        "price": float(item.price),
        "source_id": item.source_id,
    }


def _spot_candle_snapshot(item: RealCachedArtifact) -> dict[str, Any]:
    return {
        "timestamp_utc": utc_string(parse_utc(item.event_ts)),
        "symbol": item.spot_symbol,
        "price": float(item.close),
        "source_id": item.source_id,
    }


def _market_window(item: RealCachedArtifact) -> dict[str, Any]:
    return {
        "market_id": item.market_id,
        "condition_id": item.condition_id,
        "slug": item.slug,
        "spot_symbol": item.spot_symbol,
        "window_start_ts": utc_string(parse_utc(item.window_start_ts)),
        "window_end_ts": utc_string(parse_utc(item.window_end_ts)),
        "tokens": item.tokens,
        "source_id": item.source_id,
        "source_quality": item.source_quality,
        "capture_mode": item.capture_mode,
    }


def _clob_snapshot(item: RealCachedArtifact) -> dict[str, Any]:
    return {
        "clob_snapshot_id": item.clob_snapshot_id,
        "market_id": item.market_id,
        "token_id": item.token_id,
        "event_ts": utc_string(parse_utc(item.event_ts)),
        "bid": float(item.bid),
        "ask": float(item.ask),
        "last_trade_price": float(item.last_trade_price),
        "volume": float(item.volume),
        "liquidity": float(item.liquidity),
        "source_id": item.source_id,
    }


def _window_label(item: RealCachedArtifact) -> dict[str, Any]:
    return {
        "market_id": item.market_id,
        "resolved_outcome": item.resolved_outcome,
        "label_status": item.label_status,
        "resolution_source_id": item.resolution_source_id,
        "source_id": item.source_id,
        "source_quality": item.source_quality,
        "capture_mode": item.capture_mode,
    }


def _market_capture_modes(
    artifacts: list[RealCachedArtifact],
) -> dict[str, set[str]]:
    modes: dict[str, set[str]] = defaultdict(set)
    for artifact in artifacts:
        if artifact.market_id:
            modes[artifact.market_id].add(artifact.capture_mode)
    return modes


def _quality_flag_maps(
    artifacts: list[RealCachedArtifact],
) -> tuple[dict[str, set[str]], dict[str, set[str]], dict[str, set[str]]]:
    by_market: dict[str, set[str]] = defaultdict(set)
    by_source: dict[str, set[str]] = defaultdict(set)
    by_clob: dict[str, set[str]] = defaultdict(set)
    for artifact in artifacts:
        flags = set(artifact.quality_flags)
        if artifact.source_note and "fixture" in artifact.source_note:
            flags.add("REAL_CACHED_SAMPLE_FIXTURE")
        if artifact.market_id:
            by_market[artifact.market_id].update(flags)
        by_source[artifact.source_id].update(flags)
        if artifact.clob_snapshot_id:
            by_clob[artifact.clob_snapshot_id].update(flags)
    return by_market, by_source, by_clob


def _summarize_normalized_source(normalized: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_name": normalized["source_name"],
        "source_type": normalized["source_type"],
        "source_quality": normalized["source_quality"],
        "spot_snapshot_count": len(normalized["spot_snapshots"]),
        "market_window_count": len(normalized["market_windows"]),
        "clob_snapshot_count": len(normalized["clob_snapshots"]),
        "window_label_count": len(normalized["window_labels"]),
        "row_count": len(normalized["rows"]),
        "market_quality": normalized["market_quality"],
        "market_capture_modes": normalized["market_capture_modes"],
    }


def _import_status(source: dict[str, Any]) -> str:
    if source["real_cached_replay_ready_row_count"] > 0:
        return "REAL_CACHED_ROWS_IMPORTED"
    if source["accepted_artifact_count"] > 0:
        return "REAL_CACHED_IMPORT_READY"
    return "REAL_CACHED_CAPTURE_READY"


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_real_cached_import.json"
    md_path = root / "latest_real_cached_import.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 39 Real-Cached Import",
        "",
        "Local-only import and normalization of read-only replay artifacts.",
        "",
        f"Status: {payload['import_status']}",
        f"Accepted artifacts: {payload['accepted_artifact_count']}",
        f"Rejected artifacts: {payload['rejected_artifact_count']}",
        f"Replay-ready imported rows: {payload['imported_replay_ready_row_count']}",
        f"Real-cached replay-ready rows: {payload['real_cached_replay_ready_row_count']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        "",
        "## Rejections",
    ]
    if payload["rejected_by_reason"]:
        lines.extend(
            f"- {reason}: {count}" for reason, count in payload["rejected_by_reason"].items()
        )
    else:
        lines.append("- None")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
