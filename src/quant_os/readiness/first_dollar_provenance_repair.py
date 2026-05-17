from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.proving.profit_candidate_artifacts import regenerate_profit_candidate_artifacts
from quant_os.readiness.canary_readiness_common import safety_payload, write_json_markdown_report
from quant_os.readiness.first_dollar_provenance_audit import (
    REQUIRED_ARTIFACTS,
    evaluate_first_dollar_provenance_audit,
)

REPORT_DIR = Path("reports/first_dollar_preflight/provenance_repair")


def evaluate_first_dollar_provenance_repair(
    *,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    before_missing = [
        path for path in REQUIRED_ARTIFACTS if not (Path(output_root) / path).exists()
    ]
    regeneration = regenerate_profit_candidate_artifacts(output_root=output_root)
    audit = evaluate_first_dollar_provenance_audit(output_root=output_root)
    blockers = [] if audit["status"] == "PROVENANCE_AUDIT_PASSED" else audit["blockers"]
    status = "PROVENANCE_REPAIR_PASSED" if not blockers else "PROVENANCE_REPAIR_BLOCKED"
    payload = safety_payload(
        schema_version="first_dollar_provenance_repair_v1",
        status=status,
        allowed_statuses=[
            "PROVENANCE_REPAIR_PASSED",
            "PROVENANCE_REPAIR_BLOCKED",
            "REQUIRES_TRACKED_SANITIZED_FIXTURE",
            "REQUIRES_PUBLIC_REGENERATION",
            "LOCAL_ONLY_ARTIFACT_DEPENDENCY_REMOVED",
        ],
        repair_strategy="tracked_sanitized_fixture_regeneration",
        missing_artifacts_before_repair=before_missing,
        missing_artifacts_after_repair=audit["missing_artifacts"],
        regenerated_artifacts=regeneration["generated_artifacts"],
        tracked_artifacts_added=[
            "tests/fixtures/profit_candidates/weather_iem_mos_kalshi_100/candidate_manifest.json",
            "tests/fixtures/profit_candidates/weather_iem_mos_kalshi_100/weather_resolved_rows.json",
            "tests/fixtures/profit_candidates/weather_iem_mos_kalshi_100/provenance_hashes.json",
            "tests/fixtures/profit_candidates/weather_iem_mos_kalshi_100/README.md",
        ],
        artifact_hashes=regeneration["artifact_hashes"],
        source_quality_status=audit.get("source_quality_status"),
        raw_ignored_captures_required=False,
        public_network_required=False,
        fresh_worktree_can_reproduce=status == "PROVENANCE_REPAIR_PASSED",
        secrets_keys_auth_absent=True,
        blockers=blockers,
        next_action="Run canary readiness from regenerated artifacts."
        if status == "PROVENANCE_REPAIR_PASSED"
        else "Repair candidate artifact provenance.",
    )
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_provenance_repair.json",
        md_name="latest_provenance_repair.md",
        title="First-Dollar Provenance Repair",
        summary="Regenerates missing candidate evidence from a tracked sanitized fixture.",
    )
    return payload


def write_first_dollar_provenance_repair_report(
    *,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    return evaluate_first_dollar_provenance_repair(output_root=output_root)
