from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

REPORT_ROOT = Path("reports/sequence35/knowledge_ledger")
DETERMINISTIC_SEEN_AT = "1970-01-01T00:00:00Z"


def build_knowledge_ledger_summary(*, intake_run: dict[str, Any]) -> dict[str, Any]:
    entries = _entries_from_run(intake_run)
    status_counts = Counter(entry["status"] for entry in entries)
    unique_count = sum(1 for entry in entries if entry["status"] != "DUPLICATE")
    duplicate_count = status_counts.get("DUPLICATE", 0)
    return {
        "schema_version": "research_knowledge_ledger_summary_v1",
        "sequence": "35",
        "ledger_status": "HASH_DEDUPED_APPEND_SAFE_SUMMARY",
        "run_id": intake_run["run_id"],
        "unique_artifact_count": unique_count,
        "duplicate_artifact_count": duplicate_count,
        "status_counts": dict(sorted(status_counts.items())),
        "entries": entries,
        "ledger_generated_under_reports": True,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_knowledge_ledger_summary(
    *,
    intake_run: dict[str, Any],
    output_root: str | Path = ".",
) -> dict[str, Any]:
    payload = build_knowledge_ledger_summary(intake_run=intake_run)
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _entries_from_run(intake_run: dict[str, Any]) -> list[dict[str, Any]]:
    task_ids = [task["task_id"] for task in intake_run.get("tasks", [])]
    hypothesis_ids = [hypothesis["hypothesis_id"] for hypothesis in intake_run.get("hypotheses", [])]
    entries = []
    for artifact in intake_run["unique_artifacts"]:
        status = (
            "PROMOTED_TO_EVIDENCE_PLAN"
            if artifact["source_type"] == "social_capture"
            else "PROMOTED_TO_RESEARCH_TASK"
        )
        entries.append(_entry(artifact, status, task_ids=task_ids, hypothesis_ids=hypothesis_ids))
    for artifact in intake_run["duplicate_artifacts"]:
        entries.append(_entry(artifact, "DUPLICATE", task_ids=[], hypothesis_ids=[]))
    return sorted(entries, key=lambda item: item["artifact_id"])


def _entry(
    artifact: dict[str, Any],
    status: str,
    *,
    task_ids: list[str],
    hypothesis_ids: list[str],
) -> dict[str, Any]:
    return {
        "artifact_id": artifact["artifact_id"],
        "artifact_hash": artifact["raw_hash"],
        "source_ids": [artifact["source_id"]],
        "first_seen": DETERMINISTIC_SEEN_AT,
        "last_seen": DETERMINISTIC_SEEN_AT,
        "status": status,
        "hypothesis_links": hypothesis_ids if status != "DUPLICATE" else [],
        "task_links": task_ids if status != "DUPLICATE" else [],
        "duplicate_of": artifact.get("duplicate_of"),
    }


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_knowledge_ledger_summary.json"
    md_path = root / "latest_knowledge_ledger_summary.md"
    state_path = root / "latest_knowledge_ledger_state.json"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    state_path.write_text(
        json.dumps({"entries": payload["entries"]}, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    lines = [
        "# Sequence 35 Knowledge Ledger Summary",
        "",
        "Hash-based dedupe summary for local research artifacts.",
        "",
        f"Unique artifacts: {payload['unique_artifact_count']}",
        f"Duplicate artifacts: {payload['duplicate_artifact_count']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        "",
        "## Status Counts",
    ]
    lines.extend(f"- {key}: {value}" for key, value in payload["status_counts"].items())
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "json": str(json_path),
        "markdown": str(md_path),
        "state": str(state_path),
    }
