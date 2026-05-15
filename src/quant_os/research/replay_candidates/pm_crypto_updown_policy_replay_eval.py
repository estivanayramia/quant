from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.execution.pm_crypto_updown_shadow_policy import (
    evaluate_pm_crypto_updown_shadow_policy,
)
from quant_os.research.replay_candidates.pm_crypto_updown_baselines import (
    evaluate_pm_crypto_updown_baselines,
)
from quant_os.research.replay_candidates.pm_crypto_updown_dataset_builder import (
    MIN_PRIMARY_REPLAY_READY_ROWS,
    build_pm_crypto_updown_expanded_dataset,
)
from quant_os.research.replay_candidates.pm_crypto_updown_fill_blocker_attribution import (
    evaluate_pm_crypto_updown_fill_blocker_attribution,
)
from quant_os.research.replay_candidates.pm_crypto_updown_fill_variants import (
    evaluate_pm_crypto_updown_fill_variants,
)
from quant_os.research.replay_candidates.pm_crypto_updown_placebos import (
    run_pm_crypto_updown_placebos,
)
from quant_os.research.replay_candidates.pm_crypto_updown_schema import CANDIDATE_ID
from quant_os.research.replay_candidates.pm_crypto_updown_signals import (
    is_replay_ready_row,
    score_pm_crypto_updown_signals,
)
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

REPORT_ROOT = Path("reports/sequence43/policy_replay_eval")
MIN_ALLOWED_SHADOW_INTENTS = 5


def evaluate_pm_crypto_updown_policy_replay(
    *,
    rows: list[dict[str, Any]] | None = None,
    signal_report: dict[str, Any] | None = None,
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
    report = signal_report or score_pm_crypto_updown_signals(rows)
    policy = evaluate_pm_crypto_updown_shadow_policy(rows=rows, signal_report=report)
    variants = evaluate_pm_crypto_updown_fill_variants(rows=rows, signal_report=report)
    attribution = evaluate_pm_crypto_updown_fill_blocker_attribution(
        rows=rows,
        signal_report=report,
    )
    primary_rows = _primary_rows(rows)
    real_cached_rows = [row for row in primary_rows if row.get("source_quality") == "real_cached"]
    fixture_rows = [row for row in primary_rows if row.get("source_quality") == "fixture_real_shaped"]
    synthetic_rows = [row for row in rows if row.get("source_quality") == "synthetic_stress"]
    allowed = [item for item in policy["intents"] if item["decision"] == "ALLOW_SHADOW_INTENT"]
    primary_allowed = [
        item for item in allowed if item.get("source_quality") in {"fixture_real_shaped", "real_cached"}
    ]
    synthetic_allowed = [
        item for item in allowed if item.get("source_quality") == "synthetic_stress"
    ]
    allowed_primary_row_ids = {item["row_id"] for item in primary_allowed}
    allowed_primary_rows = [
        row for row in rows if str(row["clob_snapshot_id"]) in allowed_primary_row_ids
    ]
    allowed_signal_report = _filter_signal_report(
        signal_report=report,
        allowed_rows=allowed_primary_rows,
    )
    baselines = evaluate_pm_crypto_updown_baselines(
        rows=allowed_primary_rows,
        signal_report=allowed_signal_report,
    )
    placebos = run_pm_crypto_updown_placebos(
        rows=allowed_primary_rows,
        signal_report=allowed_signal_report,
    )
    best = _best_conservative_variant(variants)
    sample_too_small = len(primary_allowed) < MIN_ALLOWED_SHADOW_INTENTS
    cost_fill_still_blocks = sample_too_small or best["cost_adjusted_result"] <= 0.0
    return {
        "schema_version": "pm_crypto_updown_policy_replay_eval_v1",
        "sequence": "43",
        "candidate_id": CANDIDATE_ID,
        "evaluation_status": (
            "POLICY_REPLAY_READY_FOR_READINESS_GATE"
            if allowed
            else "NO_CONSERVATIVE_INTENTS_ALLOWED"
        ),
        "minimum_primary_replay_ready_rows": MIN_PRIMARY_REPLAY_READY_ROWS,
        "minimum_allowed_shadow_intents": MIN_ALLOWED_SHADOW_INTENTS,
        "row_count": len(rows),
        "primary_evidence_row_count": len(primary_rows),
        "real_cached_replay_ready_row_count": len(real_cached_rows),
        "fixture_primary_row_count": len(fixture_rows),
        "synthetic_stress_row_count": len(synthetic_rows),
        "allowed_intent_count": len(allowed),
        "primary_allowed_intent_count": len(primary_allowed),
        "synthetic_allowed_intent_count": len(synthetic_allowed),
        "blocked_intent_count": policy["blocked_intent_count"],
        "does_any_conservative_policy_allow_nonzero_intents": any(
            item["allowed_intent_count"] > 0
            for item in variants["variants"]
            if item["assumption_classification"] == "CONSERVATIVE"
        ),
        "allowed_intents_beat_baselines": baselines["candidate_beats_market_baseline"]
        and baselines["candidate_beats_no_skill"],
        "allowed_intents_beat_placebos": placebos["candidate_beats_placebos_for_readiness"],
        "sample_still_too_small_after_filtering": sample_too_small,
        "synthetic_rows_counted_as_primary": False,
        "primary_vs_real_cached_vs_fixture_vs_synthetic_preserved": True,
        "source_separation": {
            "primary": len(primary_rows),
            "real_cached": len(real_cached_rows),
            "fixture": len(fixture_rows),
            "synthetic": len(synthetic_rows),
            "synthetic_counted_as_primary": False,
        },
        "policy_answers": {
            "any_conservative_policy_allows_nonzero_intents": bool(allowed),
            "allowed_intents_beat_baselines": baselines["candidate_beats_market_baseline"]
            and baselines["candidate_beats_no_skill"],
            "allowed_intents_beat_placebos": placebos["candidate_beats_placebos_for_readiness"],
            "cost_fill_realism_still_blocks": cost_fill_still_blocks,
            "sample_still_too_small_after_filtering": sample_too_small,
        },
        "shadow_policy": policy,
        "fill_blocker_attribution": attribution,
        "fill_variants": variants,
        "best_conservative_variant": best,
        "baseline_metrics": baselines,
        "placebo_metrics": placebos,
        "baseline_placebo_scope": "allowed_primary_shadow_intents_only",
        "dataset_report": dataset,
        "network_fetch_attempted": False,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_pm_crypto_updown_policy_replay_eval_report(
    *,
    rows: list[dict[str, Any]] | None = None,
    signal_report: dict[str, Any] | None = None,
    fixture_root: str | Path | None = None,
    real_cached_artifact_roots: list[str | Path] | None = None,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    payload = evaluate_pm_crypto_updown_policy_replay(
        rows=rows,
        signal_report=signal_report,
        fixture_root=fixture_root,
        real_cached_artifact_roots=real_cached_artifact_roots,
    )
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _primary_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if row.get("source_quality") in {"fixture_real_shaped", "real_cached"}
        and is_replay_ready_row(row)
        and row.get("label_status") == "RESOLVED"
        and row.get("resolved_outcome") is not None
    ]


def _filter_signal_report(
    *,
    signal_report: dict[str, Any],
    allowed_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    allowed_ids = {row["clob_snapshot_id"] for row in allowed_rows}
    decisions = [
        item for item in signal_report["row_decisions"] if item["row_id"] in allowed_ids
    ]
    return {
        **signal_report,
        "row_decisions": decisions,
        "candidate_signal_count": len([item for item in decisions if item["side"] == "BUY"]),
        "blocked_row_count": sum(1 for item in decisions if item.get("blocked")),
    }


def _best_conservative_variant(variants: dict[str, Any]) -> dict[str, Any]:
    conservative = [
        item
        for item in variants["variants"]
        if item["assumption_classification"] == "CONSERVATIVE"
    ]
    if not conservative:
        return {
            "variant_id": "NONE",
            "allowed_intent_count": 0,
            "cost_adjusted_result": 0.0,
            "can_promote_readiness": False,
        }
    return max(
        conservative,
        key=lambda item: (item["cost_adjusted_result"], item["allowed_intent_count"]),
    )


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_policy_replay_eval.json"
    md_path = root / "latest_policy_replay_eval.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 43 Policy Replay Evaluation",
        "",
        "Offline replay evaluation under conservative shadow policy. Synthetic rows remain diagnostic only.",
        "",
        f"Status: {payload['evaluation_status']}",
        f"Primary rows: {payload['primary_evidence_row_count']}",
        f"Real-cached rows: {payload['real_cached_replay_ready_row_count']}",
        f"Allowed intents: {payload['allowed_intent_count']}",
        f"Primary allowed intents: {payload['primary_allowed_intent_count']}",
        f"Synthetic rows counted as primary: {payload['synthetic_rows_counted_as_primary']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        "",
        "## Policy Answers",
    ]
    lines.extend(
        f"- {key}: {value}" for key, value in payload["policy_answers"].items()
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
