from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from quant_os.research.intake.artifact_fetcher import build_artifact_fetch_report
from quant_os.research.intake.dedupe import dedupe_artifacts
from quant_os.research.social_intake.evidence_acquisition_report import (
    write_evidence_acquisition_report,
)
from quant_os.research.social_intake.hypothesis_queue import write_hypothesis_queue_report
from quant_os.research.social_intake.research_task_queue import (
    write_research_task_queue_report,
)
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY


def run_research_intake(
    *,
    source_config_path: str | Path,
    output_root: str | Path = ".",
    manual_network_fetch_enabled: bool = False,
) -> dict[str, Any]:
    fetch_report = build_artifact_fetch_report(
        source_config_path=source_config_path,
        manual_network_fetch_enabled=manual_network_fetch_enabled,
    )
    deduped = dedupe_artifacts(fetch_report["artifacts"])
    social_capture_artifact = next(
        item for item in deduped["unique_artifacts"] if item["source_type"] == "social_capture"
    )
    capture_root = Path(social_capture_artifact["source_path"])
    hypotheses = write_hypothesis_queue_report(capture_root=capture_root, output_root=output_root)
    task_queue = write_research_task_queue_report(capture_root=capture_root, output_root=output_root)
    evidence_plan = write_evidence_acquisition_report(
        capture_root=capture_root,
        output_root=output_root,
    )
    run_id = _run_id(source_config_path=source_config_path, artifact_hashes=[
        item["raw_hash"] for item in fetch_report["artifacts"]
    ])
    return {
        "schema_version": "research_intake_run_v1",
        "sequence": "35",
        "run_status": "INTAKE_RUN_COMPLETED_RESEARCH_ONLY",
        "run_id": run_id,
        "source_config_path": str(source_config_path),
        "artifact_count": fetch_report["fetched_artifact_count"],
        "duplicate_count": deduped["duplicate_count"],
        "rejected_source_count": fetch_report["rejected_source_count"],
        "hypothesis_count": hypotheses["hypothesis_count"],
        "task_count": len(task_queue["tasks"]),
        "artifacts": fetch_report["artifacts"],
        "unique_artifacts": deduped["unique_artifacts"],
        "duplicate_artifacts": deduped["duplicate_artifacts"],
        "rejected_sources": fetch_report["rejected_sources"],
        "hypotheses": hypotheses["hypotheses"],
        "tasks": task_queue["tasks"],
        "evidence_plan_updates": {
            "phase33_blocker_addressed": evidence_plan["phase33_blocker_addressed"],
            "data_needed": evidence_plan["data_needed"],
            "replay_improvements_needed": evidence_plan["replay_improvements_needed"],
            "hypotheses_worth_testing_count": len(evidence_plan["hypotheses_worth_testing"]),
            "hypotheses_rejected_count": len(evidence_plan["hypotheses_rejected"]),
        },
        "source_policy_report_paths": fetch_report.get("source_policy_report_paths", {}),
        "hypothesis_queue_report_paths": hypotheses["report_paths"],
        "research_task_report_paths": task_queue["report_paths"],
        "evidence_plan_report_paths": evidence_plan["report_paths"],
        "network_fetch_attempted": False,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _run_id(*, source_config_path: str | Path, artifact_hashes: list[str]) -> str:
    seed = "|".join([str(Path(source_config_path)), *sorted(artifact_hashes)])
    return f"intake_{hashlib.sha256(seed.encode('utf-8')).hexdigest()[:16]}"
