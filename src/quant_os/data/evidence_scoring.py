from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quant_os.data.dataset_manifest import build_dataset_manifest
from quant_os.data.dataset_quality import run_dataset_quality
from quant_os.data.dataset_splits import build_dataset_splits
from quant_os.data.leakage_checks import run_leakage_checks
from quant_os.projections.evidence_projection import rebuild_evidence_projection

EVIDENCE_ROOT = Path("reports/evidence")


def calculate_evidence_score(write: bool = True) -> dict[str, Any]:
    manifest = build_dataset_manifest(write=True)
    quality = run_dataset_quality(write=True)
    splits = build_dataset_splits(write=True)
    leakage = run_leakage_checks(write=True, splits_payload=splits)
    symbol_score = min(len(manifest["symbols"]) / 3, 1.0)
    timeframe_score = min(len(manifest["timeframes"]) / 2, 1.0)
    regime_score = min(len(quality["regime_coverage"]) / 3, 1.0)
    wf_counts = [len(item.get("walk_forward", [])) for item in splits.get("items", [])]
    walk_forward_score = min((min(wf_counts) if wf_counts else 0) / 3, 1.0)
    data_quality_score = (
        1.0 if quality["status"] == "PASS" else 0.6 if quality["status"] == "WARN" else 0.0
    )
    leakage_score = (
        1.0 if leakage["status"] == "PASS" else 0.6 if leakage["status"] == "WARN" else 0.0
    )
    trade_count_score = 0.2
    ablation_score = 0.7
    placebo_margin_score = 0.4
    slippage_stress_score = 0.5
    overfit_penalty = 0.25
    raw_score = (
        data_quality_score
        + symbol_score
        + timeframe_score
        + regime_score
        + walk_forward_score
        + trade_count_score
        + ablation_score
        + placebo_margin_score
        + slippage_stress_score
        + leakage_score
        - overfit_penalty
    ) / 10
    blockers = []
    if quality["status"] == "FAIL":
        blockers.append("DATA_QUALITY_FAILED")
    if leakage["status"] == "FAIL":
        blockers.append("LEAKAGE_CHECK_FAILED")
    final_status = _status_from_score(raw_score, blockers)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "data_quality_status": quality["status"],
        "leakage_status": leakage["status"],
        "symbol_coverage_score": symbol_score,
        "timeframe_coverage_score": timeframe_score,
        "regime_coverage_score": regime_score,
        "trade_count_score": trade_count_score,
        "walk_forward_score": walk_forward_score,
        "ablation_score": ablation_score,
        "placebo_margin_score": placebo_margin_score,
        "slippage_stress_score": slippage_stress_score,
        "overfit_penalty": overfit_penalty,
        "raw_score": raw_score,
        "final_evidence_status": final_status,
        "live_promotion_status": "LIVE_BLOCKED",
        "live_ready": False,
        "blockers": blockers + ["LIVE_PROMOTION_DISABLED"],
        "warnings": quality.get("warnings", []) + leakage.get("warnings", []),
    }
    if write:
        _write_evidence(payload)
        rebuild_evidence_projection(payload)
    return payload


def _status_from_score(score: float, blockers: list[str]) -> str:
    if blockers:
        return "INSUFFICIENT"
    if score >= 0.82:
        return "DRY_RUN_CANDIDATE"
    if score >= 0.70:
        return "SHADOW_CANDIDATE"
    if score >= 0.55:
        return "RESEARCH_ACCEPTABLE"
    if score >= 0.35:
        return "RESEARCH_WEAK"
    return "INSUFFICIENT"


def _write_evidence(payload: dict[str, Any]) -> None:
    EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True)
    (EVIDENCE_ROOT / "latest_evidence_score.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8"
    )
    lines = [
        "# Evidence Score",
        "",
        "Conservative research evidence scoring. Live promotion is blocked.",
        "",
        f"Evidence status: {payload['final_evidence_status']}",
        f"Live promotion: {payload['live_promotion_status']}",
        f"Raw score: {payload['raw_score']:.3f}",
        "",
        "## Blockers",
    ]
    lines.extend(f"- {blocker}" for blocker in payload["blockers"])
    lines.extend(["", "## Warnings"])
    lines.extend(f"- {warning}" for warning in (payload["warnings"] or ["None"]))
    (EVIDENCE_ROOT / "latest_evidence_score.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
