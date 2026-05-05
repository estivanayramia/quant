from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPORT_ROOT = Path("reports/sequence23/prediction_candidates")
SIGNAL_FAMILY_SAFETY = {
    "execution_authority": "NONE",
    "wallet_signing_enabled": False,
    "live_trading_enabled": False,
    "copy_trading_enabled": False,
    "real_orders_enabled": False,
}

SIGNAL_FAMILIES = [
    {
        "signal_family_id": "late_stabilization",
        "name": "Late-Market Stabilization",
        "probability_key": "late_stabilization_probability",
        "plain_english_explanation": "Checks whether a near-resolution market is stable enough to trust the market baseline.",
        "feature_list": ["current_market_probability", "recent_price_drift", "time_to_resolution_hours"],
        "why_it_might_work": "Late markets may contain fresher public information and clearer resolution context.",
        "why_it_might_fail": "The market baseline may already incorporate that information.",
        "failure_mode_notes": [
            "Late stability can be crowd consensus without predictive edge.",
            "Near-close markets may also be affected by liquidity gaps.",
        ],
        "opaque_model": False,
    },
    {
        "signal_family_id": "drift_reversal",
        "name": "Price Drift Reversal",
        "probability_key": "drift_reversal_probability",
        "plain_english_explanation": "Shrinks strong one-way price drift back toward 50/50 as a reversal hypothesis.",
        "feature_list": ["price_drift_from_open", "recent_price_drift", "current_market_probability"],
        "why_it_might_work": "Some markets may overshoot after narrative-driven moves.",
        "why_it_might_fail": "Price drift can be justified information discovery, not overreaction.",
        "failure_mode_notes": [
            "Reversal assumptions are fragile on small samples.",
            "This family must beat the market baseline before replay is justified.",
        ],
        "opaque_model": False,
    },
    {
        "signal_family_id": "concentration_adjusted",
        "name": "Wallet Concentration Adjustment",
        "probability_key": "concentration_adjusted_probability",
        "plain_english_explanation": "Shrinks probabilities when wallet concentration is elevated.",
        "feature_list": ["wallet_concentration", "current_market_probability"],
        "why_it_might_work": "Extreme concentration can be a manipulation or crowding warning.",
        "why_it_might_fail": "Concentrated positions may belong to informed participants rather than manipulators.",
        "failure_mode_notes": [
            "This is not wallet mirroring.",
            "Wallet concentration is heuristic context, not execution authority.",
        ],
        "opaque_model": False,
    },
    {
        "signal_family_id": "liquidity_quality",
        "name": "Liquidity Quality Adjustment",
        "probability_key": "liquidity_quality_probability",
        "plain_english_explanation": "Shrinks probabilities in thinner markets where price quality may be lower.",
        "feature_list": ["liquidity", "volume", "thinness_penalty", "current_market_probability"],
        "why_it_might_work": "Lower-liquidity markets may have noisier prices and weaker baselines.",
        "why_it_might_fail": "Shrinking can discard real information in small but well-informed markets.",
        "failure_mode_notes": [
            "Thinness penalties must not become execution filters by themselves.",
            "The adjustment is deterministic and research-only.",
        ],
        "opaque_model": False,
    },
]


def apply_signal_families(features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched = []
    for feature in features:
        item = dict(feature)
        current = float(item["current_market_probability"])
        item["late_stabilization_probability"] = _late_stabilization_probability(item, current)
        item["drift_reversal_probability"] = _shrink_probability(current, factor=0.85)
        item["concentration_adjusted_probability"] = _concentration_adjusted_probability(item, current)
        item["liquidity_quality_probability"] = _liquidity_quality_probability(item, current)
        enriched.append(item)
    return sorted(enriched, key=lambda row: row["market_id"])


def write_signal_family_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = {
        "sequence": "23",
        "source": "polymarket",
        "signal_family_count": len(SIGNAL_FAMILIES),
        "signal_families": SIGNAL_FAMILIES,
        "observed_facts": [
            "Signal families are deterministic, interpretable, and falsifiable.",
        ],
        "inferred_patterns": [
            "These signal families are hypotheses for lane evaluation, not trading instructions.",
        ],
        "unknowns": [
            "No signal family should be trusted unless it beats required baselines in lane-level tests.",
        ],
        **SIGNAL_FAMILY_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _late_stabilization_probability(feature: dict[str, Any], current: float) -> float:
    if feature["nearing_close"] and abs(float(feature["recent_price_drift"])) <= 0.04:
        return round(current, 6)
    return _shrink_probability(current, factor=0.9)


def _concentration_adjusted_probability(feature: dict[str, Any], current: float) -> float:
    concentration = float(feature["wallet_concentration"])
    if concentration >= 0.55:
        return _shrink_probability(current, factor=0.75)
    if concentration >= 0.45:
        return _shrink_probability(current, factor=0.9)
    return round(current, 6)


def _liquidity_quality_probability(feature: dict[str, Any], current: float) -> float:
    liquidity = float(feature["liquidity"])
    if liquidity < 10_000.0:
        return _shrink_probability(current, factor=0.75)
    if liquidity < 30_000.0:
        return _shrink_probability(current, factor=0.9)
    return round(current, 6)


def _shrink_probability(probability: float, *, factor: float) -> float:
    return round(0.5 + ((probability - 0.5) * factor), 6)


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_signal_families.json"
    md_path = root / "latest_signal_families.md"
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    lines = [
        "# Sequence 23 Signal Families",
        "",
        "Research-only signal family report. No execution authority.",
        "",
        f"Signal families: {payload['signal_family_count']}",
        f"Live promotion: {payload['live_promotion_status']}",
        "",
        "## Observed facts",
    ]
    lines.extend(f"- {item}" for item in payload["observed_facts"])
    lines.extend(["", "## Inferred patterns"])
    lines.extend(f"- {item}" for item in payload["inferred_patterns"])
    lines.extend(["", "## Unknowns"])
    lines.extend(f"- {item}" for item in payload["unknowns"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
