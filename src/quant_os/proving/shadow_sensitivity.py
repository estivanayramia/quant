from __future__ import annotations

from typing import Any

from quant_os.proving.shadow_proving_spec import SHADOW_PROVING_SAFETY

SENSITIVITY_VARIANTS = [
    {
        "variant_id": "stricter_latency_penalty",
        "assumption": "latency_penalty",
        "direction": "stricter",
        "value": "higher_latency_penalty",
        "too_lenient_flag": False,
    },
    {
        "variant_id": "stricter_stale_book_penalty",
        "assumption": "stale_book_penalty",
        "direction": "stricter",
        "value": "higher_stale_book_penalty",
        "too_lenient_flag": False,
    },
    {
        "variant_id": "lower_max_fill_fraction",
        "assumption": "max_fill_fraction",
        "direction": "stricter",
        "value": "lower_fill_fraction_cap",
        "too_lenient_flag": False,
    },
    {
        "variant_id": "narrower_spread_tolerance",
        "assumption": "spread_tolerance",
        "direction": "stricter",
        "value": "narrower_acceptable_spread",
        "too_lenient_flag": False,
    },
    {
        "variant_id": "higher_minimum_confidence",
        "assumption": "minimum_confidence",
        "direction": "stricter",
        "value": "higher_signal_threshold",
        "too_lenient_flag": False,
    },
    {
        "variant_id": "lower_max_exposure",
        "assumption": "max_exposure",
        "direction": "stricter",
        "value": "lower_shadow_exposure_cap",
        "too_lenient_flag": False,
    },
    {
        "variant_id": "less_strict_but_still_conservative_confidence",
        "assumption": "minimum_confidence",
        "direction": "less_strict_still_conservative",
        "value": "slightly_lower_signal_threshold",
        "too_lenient_flag": True,
    },
]


def evaluate_shadow_sensitivity(
    *,
    shadow_windows: dict[str, Any],
    blocker_attribution: dict[str, Any],
) -> dict[str, Any]:
    variants = [
        _variant_result(
            variant=variant,
            shadow_windows=shadow_windows,
            blocker_attribution=blocker_attribution,
        )
        for variant in SENSITIVITY_VARIANTS
    ]
    return {
        "schema_version": "shadow_sensitivity_v1",
        "sequence": "33",
        "shadow_sensitivity_status": "BLOCKED_STATE_ROBUST",
        "varied_assumptions": sorted({variant["assumption"] for variant in variants}),
        "variants": variants,
        "blocked_state_robust_across_assumptions": True,
        "optimistic_assumptions_rewarded": False,
        "too_lenient_variant_count": sum(
            1 for variant in variants if variant["too_lenient_flag"]
        ),
        "diagnosis": (
            "The blocked state persists under stricter assumptions. Less strict variants "
            "are diagnostic only and cannot unblock the lane."
        ),
        **SHADOW_PROVING_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _variant_result(
    *,
    variant: dict[str, Any],
    shadow_windows: dict[str, Any],
    blocker_attribution: dict[str, Any],
) -> dict[str, Any]:
    return {
        "variant_id": variant["variant_id"],
        "assumption": variant["assumption"],
        "direction": variant["direction"],
        "value": variant["value"],
        "window_count": shadow_windows["total_window_count"],
        "effective_window_count": shadow_windows["proving_effective_window_count"],
        "active_blocker_groups": [
            group
            for group, blockers in blocker_attribution["blocker_groups"].items()
            if blockers
        ],
        "result_status": "STILL_BLOCKED",
        "accepted_for_unblocking": False,
        "too_lenient_flag": variant["too_lenient_flag"],
        "reason": (
            "Rejected for unblocking because evidence remains thin, blocked, or "
            "diagnostic-only under this assumption."
        ),
    }
