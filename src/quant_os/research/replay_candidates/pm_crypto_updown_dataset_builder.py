from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from quant_os.data.crypto_spot_snapshots import load_crypto_spot_snapshots
from quant_os.data.prediction_markets.clob_snapshots import load_clob_snapshots
from quant_os.data.prediction_markets.updown_market_windows import load_updown_market_windows
from quant_os.data.prediction_markets.window_labels import load_window_labels
from quant_os.research.replay_candidates.pm_crypto_updown_alignment import (
    DEFAULT_FIXTURE_ROOT,
    align_pm_crypto_updown_rows,
    build_pm_crypto_updown_dataset,
)
from quant_os.research.replay_candidates.pm_crypto_updown_real_cached_import import (
    build_pm_crypto_updown_real_cached_source,
)
from quant_os.research.replay_candidates.pm_crypto_updown_schema import CANDIDATE_ID
from quant_os.research.replay_candidates.pm_crypto_updown_signals import is_replay_ready_row
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

MIN_PRIMARY_REPLAY_READY_ROWS = 20
PRIMARY_EVIDENCE_SOURCE_QUALITIES = {"fixture_real_shaped", "real_cached"}
SOURCE_QUALITIES = ("real_cached", "fixture_real_shaped", "synthetic_stress")

REPORT_ROOT = Path("reports/sequence38/expanded_dataset")


@dataclass(frozen=True)
class ReplaySource:
    name: str
    source_type: str
    source_quality: str
    root: Path
    spot_file: str
    market_file: str
    clob_file: str
    label_file: str

    @property
    def paths(self) -> tuple[Path, Path, Path, Path]:
        return (
            self.root / self.spot_file,
            self.root / self.market_file,
            self.root / self.clob_file,
            self.root / self.label_file,
        )

    def exists(self) -> bool:
        return all(path.exists() for path in self.paths)


def build_pm_crypto_updown_expanded_dataset(
    *,
    fixture_root: str | Path = DEFAULT_FIXTURE_ROOT,
    extra_fixture_roots: list[str | Path] | None = None,
    capture_root: str | Path | None = None,
    real_cached_artifact_roots: list[str | Path] | None = None,
) -> dict[str, Any]:
    root = Path(fixture_root)
    sources = _source_specs(root, extra_fixture_roots=extra_fixture_roots)
    if capture_root is not None:
        sources.append(
            ReplaySource(
                name="manual_real_cached_capture",
                source_type="manual_capture",
                source_quality="real_cached",
                root=Path(capture_root),
                spot_file="spot_snapshots.csv",
                market_file="market_windows.json",
                clob_file="clob_snapshots.json",
                label_file="window_labels.json",
            )
        )

    current = build_pm_crypto_updown_dataset(fixture_root=root)
    current_primary = _primary_rows(
        _annotate_rows(
            current["rows"],
            source=ReplaySource(
                name="base_fixture",
                source_type="committed_fixture",
                source_quality="fixture_real_shaped",
                root=root,
                spot_file="spot_snapshots.csv",
                market_file="market_windows.json",
                clob_file="clob_snapshots.json",
                label_file="window_labels.json",
            ),
            market_quality={},
        )
    )

    rows: list[dict[str, Any]] = []
    skipped_sources = []
    for source in sources:
        if not source.exists():
            skipped_sources.append(
                {
                    "source_name": source.name,
                    "source_type": source.source_type,
                    "source_quality": source.source_quality,
                    "reason": "SOURCE_FILES_NOT_PRESENT",
                }
            )
            continue
        rows.extend(_load_source_rows(source))

    phase38_deduped, phase38_dropped = _dedupe_rows(rows)
    phase38_primary_rows = _primary_rows(phase38_deduped)
    phase38_replay_ready = [row for row in phase38_deduped if is_replay_ready_row(row)]
    real_cached_imports = []
    for index, artifact_root in enumerate(real_cached_artifact_roots or [], start=1):
        source = build_pm_crypto_updown_real_cached_source(
            import_root=artifact_root,
            source_name=f"real_cached_import_{index}",
        )
        real_cached_imports.append(_real_cached_import_summary(source))
        rows.extend(_annotate_real_cached_import_rows(source["rows"]))

    deduped, dropped = _dedupe_rows(rows)
    replay_ready = [row for row in deduped if is_replay_ready_row(row)]
    primary_rows = _primary_rows(deduped)
    synthetic_ready = [
        row for row in replay_ready if row["source_quality"] == "synthetic_stress"
    ]
    real_cached_rows = [row for row in deduped if row["source_quality"] == "real_cached"]
    real_cached_ready = [row for row in real_cached_rows if is_replay_ready_row(row)]

    source_quality_counts = dict(sorted(Counter(row["source_quality"] for row in deduped).items()))
    source_count = dict(sorted(Counter(row["source_name"] for row in deduped).items()))
    return {
        "schema_version": "pm_crypto_updown_expanded_dataset_v1",
        "sequence": "38",
        "candidate_id": CANDIDATE_ID,
        "minimum_primary_replay_ready_rows": MIN_PRIMARY_REPLAY_READY_ROWS,
        "current_replay_ready_row_count": len(
            [row for row in current["rows"] if is_replay_ready_row(row)]
        ),
        "current_primary_evidence_row_count": len(current_primary),
        "phase38_replay_ready_row_count": len(phase38_replay_ready),
        "phase38_primary_evidence_row_count": len(phase38_primary_rows),
        "row_count": len(deduped),
        "replay_ready_row_count": len(replay_ready),
        "primary_evidence_row_count": len(primary_rows),
        "diagnostic_row_count": len(deduped) - len(primary_rows),
        "real_cached_row_count": len(real_cached_rows),
        "real_cached_replay_ready_row_count": len(real_cached_ready),
        "synthetic_stress_row_count": source_quality_counts.get("synthetic_stress", 0),
        "synthetic_stress_replay_ready_row_count": len(synthetic_ready),
        "dedupe_dropped_row_count": dropped,
        "phase38_dedupe_dropped_row_count": phase38_dropped,
        "source_quality_counts": source_quality_counts,
        "source_counts": source_count,
        "skipped_sources": skipped_sources,
        "real_cached_imports": real_cached_imports,
        "rows_needed_for_threshold": max(MIN_PRIMARY_REPLAY_READY_ROWS - len(primary_rows), 0),
        "rows": deduped,
        "primary_rows": primary_rows,
        "real_cached_rows": real_cached_rows,
        "synthetic_stress_rows": [
            row for row in deduped if row["source_quality"] == "synthetic_stress"
        ],
        "source_quality_policy": {
            "primary_evidence_source_qualities": sorted(PRIMARY_EVIDENCE_SOURCE_QUALITIES),
            "synthetic_rows_count_as_primary": False,
        },
        "network_fetch_attempted": False,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_pm_crypto_updown_expanded_dataset_report(
    *,
    fixture_root: str | Path = DEFAULT_FIXTURE_ROOT,
    output_root: str | Path = ".",
    capture_root: str | Path | None = None,
    real_cached_artifact_roots: list[str | Path] | None = None,
) -> dict[str, Any]:
    payload = build_pm_crypto_updown_expanded_dataset(
        fixture_root=fixture_root,
        capture_root=capture_root,
        real_cached_artifact_roots=real_cached_artifact_roots,
    )
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _source_specs(
    fixture_root: Path,
    *,
    extra_fixture_roots: list[str | Path] | None,
) -> list[ReplaySource]:
    sources = [
        ReplaySource(
            name="base_fixture",
            source_type="committed_fixture",
            source_quality="fixture_real_shaped",
            root=fixture_root,
            spot_file="spot_snapshots.csv",
            market_file="market_windows.json",
            clob_file="clob_snapshots.json",
            label_file="window_labels.json",
        ),
        ReplaySource(
            name="expanded_fixture",
            source_type="committed_fixture",
            source_quality="fixture_real_shaped",
            root=fixture_root,
            spot_file="spot_snapshots_expanded.csv",
            market_file="market_windows_expanded.json",
            clob_file="clob_snapshots_expanded.json",
            label_file="window_labels_expanded.json",
        ),
    ]
    for index, extra_root in enumerate(extra_fixture_roots or [], start=1):
        sources.append(
            ReplaySource(
                name=f"extra_fixture_{index}",
                source_type="committed_fixture",
                source_quality="fixture_real_shaped",
                root=Path(extra_root),
                spot_file="spot_snapshots.csv",
                market_file="market_windows.json",
                clob_file="clob_snapshots.json",
                label_file="window_labels.json",
            )
        )
    return sources


def _load_source_rows(source: ReplaySource) -> list[dict[str, Any]]:
    spot_path, market_path, clob_path, label_path = source.paths
    rows = align_pm_crypto_updown_rows(
        spot_snapshots=load_crypto_spot_snapshots(spot_path),
        market_windows=load_updown_market_windows(market_path),
        clob_snapshots=load_clob_snapshots(clob_path),
        window_labels=load_window_labels(label_path),
    )
    return _annotate_rows(
        rows,
        source=source,
        market_quality=_market_quality_map(market_path, default_quality=source.source_quality),
    )


def _annotate_rows(
    rows: list[dict[str, Any]],
    *,
    source: ReplaySource,
    market_quality: dict[str, str],
) -> list[dict[str, Any]]:
    annotated = []
    for row in rows:
        quality = market_quality.get(row["market_id"], source.source_quality)
        item = {
            **row,
            "source_name": source.name,
            "source_type": source.source_type,
            "source_quality": quality,
            "source_hash": _source_hash(row),
        }
        item["primary_evidence_candidate"] = _is_primary_evidence_row(item)
        item["synthetic_stress_only"] = quality == "synthetic_stress"
        annotated.append(item)
    return annotated


def _annotate_real_cached_import_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    annotated = []
    for row in rows:
        quality = str(row.get("source_quality", "real_cached"))
        item = {
            **row,
            "source_quality": quality,
            "source_hash": _source_hash(row),
        }
        item["primary_evidence_candidate"] = _is_primary_evidence_row(item)
        item["synthetic_stress_only"] = quality == "synthetic_stress"
        annotated.append(item)
    return annotated


def _real_cached_import_summary(source: dict[str, Any]) -> dict[str, Any]:
    normalized = source["normalized_source"]
    return {
        "source_name": source["source_name"],
        "import_root": source["import_root"],
        "accepted_artifact_count": source["accepted_artifact_count"],
        "rejected_artifact_count": source["rejected_artifact_count"],
        "rejected_by_reason": source["rejected_by_reason"],
        "dedupe_dropped_artifact_count": source["dedupe_dropped_artifact_count"],
        "imported_replay_ready_row_count": source["imported_replay_ready_row_count"],
        "real_cached_replay_ready_row_count": source["real_cached_replay_ready_row_count"],
        "source_mode_counts": source["source_mode_counts"],
        "artifact_type_counts": source["artifact_type_counts"],
        "market_window_count": len(normalized["market_windows"]),
        "clob_snapshot_count": len(normalized["clob_snapshots"]),
        "spot_snapshot_count": len(normalized["spot_snapshots"]),
        "window_label_count": len(normalized["window_labels"]),
    }


def _market_quality_map(path: Path, *, default_quality: str) -> dict[str, str]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {
        str(item["market_id"]): str(item.get("source_quality", default_quality))
        for item in raw
    }


def _dedupe_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    seen = set()
    deduped = []
    dropped = 0
    for row in sorted(
        rows,
        key=lambda item: (
            item["market_id"],
            item["window_start_ts"],
            item["event_ts"],
            item["token_id"],
            item["source_name"],
        ),
    ):
        key = (
            row["market_id"],
            row["window_start_ts"],
            row["event_ts"],
            row["token_id"],
            row["source_hash"],
        )
        if key in seen:
            dropped += 1
            continue
        seen.add(key)
        deduped.append(row)
    return deduped, dropped


def _primary_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if _is_primary_evidence_row(row)]


def _is_primary_evidence_row(row: dict[str, Any]) -> bool:
    return (
        row.get("source_quality") in PRIMARY_EVIDENCE_SOURCE_QUALITIES
        and is_replay_ready_row(row)
        and row.get("label_status") == "RESOLVED"
        and row.get("resolved_outcome") is not None
    )


def _source_hash(row: dict[str, Any]) -> str:
    digest = hashlib.sha256()
    for key in (
        "market_id",
        "condition_id",
        "window_start_ts",
        "event_ts",
        "token_id",
        "clob_snapshot_id",
        "provenance_hash",
    ):
        digest.update(str(row.get(key)).encode("utf-8"))
    return digest.hexdigest()


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_pm_crypto_updown_expanded_dataset.json"
    md_path = root / "latest_pm_crypto_updown_expanded_dataset.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 38 PM Crypto UP/DOWN Expanded Dataset",
        "",
        "Fixture-safe source mix for replay evidence expansion. No live authority.",
        "",
        f"Rows: {payload['row_count']}",
        f"Replay-ready rows: {payload['replay_ready_row_count']}",
        f"Primary evidence rows: {payload['primary_evidence_row_count']}",
        f"Real-cached rows: {payload['real_cached_row_count']}",
        f"Synthetic stress rows: {payload['synthetic_stress_row_count']}",
        f"Rows dropped by dedupe: {payload['dedupe_dropped_row_count']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        "",
        "## Source Quality",
    ]
    lines.extend(
        f"- {quality}: {count}"
        for quality, count in payload["source_quality_counts"].items()
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
