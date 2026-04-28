from __future__ import annotations

from typing import Any

from quant_os.data.dataset_manifest import build_dataset_manifest
from quant_os.data.dataset_quality import run_dataset_quality
from quant_os.data.dataset_splits import build_dataset_splits
from quant_os.data.evidence_scoring import calculate_evidence_score
from quant_os.data.leakage_checks import run_leakage_checks


def build_dataset_report() -> dict[str, Any]:
    manifest = build_dataset_manifest()
    quality = run_dataset_quality()
    splits = build_dataset_splits()
    leakage = run_leakage_checks(splits_payload=splits)
    evidence = calculate_evidence_score()
    return {
        "manifest": manifest,
        "quality": quality,
        "splits": splits,
        "leakage": leakage,
        "evidence": evidence,
    }
