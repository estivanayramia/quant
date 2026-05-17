from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from quant_os.readiness.canary_readiness_common import (
    load_rows,
    safety_payload,
    update_canary_state,
    write_json_markdown_report,
)

REPORT_DIR = Path("reports/canary_readiness/lineage_audit")


def evaluate_weather_candidate_lineage_audit(
    *,
    rows: list[dict[str, Any]] | None = None,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    rows = rows if rows is not None else load_rows(output_root=output_root)
    blockers: list[str] = []
    checked = []
    for row in rows:
        forecast_source = str(row.get("forecast_source", "")).lower()
        if "realized" in forecast_source or row.get("uses_resolution_as_forecast") is True:
            blockers.append("REALIZED_WEATHER_USED_AS_FORECAST")
        timestamps = {
            "forecast_ts": _parse_ts(row.get("forecast_ts")),
            "known_at_ts": _parse_ts(row.get("known_at_ts")),
            "orderbook_ts": _parse_ts(row.get("orderbook_ts")),
            "resolution_ts": _parse_ts(row.get("resolution_ts")),
        }
        if any(value is None for value in timestamps.values()):
            blockers.append("TIMESTAMP_MISSING_OR_INVALID")
        elif not (
            timestamps["forecast_ts"]
            <= timestamps["known_at_ts"]
            <= timestamps["orderbook_ts"]
            < timestamps["resolution_ts"]
        ):
            blockers.append("TIMESTAMP_ORDER_INVALID")
        checked.append(
            {
                "market_id": row.get("market_id"),
                "forecast_ts": row.get("forecast_ts"),
                "known_at_ts": row.get("known_at_ts"),
                "orderbook_ts": row.get("orderbook_ts"),
                "resolution_ts": row.get("resolution_ts"),
                "forecast_source": row.get("forecast_source"),
                "provenance_hash": row.get("provenance_hash"),
            }
        )
    unique_blockers = sorted(set(blockers))
    if "REALIZED_WEATHER_USED_AS_FORECAST" in unique_blockers:
        status = "LOOKAHEAD_RISK_BLOCKED"
    elif "TIMESTAMP_ORDER_INVALID" in unique_blockers:
        status = "TIMESTAMP_ALIGNMENT_FAILED"
    elif unique_blockers:
        status = "FORECAST_ARCHIVE_AMBIGUOUS"
    else:
        status = "LINEAGE_AUDIT_PASSED"
    payload = safety_payload(
        schema_version="weather_candidate_lineage_audit_v1",
        status=status,
        allowed_statuses=[
            "LINEAGE_AUDIT_PASSED",
            "LOOKAHEAD_RISK_BLOCKED",
            "FORECAST_ARCHIVE_AMBIGUOUS",
            "LABEL_SOURCE_AMBIGUOUS",
            "TIMESTAMP_ALIGNMENT_FAILED",
        ],
        candidate_id="pm_weather_forecast_market_mismatch",
        invariant="forecast_ts <= known_at_ts <= orderbook_ts < resolution_ts",
        row_count=len(rows),
        checked_rows=checked,
        source_urls_or_hashes=sorted(
            {str(row.get("provenance_hash")) for row in rows if row.get("provenance_hash")}
        ),
        blockers=unique_blockers,
        next_action="Run independent replay recomputation." if status == "LINEAGE_AUDIT_PASSED" else "Resolve lineage blocker.",
    )
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_lineage_audit.json",
        md_name="latest_lineage_audit.md",
        title="Weather Candidate Lineage Audit",
        summary="Audits timestamp lineage and no-lookahead invariants.",
    )
    update_canary_state(
        output_root=output_root,
        gate="lineage_audit",
        gate_status=status,
        evidence_paths=payload["report_paths"],
        gates_passed=["lineage_audit"] if status == "LINEAGE_AUDIT_PASSED" else [],
        gates_failed=[] if status == "LINEAGE_AUDIT_PASSED" else ["lineage_audit"],
        blocker=unique_blockers[0] if unique_blockers else None,
        next_action=payload["next_action"],
    )
    return payload


def write_weather_candidate_lineage_audit_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    return evaluate_weather_candidate_lineage_audit(output_root=output_root)


def _parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
