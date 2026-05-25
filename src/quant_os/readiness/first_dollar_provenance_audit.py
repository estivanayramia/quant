from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from quant_os.readiness.canary_readiness_common import (
    load_dataset_payload,
    load_paper_payload,
    load_profit_payload,
    safety_payload,
    write_json_markdown_report,
)

REPORT_DIR = Path("reports/first_dollar_preflight/provenance")
REQUIRED_ARTIFACTS = [
    "reports/profit_campaign/latest_profit_campaign.json",
    "reports/sequence52/weather_resolved_dataset/latest_weather_resolved_dataset.json",
    "reports/sequence52/weather_batch_paper_proving/latest_weather_batch_paper_proving.json",
]


def evaluate_first_dollar_provenance_audit(
    *,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    root = Path(output_root)
    missing = [path for path in REQUIRED_ARTIFACTS if not (root / path).exists()]
    profit = load_profit_payload(output_root=output_root) or {}
    dataset = load_dataset_payload(output_root=output_root) or {}
    paper = load_paper_payload(output_root=output_root) or {}
    blockers = list(missing)
    if profit and profit.get("paper_profit_status") != "PAPER_PROFIT_CANDIDATE_FOUND":
        blockers.append("PAPER_PROFIT_CANDIDATE_FOUND_MISSING")
    if dataset and dataset.get("dataset_status") != "WEATHER_PROOF_ROWS_BUILT":
        blockers.append("WEATHER_PROOF_ROWS_BUILT_MISSING")
    if paper and paper.get("readiness_status") != "PAPER_PROFIT_CANDIDATE":
        blockers.append("PAPER_PROFIT_CANDIDATE_MISSING")
    if paper and paper.get("source_quality_tier") in {"UNKNOWN", "WEAK", "SYNTHETIC_ONLY", None}:
        blockers.append("SOURCE_QUALITY_NOT_PROOF")
    status = "PROVENANCE_AUDIT_PASSED" if not blockers else "PROVENANCE_BLOCKED_BY_MISSING_FIXTURE"
    artifact_hashes = {
        path: _file_sha256(root / path)
        for path in REQUIRED_ARTIFACTS
        if (root / path).exists()
    }
    payload = safety_payload(
        schema_version="first_dollar_provenance_audit_v1",
        status=status,
        allowed_statuses=[
            "PROVENANCE_AUDIT_PASSED",
            "PROVENANCE_BLOCKED_BY_LOCAL_ONLY_ARTIFACT",
            "PROVENANCE_BLOCKED_BY_MISSING_FIXTURE",
            "PROVENANCE_BLOCKED_BY_UNREPRODUCIBLE_REPORT",
        ],
        required_artifacts=REQUIRED_ARTIFACTS,
        missing_artifacts=missing,
        artifact_hashes=artifact_hashes,
        source_quality_status=paper.get("source_quality_tier"),
        proof_row_count=dataset.get("proof_row_count", paper.get("proof_row_count", 0)),
        raw_ignored_captures_required=False,
        public_network_required=False,
        generated_from_tracked_fixture=not missing,
        blockers=blockers,
        next_action="Run first-dollar provenance repair."
        if blockers
        else "Run first-dollar security scan.",
    )
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_provenance_audit.json",
        md_name="latest_provenance_audit.md",
        title="First-Dollar Provenance Audit",
        summary="Audits candidate artifact provenance before first-dollar preflight.",
    )
    return payload


def write_first_dollar_provenance_audit_report(
    *,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    return evaluate_first_dollar_provenance_audit(output_root=output_root)


def _file_sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
