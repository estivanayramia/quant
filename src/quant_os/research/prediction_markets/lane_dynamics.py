from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.data.prediction_markets.activity_history import build_lane_activity_history
from quant_os.research.prediction_markets.time_series_features import build_time_series_features

REPORT_ROOT = Path("reports/sequence24/signal_reports")
DYNAMIC_SIGNAL_SAFETY = {
    "execution_authority": "NONE",
    "wallet_signing_enabled": False,
    "live_trading_enabled": False,
    "copy_trading_enabled": False,
    "real_orders_enabled": False,
}

DYNAMIC_SIGNAL_FAMILIES = [
    {
        "signal_family_id": "late_stabilization_slope",
        "name": "Late Stabilization Slope",
        "probability_key": "late_stabilization_slope_probability",
        "plain_english_explanation": "Trusts the market only when the final price step is small; otherwise it shrinks toward 50/50.",
        "what_it_measures": "Late price stabilization versus near-close instability.",
        "feature_list": ["late_price_slope", "latest_time_to_resolution_bucket", "current_market_probability"],
        "why_it_might_work": "Near-resolution markets with stable prices may already reflect stronger public information.",
        "why_it_might_fail": "Stable late prices can be consensus without edge, and unstable prices can still be correct.",
        "market_pathology_sensitivity": "Sensitive to stale late snapshots and abrupt resolution-news repricing.",
        "failure_mode_notes": [
            "This family cannot justify replay without beating the market baseline.",
            "It remains a deterministic research feature, not an execution filter.",
        ],
        "opaque_model": False,
    },
    {
        "signal_family_id": "liquidity_confirmed_momentum",
        "name": "Liquidity-Confirmed Momentum",
        "probability_key": "liquidity_confirmed_momentum_probability",
        "plain_english_explanation": "Keeps market probability only when price movement is supported by liquidity and volume growth.",
        "what_it_measures": "Price drift supported by improving liquidity and volume.",
        "feature_list": ["mid_to_close_drift", "liquidity_change_pct", "volume_change"],
        "why_it_might_work": "Momentum with improving liquidity may reflect better information quality than thin moves.",
        "why_it_might_fail": "The market price may already include this information, leaving no residual signal.",
        "market_pathology_sensitivity": "Sensitive to volume bursts that are not independent information.",
        "failure_mode_notes": [
            "Confirmed momentum is still compared against the market baseline.",
            "It does not create market-making or order-routing authority.",
        ],
        "opaque_model": False,
    },
    {
        "signal_family_id": "wallet_flow_caution",
        "name": "Wallet-Flow Caution",
        "probability_key": "wallet_flow_caution_probability",
        "plain_english_explanation": "Shrinks probabilities when concentration or one-sided participation suggests fragile price quality.",
        "what_it_measures": "Dominant-wallet persistence, concentration change, and one-sided flow spikes.",
        "feature_list": [
            "wallet_concentration_change",
            "dominant_wallet_persistence",
            "new_wallet_entry_burst",
            "one_sided_flow_spike",
        ],
        "why_it_might_work": "Extreme flow concentration can warn that a displayed price is less robust.",
        "why_it_might_fail": "Concentrated flow can come from informed participants rather than manipulation.",
        "market_pathology_sensitivity": "Sensitive to crowding, coordination, and one-sided late participation.",
        "failure_mode_notes": [
            "This is not wallet mirroring or copy trading.",
            "Wallet observations remain heuristic context only.",
        ],
        "opaque_model": False,
    },
    {
        "signal_family_id": "unsupported_jump_caution",
        "name": "Unsupported Jump Caution",
        "probability_key": "unsupported_jump_caution_probability",
        "plain_english_explanation": "Shrinks after abrupt price jumps that occur without improving liquidity.",
        "what_it_measures": "Large price changes coincident with flat or falling liquidity.",
        "feature_list": ["max_unsupported_price_jump", "liquidity_change", "current_market_probability"],
        "why_it_might_work": "Unsupported jumps can indicate noisy repricing or fragile market depth.",
        "why_it_might_fail": "A true information shock can move prices before liquidity recovers.",
        "market_pathology_sensitivity": "Sensitive to thin liquidity, stale quotes, and jumpy late markets.",
        "failure_mode_notes": [
            "Unsupported jumps are research warnings, not trade commands.",
            "This family must be evaluated on resolved labels before replay design.",
        ],
        "opaque_model": False,
    },
]


def apply_dynamic_signal_families(features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched = []
    for feature in features:
        item = dict(feature)
        current = float(item["current_market_probability"])
        item["late_stabilization_slope_probability"] = _late_stabilization_probability(item, current)
        item["liquidity_confirmed_momentum_probability"] = _liquidity_confirmed_momentum_probability(
            item,
            current,
        )
        item["wallet_flow_caution_probability"] = _wallet_flow_caution_probability(item, current)
        item["unsupported_jump_caution_probability"] = _unsupported_jump_caution_probability(
            item,
            current,
        )
        enriched.append(item)
    return sorted(enriched, key=lambda row: row["market_id"])


def write_dynamic_signal_report(
    *,
    fixture_path: str | Path,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    dataset = build_lane_activity_history(fixture_path)
    features = apply_dynamic_signal_families(build_time_series_features(dataset))
    payload = {
        "sequence": "24",
        "source": dataset["source"],
        "source_mode": dataset["source_mode"],
        "lane_id": dataset["lane_id"],
        "dataset_id": dataset["dataset_id"],
        "dataset_hash": dataset["dataset_hash"],
        "feature_count": len(features),
        "signal_family_count": len(DYNAMIC_SIGNAL_FAMILIES),
        "signal_families": DYNAMIC_SIGNAL_FAMILIES,
        "observed_facts": [
            "Dynamic signal families use saved activity fixtures only.",
            "Every family is deterministic, interpretable, and falsifiable.",
        ],
        "inferred_patterns": [
            "Dynamic activity signals are hypotheses for lane evaluation, not trade instructions.",
        ],
        "unknowns": [
            "No dynamic family should be trusted unless it beats required baselines on sufficient history.",
        ],
        **DYNAMIC_SIGNAL_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _late_stabilization_probability(feature: dict[str, Any], current: float) -> float:
    if feature["latest_time_to_resolution_bucket"] == "FINAL_HOURS" and abs(
        float(feature["late_price_slope"])
    ) <= 0.03:
        return round(current, 6)
    return _shrink_probability(current, factor=0.92)


def _liquidity_confirmed_momentum_probability(feature: dict[str, Any], current: float) -> float:
    if (
        abs(float(feature["mid_to_close_drift"])) >= 0.04
        and float(feature["liquidity_change_pct"]) > 0.15
        and float(feature["volume_change"]) > 0
    ):
        return round(current, 6)
    return _shrink_probability(current, factor=0.94)


def _wallet_flow_caution_probability(feature: dict[str, Any], current: float) -> float:
    if (
        float(feature["wallet_concentration_change"]) >= 0.18
        or float(feature["dominant_wallet_persistence"]) >= 0.4
        or float(feature["one_sided_flow_spike"]) >= 0.72
    ):
        return _shrink_probability(current, factor=0.78)
    return round(current, 6)


def _unsupported_jump_caution_probability(feature: dict[str, Any], current: float) -> float:
    if float(feature["max_unsupported_price_jump"]) >= 0.08:
        return _shrink_probability(current, factor=0.72)
    return round(current, 6)


def _shrink_probability(probability: float, *, factor: float) -> float:
    return round(0.5 + ((probability - 0.5) * factor), 6)


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_signal_reports.json"
    md_path = root / "latest_signal_reports.md"
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    lines = [
        "# Sequence 24 Dynamic Signal Families",
        "",
        "Research-only dynamic signal report. No execution authority.",
        "",
        f"Lane: {payload['lane_id']}",
        f"Signal families: {payload['signal_family_count']}",
        f"Feature count: {payload['feature_count']}",
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
