from __future__ import annotations

from typing import Any

from quant_os.research.research_evidence_report import write_research_evidence_report


def research_evidence_status() -> dict[str, Any]:
    report = write_research_evidence_report()
    return {
        "research_evidence": {
            "evidence_status": report["evidence_score"]["final_evidence_status"],
            "quality_status": report["dataset_quality_summary"]["status"],
            "leakage_status": report["leakage_summary"]["status"],
            "latest_report_path": "reports/evidence/latest_research_evidence_report.md",
            "live_promotion_status": "LIVE_BLOCKED",
        }
    }
