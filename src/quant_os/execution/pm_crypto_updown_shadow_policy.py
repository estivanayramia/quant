from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.execution.pm_crypto_updown_shadow_intents import (
    DEFAULT_PM_CRYPTO_UPDOWN_SHADOW_POLICY,
    PmCryptoUpdownShadowPolicyConfig,
    build_pm_crypto_updown_shadow_intents,
)
from quant_os.research.replay_candidates.pm_crypto_updown_schema import CANDIDATE_ID
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

REPORT_ROOT = Path("reports/sequence43/shadow_policy")


def evaluate_pm_crypto_updown_shadow_policy(
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
    allowed = [item for item in intents if item["decision"] == "ALLOW_SHADOW_INTENT"]
    blocked = [item for item in intents if item["decision"] == "BLOCK_SHADOW_INTENT"]
    return {
        "schema_version": "pm_crypto_updown_shadow_policy_v1",
        "sequence": "43",
        "candidate_id": CANDIDATE_ID,
        "policy_scope": "OFFLINE_HYPOTHETICAL_INTENTS_ONLY",
        "intents": intents,
        "intent_count": len(intents),
        "allowed_intent_count": len(allowed),
        "blocked_intent_count": len(blocked),
        "zero_trade_outcome_preferred_over_weak_trades": True,
        "order_routing_enabled": False,
        "order_signing_enabled": False,
        "order_cancellation_enabled": False,
        "wallet_signing_enabled": False,
        "assumptions": {
            "max_spread": config.max_spread,
            "min_liquidity": config.min_liquidity,
            "max_stale_book_age_seconds": config.max_stale_book_age_seconds,
            "max_latency_penalty": config.max_latency_penalty,
            "minimum_spot_lag_confidence": config.min_spot_lag_confidence,
            "minimum_expected_edge_after_cost": config.min_expected_edge_after_cost,
            "minimum_time_to_window_end": config.min_time_to_window_end_seconds,
            "limit_price_discipline": "cap limit price at max acceptable price after fees, latency, and spread",
            "reject_market_crossing_if_cost_burden_is_too_high": True,
            "no_fill_allowed": True,
            "partial_fill_allowed": True,
        },
        "network_fetch_attempted": False,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_pm_crypto_updown_shadow_policy_report(
    *,
    rows: list[dict[str, Any]],
    signal_report: dict[str, Any] | None = None,
    output_root: str | Path = ".",
    config: PmCryptoUpdownShadowPolicyConfig = DEFAULT_PM_CRYPTO_UPDOWN_SHADOW_POLICY,
) -> dict[str, Any]:
    payload = evaluate_pm_crypto_updown_shadow_policy(
        rows=rows,
        signal_report=signal_report,
        config=config,
    )
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_pm_crypto_updown_shadow_policy.json"
    md_path = root / "latest_pm_crypto_updown_shadow_policy.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 43 PM Crypto UP/DOWN Shadow Policy",
        "",
        "Offline hypothetical intent policy only. No routing, signing, cancellation, wallet, or live authority.",
        "",
        f"Allowed intents: {payload['allowed_intent_count']}",
        f"Blocked intents: {payload['blocked_intent_count']}",
        f"Execution authority: {payload['execution_authority']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        "",
        "## Blocked Reasons",
    ]
    blocked = [item for item in payload["intents"] if item["decision"] == "BLOCK_SHADOW_INTENT"]
    if not blocked:
        lines.append("- None")
    else:
        lines.extend(f"- {item['market_id']}: {item['blocker_reason']}" for item in blocked)
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
