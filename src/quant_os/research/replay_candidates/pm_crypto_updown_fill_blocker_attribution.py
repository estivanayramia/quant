from __future__ import annotations

from collections import Counter
from typing import Any

from quant_os.execution.pm_crypto_updown_shadow_intents import (
    DEFAULT_PM_CRYPTO_UPDOWN_SHADOW_POLICY,
    PmCryptoUpdownShadowPolicyConfig,
    build_pm_crypto_updown_shadow_intents,
)
from quant_os.research.replay_candidates.pm_crypto_updown_schema import CANDIDATE_ID
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY


def evaluate_pm_crypto_updown_fill_blocker_attribution(
    *,
    rows: list[dict[str, Any]],
    signal_report: dict[str, Any] | None = None,
    config: PmCryptoUpdownShadowPolicyConfig = DEFAULT_PM_CRYPTO_UPDOWN_SHADOW_POLICY,
) -> dict[str, Any]:
    intents = build_pm_crypto_updown_shadow_intents(
        rows=rows,
        signal_report=signal_report,
        config=config,
    )
    blocked = [item for item in intents if item["decision"] == "BLOCK_SHADOW_INTENT"]
    potentially_tradeable = [
        item for item in intents if item["decision"] == "ALLOW_SHADOW_INTENT"
    ]
    primary_counts = Counter(item["blocker_reason"] for item in blocked)
    all_counts = Counter(
        blocker for item in blocked for blocker in item.get("blocker_reasons", [])
    )
    return {
        "schema_version": "pm_crypto_updown_fill_blocker_attribution_v1",
        "sequence": "43",
        "candidate_id": CANDIDATE_ID,
        "row_count": len(rows),
        "intent_count": len(intents),
        "blocked_row_count": len(blocked),
        "potentially_tradeable_row_count": len(potentially_tradeable),
        "blocked_counts_by_reason": dict(sorted(primary_counts.items())),
        "all_blocked_counts_by_reason": dict(sorted(all_counts.items())),
        "rows_blocked_by_spread": primary_counts["SPREAD_TOO_WIDE"],
        "rows_blocked_by_low_liquidity": primary_counts["LOW_LIQUIDITY"],
        "rows_blocked_by_stale_clob": primary_counts["STALE_CLOB"],
        "rows_blocked_by_latency_penalty": primary_counts["LATENCY_PENALTY_TOO_HIGH"],
        "rows_blocked_by_no_fill_probability": primary_counts[
            "NO_FILL_PROBABILITY_TOO_HIGH"
        ],
        "rows_blocked_by_partial_fill_rules": primary_counts["PARTIAL_FILL_TOO_SMALL"],
        "rows_blocked_by_time_to_window_end": primary_counts["TOO_CLOSE_TO_WINDOW_END"],
        "rows_blocked_by_price_discipline": primary_counts["PRICE_DISCIPLINE_FAILED"],
        "rows_still_potentially_tradeable_under_conservative_assumptions": len(
            potentially_tradeable
        ),
        "potentially_tradeable_intents": potentially_tradeable,
        "blocked_intents": blocked,
        "network_fetch_attempted": False,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }
