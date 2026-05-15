from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from quant_os.execution.pm_crypto_updown_shadow_policy import (
    evaluate_pm_crypto_updown_shadow_policy,
)
from quant_os.research.replay_candidates.pm_crypto_updown_baselines import (
    MIN_CONFIDENT_SAMPLE_ROWS,
    evaluate_pm_crypto_updown_baselines,
)
from quant_os.research.replay_candidates.pm_crypto_updown_dataset_builder import (
    MIN_PRIMARY_REPLAY_READY_ROWS,
    build_pm_crypto_updown_expanded_dataset,
)
from quant_os.research.replay_candidates.pm_crypto_updown_placebos import (
    run_pm_crypto_updown_placebos,
)
from quant_os.research.replay_candidates.pm_crypto_updown_policy_replay_eval import (
    MIN_ALLOWED_SHADOW_INTENTS,
    evaluate_pm_crypto_updown_policy_replay,
)
from quant_os.research.replay_candidates.pm_crypto_updown_schema import CANDIDATE_ID
from quant_os.research.replay_candidates.pm_crypto_updown_signals import (
    score_pm_crypto_updown_signals,
)
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

PRIMARY_SOURCE_QUALITIES = {"fixture_real_shaped", "real_cached"}


def evaluate_pm_crypto_updown_allowed_intent_diagnostics(
    *,
    rows: list[dict[str, Any]] | None = None,
    signal_report: dict[str, Any] | None = None,
    policy_replay_eval: dict[str, Any] | None = None,
    fixture_root: str | Path | None = None,
    real_cached_artifact_roots: list[str | Path] | None = None,
) -> dict[str, Any]:
    dataset = None
    if rows is None:
        dataset = build_pm_crypto_updown_expanded_dataset(
            fixture_root=fixture_root or Path("tests/fixtures/replay_candidates/pm_crypto_updown"),
            real_cached_artifact_roots=real_cached_artifact_roots,
        )
        rows = dataset["rows"]
    signals = signal_report or score_pm_crypto_updown_signals(rows)
    policy_eval = policy_replay_eval or evaluate_pm_crypto_updown_policy_replay(
        rows=rows,
        signal_report=signals,
        fixture_root=fixture_root,
        real_cached_artifact_roots=real_cached_artifact_roots,
    )
    shadow_policy = policy_eval.get("shadow_policy") or evaluate_pm_crypto_updown_shadow_policy(
        rows=rows,
        signal_report=signals,
    )
    allowed = [
        intent
        for intent in shadow_policy["intents"]
        if intent["decision"] == "ALLOW_SHADOW_INTENT"
    ]
    allowed_primary = [
        intent for intent in allowed if intent.get("source_quality") in PRIMARY_SOURCE_QUALITIES
    ]
    allowed_real_cached = [
        intent for intent in allowed_primary if intent.get("source_quality") == "real_cached"
    ]
    allowed_synthetic = [
        intent for intent in allowed if intent.get("source_quality") == "synthetic_stress"
    ]
    rows_by_id = {str(row["clob_snapshot_id"]): row for row in rows}
    allowed_primary_rows = [
        rows_by_id[str(intent["row_id"])]
        for intent in allowed_primary
        if str(intent["row_id"]) in rows_by_id
    ]
    allowed_primary_signal_report = _filter_signal_report(
        signal_report=signals,
        allowed_row_ids=[row["clob_snapshot_id"] for row in allowed_primary_rows],
    )
    baselines = evaluate_pm_crypto_updown_baselines(
        rows=allowed_primary_rows,
        signal_report=allowed_primary_signal_report,
    )
    placebos = run_pm_crypto_updown_placebos(
        rows=allowed_primary_rows,
        signal_report=allowed_primary_signal_report,
    )
    best_variant = policy_eval.get("best_conservative_variant", {})
    cost_fill_adjusted = float(best_variant.get("cost_adjusted_result") or 0.0)
    placebo_similarity_score = _placebo_similarity_score(placebos)
    causes = _blocker_causes(
        allowed_primary_rows=allowed_primary_rows,
        allowed_primary=allowed_primary,
        allowed_real_cached=allowed_real_cached,
        baselines=baselines,
        placebos=placebos,
        cost_fill_adjusted=cost_fill_adjusted,
        placebo_similarity_score=placebo_similarity_score,
    )
    active_blocker = (
        "BASELINE_OR_PLACEBO_BLOCKED"
        if causes["baseline_dominance"] or causes["placebo_similarity"]
        else "NONE"
    )
    return {
        "schema_version": "pm_crypto_updown_allowed_intent_diagnostics_v1",
        "sequence": "44",
        "candidate_id": CANDIDATE_ID,
        "minimum_primary_replay_ready_rows": MIN_PRIMARY_REPLAY_READY_ROWS,
        "minimum_allowed_shadow_intents": MIN_ALLOWED_SHADOW_INTENTS,
        "minimum_confident_sample_rows": MIN_CONFIDENT_SAMPLE_ROWS,
        "row_count": len(rows),
        "primary_evidence_row_count": policy_eval["primary_evidence_row_count"],
        "real_cached_replay_ready_row_count": policy_eval[
            "real_cached_replay_ready_row_count"
        ],
        "allowed_intent_count": len(allowed),
        "allowed_primary_intent_count": len(allowed_primary),
        "allowed_real_cached_intent_count": len(allowed_real_cached),
        "allowed_synthetic_diagnostic_intent_count": len(allowed_synthetic),
        "primary_claim_row_count": len(allowed_primary_rows),
        "allowed_primary_row_ids": [row["clob_snapshot_id"] for row in allowed_primary_rows],
        "allowed_real_cached_row_ids": [intent["row_id"] for intent in allowed_real_cached],
        "allowed_synthetic_diagnostic_row_ids": [intent["row_id"] for intent in allowed_synthetic],
        "allowed_primary_rows": allowed_primary_rows,
        "allowed_primary_signal_report": allowed_primary_signal_report,
        "outcome_distribution": dict(
            sorted(Counter(row["outcome"] for row in allowed_primary_rows).items())
        ),
        "label_distribution": dict(
            sorted(Counter(row["resolved_outcome"] for row in allowed_primary_rows).items())
        ),
        "signal_distribution": _signal_distribution(allowed_primary_signal_report),
        "market_baseline_distribution": _market_distribution(allowed_primary_rows),
        "placebo_distribution": _placebo_distribution(placebos),
        "cost_fill_adjusted_result": round(cost_fill_adjusted, 6),
        "per_intent_reasons": _per_intent_reasons(
            allowed_primary=allowed_primary,
            rows_by_id=rows_by_id,
            signal_report=allowed_primary_signal_report,
        ),
        "baseline_metrics": baselines,
        "placebo_metrics": placebos,
        "baseline_placebo_scope": "allowed_primary_shadow_intents_only",
        "baseline_placebo_blocker_active": active_blocker == "BASELINE_OR_PLACEBO_BLOCKED",
        "active_blocker": active_blocker,
        "blocker_causes": causes,
        "placebo_similarity_score": round(placebo_similarity_score, 6),
        "one_row_dominance_share": round(_one_row_dominance_share(allowed_primary), 6),
        "synthetic_rows_counted_as_primary": False,
        "does_any_conservative_policy_allow_nonzero_intents": bool(allowed),
        "network_fetch_attempted": False,
        "dataset_report": dataset,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _filter_signal_report(
    *,
    signal_report: dict[str, Any],
    allowed_row_ids: list[str],
) -> dict[str, Any]:
    allowed = set(allowed_row_ids)
    decisions = [
        item for item in signal_report["row_decisions"] if str(item["row_id"]) in allowed
    ]
    return {
        **signal_report,
        "row_decisions": decisions,
        "candidate_signal_count": len([item for item in decisions if item["side"] == "BUY"]),
        "blocked_row_count": sum(1 for item in decisions if item.get("blocked")),
    }


def _blocker_causes(
    *,
    allowed_primary_rows: list[dict[str, Any]],
    allowed_primary: list[dict[str, Any]],
    allowed_real_cached: list[dict[str, Any]],
    baselines: dict[str, Any],
    placebos: dict[str, Any],
    cost_fill_adjusted: float,
    placebo_similarity_score: float,
) -> dict[str, bool]:
    return {
        "too_few_allowed_intents": len(allowed_primary) < MIN_ALLOWED_SHADOW_INTENTS,
        "weak_signal_discrimination": not baselines["candidate_beats_no_skill"],
        "placebo_similarity": (
            not placebos["candidate_beats_placebos_for_readiness"]
            or placebo_similarity_score <= 0.01
        ),
        "baseline_dominance": not baselines["candidate_beats_market_baseline"],
        "label_imbalance": _label_imbalance(allowed_primary_rows),
        "cost_fill_erosion": cost_fill_adjusted <= 0.0,
        "data_quality_caveats": len(allowed_real_cached) < 3,
    }


def _signal_distribution(signal_report: dict[str, Any]) -> dict[str, Any]:
    decisions = signal_report["row_decisions"]
    strengths = [float(item.get("signal_strength") or 0.0) for item in decisions]
    probabilities = [float(item.get("predicted_probability") or 0.0) for item in decisions]
    return {
        "side_counts": dict(sorted(Counter(item["side"] for item in decisions).items())),
        "min_signal_strength": min(strengths) if strengths else None,
        "max_signal_strength": max(strengths) if strengths else None,
        "min_predicted_probability": min(probabilities) if probabilities else None,
        "max_predicted_probability": max(probabilities) if probabilities else None,
    }


def _market_distribution(rows: list[dict[str, Any]]) -> dict[str, Any]:
    mids = [float(row["market_mid"]) for row in rows]
    asks = [float(row["market_ask"]) for row in rows]
    return {
        "row_count": len(rows),
        "min_market_mid": min(mids) if mids else None,
        "max_market_mid": max(mids) if mids else None,
        "min_market_ask": min(asks) if asks else None,
        "max_market_ask": max(asks) if asks else None,
    }


def _placebo_distribution(placebos: dict[str, Any]) -> dict[str, Any]:
    tests = placebos["placebo_tests"]
    return {
        "comparison_status": placebos["placebo_comparison_status"],
        "candidate_brier_score": placebos["candidate_brier_score"],
        "placebo_brier_scores": {
            item["placebo_type"]: item["brier_score"]
            for item in tests
            if item.get("brier_score") is not None
        },
    }


def _per_intent_reasons(
    *,
    allowed_primary: list[dict[str, Any]],
    rows_by_id: dict[str, dict[str, Any]],
    signal_report: dict[str, Any],
) -> list[dict[str, Any]]:
    decisions = {str(item["row_id"]): item for item in signal_report["row_decisions"]}
    reasons = []
    for intent in allowed_primary:
        row = rows_by_id[str(intent["row_id"])]
        decision = decisions[str(intent["row_id"])]
        reasons.append(
            {
                "row_id": intent["row_id"],
                "source_quality": intent.get("source_quality"),
                "outcome": row["outcome"],
                "resolved_outcome": row["resolved_outcome"],
                "predicted_probability": decision["predicted_probability"],
                "market_mid": row["market_mid"],
                "expected_edge_after_cost": intent["expected_edge_after_cost"],
                "reason": "Allowed by Phase 43 fill policy; Phase 44 treats it as diagnostic evidence only.",
            }
        )
    return reasons


def _placebo_similarity_score(placebos: dict[str, Any]) -> float:
    candidate = placebos.get("candidate_brier_score")
    scores = [
        item["brier_score"]
        for item in placebos.get("placebo_tests", [])
        if item.get("brier_score") is not None and item.get("skipped") is False
    ]
    if candidate is None or not scores:
        return 1.0
    return min(abs(float(candidate) - float(score)) for score in scores)


def _one_row_dominance_share(allowed_primary: list[dict[str, Any]]) -> float:
    values = [
        abs(float(item["expected_edge_after_cost"]) * float(item["partial_fill_ratio"]))
        for item in allowed_primary
    ]
    total = sum(values)
    if total <= 0.0:
        return 1.0 if values else 0.0
    return max(values) / total


def _label_imbalance(rows: list[dict[str, Any]]) -> bool:
    if len(rows) < MIN_ALLOWED_SHADOW_INTENTS:
        return True
    counts = Counter(row["resolved_outcome"] for row in rows)
    if len(counts) <= 1:
        return True
    return max(counts.values()) / len(rows) >= 0.8
