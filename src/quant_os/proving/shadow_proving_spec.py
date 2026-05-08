from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPORT_ROOT = Path("reports/sequence32/shadow_proving")
SCHEMA_VERSION = "shadow_proving_spec_v1"
SHADOW_PROVING_SAFETY = {
    "execution_authority": "NONE",
    "wallet_signing_enabled": False,
    "live_trading_enabled": False,
    "copy_trading_enabled": False,
    "real_orders_enabled": False,
    "prediction_market_execution_authority_added": False,
}


def write_shadow_proving_spec_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_shadow_proving_spec()
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def build_shadow_proving_spec() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "sequence": "32",
        "status": "SPEC_DEFINED",
        "thresholds": {
            "minimum_shadow_windows": 5,
            "minimum_consistent_windows": 4,
            "minimum_total_intents": 30,
            "maximum_blocked_trade_ratio": "0.35",
            "minimum_fill_rate": "0.05",
            "maximum_fill_rate": "0.50",
            "minimum_no_fill_rate": "0.20",
            "maximum_no_fill_rate": "0.90",
            "maximum_expectancy_degradation_ratio": "0.25",
            "maximum_lane_intent_concentration": "0.80",
        },
        "consistency_requirements": [
            "Intent counts must be nonzero across at least four independent replay windows.",
            "Blocked-decision reasons must be stable and explainable across windows.",
            "Risk-envelope adherence must be perfect; one violation blocks canary consideration.",
            "Harsher fill assumptions must not flip a positive result into a loss-making result.",
        ],
        "instant_fail_conditions": [
            "all_intents_blocked",
            "unresolved_realism_disqualifier",
            "risk_envelope_violation",
            "optimistic_fill_assumption",
            "weak_signal_promoted",
            "manual_live_enablement_present",
        ],
        "observed_facts_required": [
            "window_count",
            "intent_count",
            "blocked_trade_count",
            "fill_rate",
            "no_fill_rate",
            "risk_block_count",
            "expectancy_under_conservative_assumptions",
        ],
        **SHADOW_PROVING_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_shadow_proving_spec.json"
    md_path = root / "latest_shadow_proving_spec.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 32 Shadow-Proving Spec",
        "",
        "Conservative proving criteria for future tiny canary consideration. No execution authority.",
        "",
        f"Status: {payload['status']}",
        f"Live promotion: {payload['live_promotion_status']}",
        "",
        "## Thresholds",
    ]
    lines.extend(f"- {key}: {value}" for key, value in payload["thresholds"].items())
    lines.extend(["", "## Instant Fail Conditions"])
    lines.extend(f"- {item}" for item in payload["instant_fail_conditions"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
