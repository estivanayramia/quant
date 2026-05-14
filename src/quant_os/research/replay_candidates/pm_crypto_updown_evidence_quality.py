from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.research.replay_candidates.pm_crypto_updown_alignment import DEFAULT_FIXTURE_ROOT
from quant_os.research.replay_candidates.pm_crypto_updown_dataset_builder import (
    MIN_PRIMARY_REPLAY_READY_ROWS,
    build_pm_crypto_updown_expanded_dataset,
)
from quant_os.research.replay_candidates.pm_crypto_updown_schema import CANDIDATE_ID
from quant_os.research.replay_candidates.pm_crypto_updown_signals import is_replay_ready_row
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

REPORT_ROOT = Path("reports/sequence38/evidence_quality")


def evaluate_pm_crypto_updown_evidence_quality(
    *,
    fixture_root: str | Path = DEFAULT_FIXTURE_ROOT,
    capture_root: str | Path | None = None,
) -> dict[str, Any]:
    dataset = build_pm_crypto_updown_expanded_dataset(
        fixture_root=fixture_root,
        capture_root=capture_root,
    )
    rows = dataset["rows"]
    row_count = len(rows)
    replay_ready = [row for row in rows if is_replay_ready_row(row)]
    primary_rows = dataset["primary_rows"]
    missing_clob = _count(rows, "MISSING_CLOB_SNAPSHOT")
    missing_spot = _count(rows, "MISSING_SPOT_SNAPSHOT")
    stale_count = _count(rows, "STALE_SPOT_SNAPSHOT") + _count(rows, "STALE_CLOB_SNAPSHOT")
    missing_label = _count(rows, "MISSING_WINDOW_LABELS")
    unresolved_label = _count(rows, "LABEL_UNRESOLVED")
    wide_spread = _count(rows, "WIDE_SPREAD")
    low_liquidity = _count(rows, "LOW_LIQUIDITY")
    label_count = len(
        {
            row["market_id"]
            for row in rows
            if row.get("label_status") == "RESOLVED" and row.get("resolved_outcome") is not None
        }
    )
    rows_needed = max(MIN_PRIMARY_REPLAY_READY_ROWS - len(primary_rows), 0)
    blockers = _blockers(
        primary_count=len(primary_rows),
        missing_clob=missing_clob,
        missing_spot=missing_spot,
        missing_label=missing_label,
    )
    status = _status(
        primary_count=len(primary_rows),
        current_primary=dataset["current_primary_evidence_row_count"],
        missing_clob=missing_clob,
        missing_spot=missing_spot,
        label_count=label_count,
    )
    return {
        "schema_version": "pm_crypto_updown_evidence_quality_v1",
        "sequence": "38",
        "candidate_id": CANDIDATE_ID,
        "evidence_expansion_status": status,
        "candidate_status": (
            "READY_FOR_EXPANDED_SHADOW_REPLAY"
            if status == "READY_FOR_EXPANDED_SHADOW_REPLAY"
            else "CANDIDATE_REMAINS_BLOCKED"
        ),
        "minimum_primary_replay_ready_rows": MIN_PRIMARY_REPLAY_READY_ROWS,
        "current_replay_ready_row_count": dataset["current_replay_ready_row_count"],
        "current_primary_evidence_row_count": dataset["current_primary_evidence_row_count"],
        "row_count": row_count,
        "total_rows": row_count,
        "replay_ready_row_count": len(replay_ready),
        "primary_evidence_row_count": len(primary_rows),
        "diagnostic_row_count": dataset["diagnostic_row_count"],
        "synthetic_stress_row_count": dataset["synthetic_stress_row_count"],
        "synthetic_stress_replay_ready_row_count": dataset[
            "synthetic_stress_replay_ready_row_count"
        ],
        "market_count": len({row["market_id"] for row in rows}),
        "window_count": len({(row["market_id"], row["window_start_ts"]) for row in rows}),
        "label_count": label_count,
        "clob_coverage": _coverage(row_count, row_count - missing_clob),
        "spot_coverage": _coverage(row_count, row_count - missing_spot),
        "stale_snapshot_count": stale_count,
        "wide_spread_count": wide_spread,
        "low_liquidity_count": low_liquidity,
        "unresolved_label_count": unresolved_label,
        "missing_label_count": missing_label,
        "spread_liquidity_caveats": _caveats(wide_spread=wide_spread, low_liquidity=low_liquidity),
        "threshold_progress": {
            "primary_rows": len(primary_rows),
            "minimum_primary_rows": MIN_PRIMARY_REPLAY_READY_ROWS,
            "fraction": len(primary_rows) / MIN_PRIMARY_REPLAY_READY_ROWS,
        },
        "rows_needed_for_threshold": rows_needed,
        "expanded_replay_ready_row_delta": (
            len(replay_ready) - dataset["current_replay_ready_row_count"]
        ),
        "source_quality_counts": dataset["source_quality_counts"],
        "blockers": blockers,
        "dataset_report": dataset,
        "network_fetch_attempted": False,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_pm_crypto_updown_evidence_quality_report(
    *,
    fixture_root: str | Path = DEFAULT_FIXTURE_ROOT,
    output_root: str | Path = ".",
    capture_root: str | Path | None = None,
) -> dict[str, Any]:
    payload = evaluate_pm_crypto_updown_evidence_quality(
        fixture_root=fixture_root,
        capture_root=capture_root,
    )
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _count(rows: list[dict[str, Any]], flag: str) -> int:
    return sum(1 for row in rows if flag in row.get("data_quality_flags", []))


def _coverage(row_count: int, covered_count: int) -> float:
    if row_count == 0:
        return 0.0
    return covered_count / row_count


def _blockers(
    *,
    primary_count: int,
    missing_clob: int,
    missing_spot: int,
    missing_label: int,
) -> list[str]:
    blockers = []
    if missing_clob:
        blockers.append("MISSING_CLOB_SNAPSHOT")
    if missing_spot:
        blockers.append("MISSING_SPOT_SNAPSHOT")
    if missing_label:
        blockers.append("MISSING_WINDOW_LABELS")
    if primary_count < MIN_PRIMARY_REPLAY_READY_ROWS:
        blockers.append(f"PRIMARY_ROWS_{primary_count}_LT_{MIN_PRIMARY_REPLAY_READY_ROWS}")
    return blockers


def _status(
    *,
    primary_count: int,
    current_primary: int,
    missing_clob: int,
    missing_spot: int,
    label_count: int,
) -> str:
    if missing_clob:
        return "REPLAY_EVIDENCE_BLOCKED_MISSING_CLOB"
    if missing_spot:
        return "REPLAY_EVIDENCE_BLOCKED_MISSING_SPOT"
    if label_count == 0:
        return "REPLAY_EVIDENCE_BLOCKED_MISSING_LABELS"
    if primary_count >= MIN_PRIMARY_REPLAY_READY_ROWS:
        return "READY_FOR_EXPANDED_SHADOW_REPLAY"
    if primary_count > current_primary:
        return "REPLAY_EVIDENCE_PARTIAL"
    return "REPLAY_EVIDENCE_STILL_TOO_THIN"


def _caveats(*, wide_spread: int, low_liquidity: int) -> list[str]:
    caveats = []
    if wide_spread:
        caveats.append("WIDE_SPREAD_ROWS_PRESENT")
    if low_liquidity:
        caveats.append("LOW_LIQUIDITY_ROWS_PRESENT")
    return caveats


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_pm_crypto_updown_evidence_quality.json"
    md_path = root / "latest_pm_crypto_updown_evidence_quality.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 38 PM Crypto UP/DOWN Evidence Quality",
        "",
        "Expanded evidence quality and threshold progress. No live authority.",
        "",
        f"Status: {payload['evidence_expansion_status']}",
        f"Candidate status: {payload['candidate_status']}",
        f"Replay-ready rows: {payload['replay_ready_row_count']}",
        f"Primary evidence rows: {payload['primary_evidence_row_count']}",
        f"Rows needed for threshold: {payload['rows_needed_for_threshold']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        "",
        "## Blockers",
    ]
    lines.extend(f"- {item}" for item in (payload["blockers"] or ["None"]))
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
