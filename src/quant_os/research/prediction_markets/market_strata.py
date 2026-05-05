from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from quant_os.data.prediction_markets.resolution_dataset import build_resolution_aware_dataset

REPORT_ROOT = Path("reports/sequence23/dataset")
STRATA_SAFETY = {
    "execution_authority": "NONE",
    "wallet_signing_enabled": False,
    "live_trading_enabled": False,
    "copy_trading_enabled": False,
    "real_orders_enabled": False,
}


def build_market_strata(dataset: dict[str, Any]) -> dict[str, Any]:
    markets = [_stratify_market(market) for market in dataset["markets"]]
    markets = sorted(markets, key=lambda item: item["market_id"])
    return {
        "sequence": "23",
        "source": "polymarket",
        "source_mode": dataset["source_mode"],
        "dataset_id": dataset["dataset_id"],
        "dataset_hash": dataset["dataset_hash"],
        "summary": _summary(markets),
        "markets": markets,
        "observed_facts": [
            "Market strata are computed from saved fixture snapshots and resolution metadata only.",
            "Each market is bucketed by category, time to resolution, liquidity, concentration, and cleanliness.",
        ],
        "inferred_patterns": [
            "Strata are research-routing diagnostics, not trading signals.",
        ],
        "unknowns": [
            "Fixture strata cannot prove causal edge or execution readiness.",
        ],
        **STRATA_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_market_strata_report(
    *,
    fixture_path: str | Path,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    dataset = build_resolution_aware_dataset(fixture_path)
    payload = build_market_strata(dataset)
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _stratify_market(market: dict[str, Any]) -> dict[str, Any]:
    latest = _latest_snapshot(market)
    time_bucket = _time_to_resolution_bucket(market, latest)
    liquidity_bucket = _liquidity_bucket(float(latest.get("liquidity", 0.0)))
    concentration_bucket = _concentration_bucket(float(latest.get("wallet_concentration", 0.0)))
    cleanliness_score = _cleanliness_score(
        market,
        liquidity_bucket=liquidity_bucket,
        concentration_bucket=concentration_bucket,
    )
    return {
        "market_id": market["market_id"],
        "condition_id": market["condition_id"],
        "slug": market["slug"],
        "category": market["category"],
        "resolution_status": market["resolution"]["status"],
        "candidate_research_status": market.get("candidate_research_status"),
        "exclusion_reason": market.get("exclusion_reason"),
        "category_bucket": market["category"],
        "time_to_resolution_bucket": time_bucket,
        "liquidity_bucket": liquidity_bucket,
        "concentration_bucket": concentration_bucket,
        "cleanliness_score": cleanliness_score,
        "cleanliness_bucket": _cleanliness_bucket(cleanliness_score),
        "usable_for_lane_research": bool(market.get("included_in_candidate_research")),
        "latest_snapshot": latest,
        "join_keys": {
            "source": "polymarket",
            "market_id": market["market_id"],
            "condition_id": market["condition_id"],
        },
    }


def _summary(markets: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "market_count": len(markets),
        "usable_market_count": sum(int(item["usable_for_lane_research"]) for item in markets),
        "category_counts": _counts(markets, "category_bucket"),
        "time_to_resolution_bucket_counts": _counts(markets, "time_to_resolution_bucket"),
        "liquidity_bucket_counts": _counts(markets, "liquidity_bucket"),
        "concentration_bucket_counts": _counts(markets, "concentration_bucket"),
        "cleanliness_bucket_counts": _counts(markets, "cleanliness_bucket"),
    }


def _counts(markets: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for market in markets:
        value = str(market[key])
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _latest_snapshot(market: dict[str, Any]) -> dict[str, Any]:
    snapshots = sorted(market.get("snapshots") or [], key=lambda item: item["timestamp"])
    if not snapshots:
        return {
            "timestamp": market.get("opened_at"),
            "lifecycle_status": "UNKNOWN",
            "yes_price": 0.0,
            "no_price": 0.0,
            "volume": 0.0,
            "liquidity": 0.0,
            "wallet_concentration": 0.0,
        }
    return snapshots[-1]


def _time_to_resolution_bucket(market: dict[str, Any], latest: dict[str, Any]) -> str:
    if not market.get("end_time") or not latest.get("timestamp"):
        return "UNKNOWN"
    end_time = _parse_time(market["end_time"])
    latest_time = _parse_time(latest["timestamp"])
    hours = (end_time - latest_time).total_seconds() / 3600.0
    if hours <= 72.0:
        return "SHORT"
    if hours <= 720.0:
        return "MEDIUM"
    return "LONG"


def _liquidity_bucket(liquidity: float) -> str:
    if liquidity < 10_000.0:
        return "THIN"
    if liquidity < 30_000.0:
        return "MEDIUM"
    return "DEEP"


def _concentration_bucket(wallet_concentration: float) -> str:
    if wallet_concentration < 0.4:
        return "LOW"
    if wallet_concentration <= 0.6:
        return "MODERATE"
    return "HIGH"


def _cleanliness_score(
    market: dict[str, Any],
    *,
    liquidity_bucket: str,
    concentration_bucket: str,
) -> int:
    score = 100
    if market.get("exclusion_reason"):
        score -= 55
    if not market.get("binary"):
        score -= 35
    if market["resolution"]["status"] != "RESOLVED":
        score -= 10
    if liquidity_bucket == "THIN":
        score -= 15
    if concentration_bucket == "HIGH":
        score -= 20
    return max(score, 0)


def _cleanliness_bucket(score: int) -> str:
    if score >= 80:
        return "CLEAN"
    if score >= 60:
        return "WATCHLIST"
    return "LOW_QUALITY"


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_market_strata.json"
    md_path = root / "latest_market_strata.md"
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    lines = [
        "# Sequence 23 Market Strata",
        "",
        "Research-only market strata report. No execution authority.",
        "",
        f"Markets: {payload['summary']['market_count']}",
        f"Usable markets: {payload['summary']['usable_market_count']}",
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
