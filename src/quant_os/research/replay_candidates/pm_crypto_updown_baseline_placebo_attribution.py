from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.research.replay_candidates.pm_crypto_updown_policy_replay_eval import (
    MIN_ALLOWED_SHADOW_INTENTS,
)
from quant_os.research.replay_candidates.pm_crypto_updown_schema import CANDIDATE_ID
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

REPORT_ROOT = Path("reports/sequence44/baseline_placebo_attribution")
EPSILON = 1e-9


def evaluate_pm_crypto_updown_baseline_placebo_attribution(
    *,
    diagnostics: dict[str, Any],
) -> dict[str, Any]:
    baseline_metrics = diagnostics["baseline_metrics"]
    placebo_metrics = diagnostics["placebo_metrics"]
    candidate = baseline_metrics["candidate_metrics"]
    candidate_brier = candidate["brier_score"]
    baselines_blocking = _baselines_beating_or_tying(candidate_brier, baseline_metrics)
    placebos_blocking = _placebos_beating_or_tying(
        placebo_metrics.get("candidate_brier_score"),
        placebo_metrics,
    )
    candidate_beats_no_skill = baseline_metrics["candidate_beats_no_skill"]
    candidate_beats_market = baseline_metrics["candidate_beats_market_baseline"]
    candidate_beats_placebos = placebo_metrics["candidate_beats_placebos_for_readiness"]
    market_dominant = "market_probability" in baselines_blocking
    meaningful = (
        candidate_beats_placebos
        and float(diagnostics.get("placebo_similarity_score") or 1.0) > 0.01
    )
    active = (
        "BASELINE_OR_PLACEBO_BLOCKED"
        if baselines_blocking or placebos_blocking or not meaningful
        else "NONE"
    )
    additional = max(
        MIN_ALLOWED_SHADOW_INTENTS - int(diagnostics["allowed_primary_intent_count"]),
        0,
    )
    recommendation = _recommended_path(diagnostics, active)
    return {
        "schema_version": "pm_crypto_updown_baseline_placebo_attribution_v1",
        "sequence": "44",
        "candidate_id": CANDIDATE_ID,
        "active_blocker": active,
        "candidate_brier_score": candidate_brier,
        "candidate_log_loss": candidate["log_loss"],
        "baselines_beating_or_tying_candidate": baselines_blocking,
        "placebos_beating_or_tying_candidate": placebos_blocking,
        "candidate_beats_market_baseline": candidate_beats_market,
        "candidate_beats_no_skill_baseline": candidate_beats_no_skill,
        "candidate_beats_or_separates_from_placebos": meaningful,
        "candidate_meaningfully_different_from_placebo": meaningful,
        "market_baseline_dominant": market_dominant,
        "additional_allowed_primary_intents_required": additional,
        "candidate_needs_more_data_or_retirement": recommendation,
        "baseline_metrics": baseline_metrics,
        "placebo_metrics": placebo_metrics,
        "network_fetch_attempted": False,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_pm_crypto_updown_baseline_placebo_attribution_report(
    *,
    diagnostics: dict[str, Any],
    output_root: str | Path = ".",
) -> dict[str, Any]:
    payload = evaluate_pm_crypto_updown_baseline_placebo_attribution(
        diagnostics=diagnostics,
    )
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _baselines_beating_or_tying(
    candidate_brier: float | None,
    baseline_metrics: dict[str, Any],
) -> list[str]:
    if candidate_brier is None:
        return list(baseline_metrics["baselines"])
    blockers = []
    for name, metrics in baseline_metrics["baselines"].items():
        brier = metrics["brier_score"]
        if brier is not None and float(brier) <= float(candidate_brier) + EPSILON:
            blockers.append(name)
    return blockers


def _placebos_beating_or_tying(
    candidate_brier: float | None,
    placebo_metrics: dict[str, Any],
) -> list[str]:
    if candidate_brier is None:
        return [
            item["placebo_type"]
            for item in placebo_metrics["placebo_tests"]
            if item.get("skipped") is False
        ]
    blockers = []
    for item in placebo_metrics["placebo_tests"]:
        brier = item.get("brier_score")
        if (
            item.get("skipped") is False
            and brier is not None
            and float(brier) <= float(candidate_brier) + EPSILON
        ):
            blockers.append(item["placebo_type"])
    return blockers


def _recommended_path(diagnostics: dict[str, Any], active_blocker: str) -> str:
    if int(diagnostics["allowed_primary_intent_count"]) < MIN_ALLOWED_SHADOW_INTENTS:
        return "NEEDS_MORE_ALLOWED_INTENTS"
    if active_blocker == "BASELINE_OR_PLACEBO_BLOCKED":
        return "DEPRIORITIZE_CANDIDATE"
    return "CONTINUE_TO_SHADOW_REHEARSAL"


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_baseline_placebo_attribution.json"
    md_path = root / "latest_baseline_placebo_attribution.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 44 Baseline/Placebo Attribution",
        "",
        "Explains the active baseline/placebo blocker for allowed primary intents.",
        "",
        f"Active blocker: {payload['active_blocker']}",
        f"Market baseline dominant: {payload['market_baseline_dominant']}",
        f"Meaningfully different from placebo: {payload['candidate_meaningfully_different_from_placebo']}",
        f"Additional allowed primary intents required: {payload['additional_allowed_primary_intents_required']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        "",
        "## Baselines beating or tying candidate",
    ]
    lines.extend(f"- {item}" for item in payload["baselines_beating_or_tying_candidate"] or ["None"])
    lines.extend(["", "## Placebos beating or tying candidate"])
    lines.extend(f"- {item}" for item in payload["placebos_beating_or_tying_candidate"] or ["None"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
