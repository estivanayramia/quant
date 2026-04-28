from __future__ import annotations

from typing import Any

from quant_os.data.dataset_manifest import build_dataset_manifest
from quant_os.data.dataset_quality import run_dataset_quality
from quant_os.data.dataset_splits import build_dataset_splits
from quant_os.data.evidence_scoring import calculate_evidence_score
from quant_os.data.expanded_demo_data import seed_expanded_demo_data
from quant_os.data.leakage_checks import run_leakage_checks


def dataset_evidence_status() -> dict[str, Any]:
    seed_summary = seed_expanded_demo_data()
    manifest = build_dataset_manifest()
    quality = run_dataset_quality()
    splits = build_dataset_splits()
    leakage = run_leakage_checks(splits_payload=splits)
    evidence = calculate_evidence_score()
    return {
        "dataset_evidence": {
            "manifest_status": manifest["status"],
            "quality_status": quality["status"],
            "leakage_status": leakage["status"],
            "evidence_status": evidence["final_evidence_status"],
            "symbols_count": len(manifest["symbols"]),
            "timeframes_count": len(manifest["timeframes"]),
            "regime_coverage": quality["regime_coverage"],
            "blockers": evidence["blockers"],
            "warnings": evidence["warnings"],
            "latest_report_path": "reports/evidence/latest_evidence_score.md",
            "live_promotion_status": "LIVE_BLOCKED",
            "seed_rows": seed_summary["rows"],
        }
    }
