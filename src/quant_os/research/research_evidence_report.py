from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quant_os.data.dataset_manifest import build_dataset_manifest
from quant_os.data.dataset_quality import run_dataset_quality
from quant_os.data.dataset_splits import build_dataset_splits
from quant_os.data.evidence_scoring import calculate_evidence_score
from quant_os.data.leakage_checks import run_leakage_checks
from quant_os.research.leaderboard import build_strategy_leaderboard
from quant_os.research.overfit_checks import run_overfit_checks
from quant_os.research.regime_tests import run_regime_tests
from quant_os.research.strategy_ablation import run_strategy_ablation
from quant_os.research.walk_forward import run_walk_forward_validation

EVIDENCE_ROOT = Path("reports/evidence")


def write_research_evidence_report() -> dict[str, Any]:
    manifest = build_dataset_manifest()
    quality = run_dataset_quality()
    splits = build_dataset_splits()
    leakage = run_leakage_checks(splits_payload=splits)
    evidence = calculate_evidence_score()
    leaderboard = build_strategy_leaderboard()
    ablation = run_strategy_ablation()
    walk_forward = run_walk_forward_validation()
    regime = run_regime_tests()
    overfit = run_overfit_checks()
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset_manifest_summary": {
            "dataset_id": manifest["dataset_id"],
            "symbols": manifest["symbols"],
            "timeframes": manifest["timeframes"],
            "rows": manifest["rows"],
        },
        "dataset_quality_summary": {
            "status": quality["status"],
            "warnings": quality["warnings"],
            "failures": quality["failures"],
        },
        "split_summary": {"status": splits["status"], "items": len(splits["items"])},
        "leakage_summary": {
            "status": leakage["status"],
            "target_leakage": leakage["target_leakage"],
        },
        "strategy_leaderboard_summary": {
            "top_strategy": leaderboard["top_strategy"],
            "dry_run_candidates": leaderboard["dry_run_candidates"],
        },
        "ablation_summary": {"status": ablation["status"]},
        "walk_forward_summary": {"status": walk_forward["status"]},
        "regime_summary": {"status": regime["status"]},
        "overfit_summary": {"status": overfit["status"], "warnings": overfit["warnings"]},
        "evidence_score": evidence,
        "blockers": evidence["blockers"],
        "warnings": evidence["warnings"],
        "dry_run_candidate_status": evidence["final_evidence_status"],
        "live_promotion_status": "LIVE_BLOCKED",
        "next_commands": [
            "make.cmd dataset-quality",
            "make.cmd dataset-leakage-check",
            "make.cmd dataset-evidence-score",
            "make.cmd strategy-leaderboard",
        ],
    }
    _write_report(payload)
    return payload


def _write_report(payload: dict[str, Any]) -> None:
    EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True)
    (EVIDENCE_ROOT / "latest_research_evidence_report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8"
    )
    lines = [
        "# Research Evidence Report",
        "",
        "Dataset and strategy evidence report. Live promotion is blocked.",
        "",
        f"Dataset rows: {payload['dataset_manifest_summary']['rows']}",
        f"Quality: {payload['dataset_quality_summary']['status']}",
        f"Leakage: {payload['leakage_summary']['status']}",
        f"Evidence: {payload['evidence_score']['final_evidence_status']}",
        f"Live promotion: {payload['live_promotion_status']}",
        "",
        "## Blockers",
    ]
    lines.extend(f"- {blocker}" for blocker in payload["blockers"])
    lines.extend(["", "## Warnings"])
    lines.extend(f"- {warning}" for warning in (payload["warnings"] or ["None"]))
    lines.extend(["", "## Next Commands"])
    lines.extend(f"- `{command}`" for command in payload["next_commands"])
    (EVIDENCE_ROOT / "latest_research_evidence_report.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
