from __future__ import annotations

from typing import Any

from quant_os.proving.shadow_proving_spec import SHADOW_PROVING_SAFETY

STRESS_VARIANTS = [
    {
        "window_id": "stress_latency_penalty",
        "source_id": "synthetic_stress_latency_penalty_v1",
        "assumption_changes": {
            "latency_penalty": "stricter",
            "stale_book_penalty": "unchanged",
            "max_fill_fraction": "unchanged",
            "spread_tolerance": "unchanged",
            "minimum_confidence": "unchanged",
            "risk_limits": "unchanged",
        },
    },
    {
        "window_id": "stress_stale_book_penalty",
        "source_id": "synthetic_stress_stale_book_penalty_v1",
        "assumption_changes": {
            "latency_penalty": "unchanged",
            "stale_book_penalty": "stricter",
            "max_fill_fraction": "unchanged",
            "spread_tolerance": "unchanged",
            "minimum_confidence": "unchanged",
            "risk_limits": "unchanged",
        },
    },
    {
        "window_id": "stress_low_fill_fraction",
        "source_id": "synthetic_stress_low_fill_fraction_v1",
        "assumption_changes": {
            "latency_penalty": "unchanged",
            "stale_book_penalty": "unchanged",
            "max_fill_fraction": "stricter",
            "spread_tolerance": "unchanged",
            "minimum_confidence": "unchanged",
            "risk_limits": "unchanged",
        },
    },
    {
        "window_id": "stress_strict_signal_and_spread",
        "source_id": "synthetic_stress_strict_signal_and_spread_v1",
        "assumption_changes": {
            "latency_penalty": "unchanged",
            "stale_book_penalty": "unchanged",
            "max_fill_fraction": "unchanged",
            "spread_tolerance": "stricter",
            "minimum_confidence": "stricter",
            "risk_limits": "unchanged",
        },
    },
]


def build_shadow_sample_windows(
    *,
    shadow_execution: dict[str, Any],
    shadow_proving: dict[str, Any],
) -> dict[str, Any]:
    windows = [_fixture_window(shadow_execution=shadow_execution, shadow_proving=shadow_proving)]
    windows.extend(
        _synthetic_window(index=index, variant=variant, shadow_execution=shadow_execution)
        for index, variant in enumerate(STRESS_VARIANTS, start=1)
    )
    counts = _evidence_class_counts(windows)
    effective_count = sum(1 for window in windows if window["counts_for_proving_thresholds"])
    return {
        "schema_version": "shadow_sample_windows_v1",
        "sequence": "33",
        "shadow_sample_status": "SYNTHETIC_STRESS_EXPANDED_NOT_PROOF",
        "total_window_count": len(windows),
        "proving_effective_window_count": effective_count,
        "synthetic_window_count": counts["synthetic_stress"],
        "evidence_class_counts": counts,
        "windows": windows,
        "provenance_policy": {
            "fixture_evidence": "Fixture-safe replay output from Phase 31/32 reports.",
            "real_cached_evidence": "Only counted when sourced from real cached activity manifests.",
            "synthetic_stress": "Stress-test only; never treated as proof of edge or profitability.",
        },
        "sample_inflation_guard": (
            "Synthetic stress windows are useful for blocker diagnosis but do not increase "
            "the proving-effective evidence count."
        ),
        **SHADOW_PROVING_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _fixture_window(
    *,
    shadow_execution: dict[str, Any],
    shadow_proving: dict[str, Any],
) -> dict[str, Any]:
    return {
        "window_id": "fixture_phase31_shadow_execution",
        "window_index": 0,
        "evidence_class": "fixture_evidence",
        "counts_for_proving_thresholds": True,
        "profitability_evidence": False,
        "selected_lane_id": shadow_execution["selected_lane_id"],
        "shadow_execution_status": shadow_execution["shadow_execution_status"],
        "shadow_proving_status": shadow_proving["shadow_proving_status"],
        "metrics": shadow_execution["metrics"],
        "blockers": shadow_execution["blockers"],
        "proving_blockers": shadow_proving["blockers"],
        "provenance": {
            "source_id": "phase31_shadow_execution_fixture_report",
            "snapshot_id": "benchmark_fixture_bundle",
            "source_quality": "fixture_safe",
            "synthetic": False,
        },
        "assumption_changes": {
            "latency_penalty": "base",
            "stale_book_penalty": "base",
            "max_fill_fraction": "base",
            "spread_tolerance": "base",
            "minimum_confidence": "base",
            "risk_limits": "base",
        },
        "diagnostic_conclusion": "Base fixture window remains blocked and is not edge evidence.",
    }


def _synthetic_window(
    *,
    index: int,
    variant: dict[str, Any],
    shadow_execution: dict[str, Any],
) -> dict[str, Any]:
    return {
        "window_id": variant["window_id"],
        "window_index": index,
        "evidence_class": "synthetic_stress",
        "counts_for_proving_thresholds": False,
        "profitability_evidence": False,
        "selected_lane_id": shadow_execution["selected_lane_id"],
        "shadow_execution_status": "SHADOW_EXECUTION_NOT_JUSTIFIED",
        "metrics": _stress_metrics(shadow_execution["metrics"]),
        "blockers": _dedupe(
            [
                *shadow_execution["blockers"],
                "SYNTHETIC_STRESS_NOT_EDGE_EVIDENCE",
            ]
        ),
        "provenance": {
            "source_id": variant["source_id"],
            "snapshot_id": "synthetic_stress_window",
            "source_quality": "synthetic_stress",
            "synthetic": True,
        },
        "assumption_changes": variant["assumption_changes"],
        "diagnostic_conclusion": (
            "Synthetic stress window preserves the blocked state and diagnoses "
            "assumption sensitivity only."
        ),
    }


def _stress_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    stressed = dict(metrics)
    stressed["fill_rate"] = "0"
    stressed["no_fill_rate"] = "1"
    stressed["expectancy_under_conservative_assumptions"] = "not_estimated_stress_window"
    return stressed


def _evidence_class_counts(windows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "real_cached_evidence": 0,
        "fixture_evidence": 0,
        "synthetic_stress": 0,
    }
    for window in windows:
        counts[window["evidence_class"]] += 1
    return counts


def _dedupe(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
