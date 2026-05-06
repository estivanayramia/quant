from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.data.prediction_markets.activity_history import build_lane_activity_history

REPORT_ROOT = Path("reports/sequence24/signal_reports")
WALLET_FLOW_SAFETY = {
    "execution_authority": "NONE",
    "wallet_signing_enabled": False,
    "live_trading_enabled": False,
    "copy_trading_enabled": False,
    "real_orders_enabled": False,
}


def build_wallet_flow_features(dataset: dict[str, Any]) -> dict[str, Any]:
    markets = [
        _market_wallet_flow_features(market)
        for market in dataset["markets"]
        if market["included_in_lane_activity_research"] and market["activity"]
    ]
    return {
        "sequence": "24",
        "source": dataset["source"],
        "source_mode": dataset["source_mode"],
        "lane_id": dataset["lane_id"],
        "dataset_id": dataset["dataset_id"],
        "dataset_hash": dataset["dataset_hash"],
        "market_count": len(markets),
        "markets": sorted(markets, key=lambda item: item["market_id"]),
        "observed_facts": [
            "Wallet-flow features are derived from saved aggregate activity fixtures.",
            "No wallet identities, signing, following, or order authority are introduced.",
        ],
        "inferred_patterns": [
            "Concentration and one-sided flow can flag fragile market quality for later research.",
        ],
        "unknowns": [
            "Wallet ownership, off-platform hedges, and intent are unknown.",
            "Wallet-flow heuristics are not causal profitability evidence.",
        ],
        **WALLET_FLOW_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_wallet_flow_report(
    *,
    fixture_path: str | Path,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    dataset = build_lane_activity_history(fixture_path)
    payload = build_wallet_flow_features(dataset)
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _market_wallet_flow_features(market: dict[str, Any]) -> dict[str, Any]:
    activity = sorted(market["activity"], key=lambda item: item["timestamp"] or "")
    first = activity[0]
    latest = activity[-1]
    wallet_counts = [max(int(item["wallet_count"]), 1) for item in activity]
    new_wallet_ratios = [
        float(item["new_wallet_count"]) / wallet_count
        for item, wallet_count in zip(activity, wallet_counts, strict=False)
    ]
    dominant_wallet_shares = [float(item["dominant_wallet_share"]) for item in activity]
    concentration_change = round(
        float(latest["wallet_concentration"]) - float(first["wallet_concentration"]),
        6,
    )
    facts = {
        "latest_wallet_count": int(latest["wallet_count"]),
        "wallet_count_change": int(latest["wallet_count"]) - int(first["wallet_count"]),
        "latest_dominant_wallet_share": round(float(latest["dominant_wallet_share"]), 6),
        "dominant_wallet_persistence": round(
            sum(1 for share in dominant_wallet_shares if share >= 0.5)
            / len(dominant_wallet_shares),
            6,
        ),
        "wallet_concentration_change": concentration_change,
        "new_wallet_entry_burst": round(max(new_wallet_ratios or [0.0]), 6),
        "one_sided_flow_spike": round(
            max(float(item["one_sided_flow_ratio"]) for item in activity),
            6,
        ),
    }
    return {
        "market_id": market["market_id"],
        "category": market["category"],
        "resolution_status": market["resolution"]["status"],
        "observed_facts": facts,
        "heuristic_interpretations": _heuristic_interpretations(facts),
        "unknowns": [
            "Wallet-flow aggregates do not reveal participant intent.",
            "Heuristic labels are research triage only and cannot authorize orders.",
        ],
    }


def _heuristic_interpretations(facts: dict[str, Any]) -> list[dict[str, Any]]:
    interpretations = []
    if float(facts["wallet_concentration_change"]) >= 0.15:
        interpretations.append(
            {
                "label": "CONCENTRATION_RISING",
                "confidence_limit": "HEURISTIC_NOT_CERTAINTY",
            }
        )
    if float(facts["wallet_concentration_change"]) <= -0.15:
        interpretations.append(
            {
                "label": "CONCENTRATION_COLLAPSE",
                "confidence_limit": "HEURISTIC_NOT_CERTAINTY",
            }
        )
    if float(facts["dominant_wallet_persistence"]) >= 0.4:
        interpretations.append(
            {
                "label": "DOMINANT_WALLET_PERSISTENCE",
                "confidence_limit": "HEURISTIC_NOT_CAUSAL_ALPHA",
            }
        )
    if float(facts["new_wallet_entry_burst"]) >= 0.75:
        interpretations.append(
            {
                "label": "NEW_WALLET_ENTRY_BURST",
                "confidence_limit": "HEURISTIC_NOT_CAUSAL_ALPHA",
            }
        )
    if float(facts["one_sided_flow_spike"]) >= 0.72:
        interpretations.append(
            {
                "label": "ONE_SIDED_PARTICIPATION_SPIKE",
                "confidence_limit": "HEURISTIC_NOT_CERTAINTY",
            }
        )
    return interpretations


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_wallet_flow_features.json"
    md_path = root / "latest_wallet_flow_features.md"
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    lines = [
        "# Sequence 24 Wallet-Flow Features",
        "",
        "Research-only wallet-flow report. No execution authority.",
        "",
        f"Lane: {payload['lane_id']}",
        f"Markets: {payload['market_count']}",
        f"Live promotion: {payload['live_promotion_status']}",
        "",
        "## Observed facts",
    ]
    lines.extend(f"- {item}" for item in payload["observed_facts"])
    lines.extend(["", "## Heuristic interpretations"])
    lines.extend(
        f"- {item['market_id']}: "
        + ", ".join(
            interpretation["label"] for interpretation in item["heuristic_interpretations"]
        )
        for item in payload["markets"]
        if item["heuristic_interpretations"]
    )
    lines.extend(["", "## Inferred patterns"])
    lines.extend(f"- {item}" for item in payload["inferred_patterns"])
    lines.extend(["", "## Unknowns"])
    lines.extend(f"- {item}" for item in payload["unknowns"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
