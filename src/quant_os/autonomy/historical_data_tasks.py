from __future__ import annotations

from typing import Any

from quant_os.data.historical_manifest import build_historical_manifest
from quant_os.data.historical_quality import run_historical_quality
from quant_os.data.provider_check import check_historical_providers
from quant_os.research.historical_evidence import calculate_historical_evidence_score


def historical_data_status() -> dict[str, Any]:
    providers = check_historical_providers()
    manifest = build_historical_manifest()
    quality = run_historical_quality()
    evidence = calculate_historical_evidence_score()
    return {
        "historical_data": {
            "provider_status": providers["providers"],
            "imported_datasets_count": 1 if manifest["rows"] else 0,
            "latest_manifest_status": manifest["status"],
            "latest_quality_status": quality["status"],
            "latest_historical_evidence_status": evidence["final_evidence_status"],
            "source_types": [manifest["source_type"]],
            "blockers": evidence["blockers"],
            "warnings": evidence["warnings"],
            "latest_report_path": "reports/historical/evidence/latest_historical_evidence_score.md",
            "live_promotion_status": "LIVE_BLOCKED",
        }
    }
