from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

REPORT_ROOT = Path("reports/sequence50/weather_candidate")
CANDIDATE_ID = "pm_weather_forecast_market_mismatch"


def build_weather_market_mismatch_candidate() -> dict[str, Any]:
    return {
        "schema_version": "weather_market_mismatch_candidate_v1",
        "sequence": "50",
        "candidate_id": CANDIDATE_ID,
        "hypothesis_status": "UNPROVEN_HYPOTHESIS_ONLY",
        "hypothesis": (
            "Public forecast probabilities or bucket/range expectations may diverge from "
            "prediction-market implied probabilities. A mismatch only matters after spread, "
            "liquidity, fill, cost, baseline, placebo, and no-lookahead checks."
        ),
        "supported_market_types": [
            "binary_yes_no_weather_bucket",
            "range_bucket_weather_market",
            "multi_bucket_weather_event",
        ],
        "bucket_range_rules": [
            "Parse market rule text into deterministic lower/upper bounds.",
            "Record inclusivity, units, timezone, station/location, and resolution source.",
            "Reject ambiguous bucket rules until manually reviewed.",
        ],
        "forecast_source_requirements": [
            "public/read-only source-policy-approved endpoint or manual capture",
            "forecast issue or model-run timestamp in UTC",
            "forecast value or bucket probability known before market decision timestamp",
            "source provenance hash and source-quality tier",
        ],
        "market_price_requirements": [
            "public market metadata with market id, slug, condition id, or token id",
            "point-in-time price, midpoint, best bid, best ask, spread, and liquidity",
            "orderbook timestamp in UTC",
            "no authenticated trading endpoint dependency",
        ],
        "resolution_requirements": [
            "public final weather observation or market resolution label",
            "resolution timestamp in UTC",
            "label available only after decision timestamp",
            "proof rows require non-missing real labels",
        ],
        "timestamp_no_lookahead_requirements": [
            "forecast_ts <= known_at_ts <= orderbook_ts",
            "resolution_ts > orderbook_ts for proof rows",
            "fixtures cannot count as proof",
        ],
        "spread_liquidity_requirements": [
            "no-fill when spread is wider than conservative threshold",
            "partial-fill when displayed liquidity is below target size",
            "adverse-selection warning on thin or wide markets",
        ],
        "baselines": [
            "market_implied_baseline",
            "forecast_baseline",
            "no_skill_baseline",
        ],
        "placebos": [
            "stale_forecast_placebo",
            "random_bucket_placebo",
            "timestamp_shift_placebo",
            "sign_flip_mismatch_placebo",
        ],
        "failure_modes": [
            "WEATHER_DATA_CAPTURE_BLOCKED",
            "MARKET_DATA_CAPTURE_BLOCKED",
            "RESOLUTION_LABELS_MISSING",
            "SAMPLE_TOO_THIN",
            "PAPER_PROFIT_BLOCKED_BY_BASELINE",
            "PAPER_PROFIT_BLOCKED_BY_PLACEBO",
            "PAPER_PROFIT_BLOCKED_BY_COSTS",
            "PAPER_PROFIT_BLOCKED_BY_FILLS",
            "NO_PROFIT_CLAIM_ALLOWED",
        ],
        "profit_claim_allowed": False,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_weather_market_mismatch_candidate_report(
    *,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    payload = build_weather_market_mismatch_candidate()
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_weather_candidate.json"
    md_path = root / "latest_weather_candidate.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 50 Weather Market Mismatch Candidate",
        "",
        "Candidate definition only. No profit, live, or canary claim.",
        "",
        f"Candidate: {payload['candidate_id']}",
        f"Hypothesis status: {payload['hypothesis_status']}",
        f"Profit claim allowed: {payload['profit_claim_allowed']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        f"Execution authority: {payload['execution_authority']}",
        "",
        "## Baselines",
    ]
    lines.extend(f"- {item}" for item in payload["baselines"])
    lines.extend(["", "## Placebos"])
    lines.extend(f"- {item}" for item in payload["placebos"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}

