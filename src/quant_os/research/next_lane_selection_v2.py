from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPORT_ROOT = Path("reports/sequence28/next_lane")
NEXT_LANE_SAFETY = {
    "execution_authority": "NONE",
    "wallet_signing_enabled": False,
    "live_trading_enabled": False,
    "copy_trading_enabled": False,
    "real_orders_enabled": False,
    "prediction_market_execution_authority_added": False,
}


def write_next_lane_selection_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_next_lane_selection_report()
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def build_next_lane_selection_report() -> dict[str, Any]:
    lanes = _candidate_lanes()
    selected = next(
        lane for lane in lanes if lane["lane_id"] == "prediction_market_replay_input_infrastructure"
    )
    return {
        "sequence": "28",
        "selection_status": "BUILD_REPLAY_INPUTS_BEFORE_LANE_PROMOTION",
        "selected_lane_id": selected["lane_id"],
        "selected_lane": selected,
        "current_lane": {
            "lane_id": "short_dated_clean_binary",
            "status": "DEPRIORITIZED",
            "reason": (
                "Sequence 27 recorded market-baseline dominance and no credible "
                "venue-specific signal family."
            ),
        },
        "candidate_lanes": lanes,
        "decision_rules": [
            "Do not keep forcing replay design around a retire/deprioritize candidate.",
            "Prefer work that improves future profitability testability without live authority.",
            "Require data, replay, validation, and risk blockers before any execution discussion.",
        ],
        "observed_facts": [
            "The crypto lane has bounded dry-run/canary infrastructure but weak recent edge evidence.",
            "Prediction-market lane research lacks normalized replay inputs and realistic replay events.",
            "Alternative prediction-market signals remain unsupported until data quality improves.",
        ],
        "inferred_patterns": [
            "The next profitable path is improving replay testability, not adding strategy hype.",
        ],
        "unknowns": [
            "Whether normalized replay inputs will be deep enough for narrow replay design.",
            "Whether any prediction-market lane can survive market baselines after realistic costs.",
        ],
        **NEXT_LANE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _candidate_lanes() -> list[dict[str, Any]]:
    return [
        {
            "lane_id": "bounded_crypto_dry_run_proving_continuation",
            "description": "Continue deterministic crypto dry-run/canary infrastructure only.",
            "research_worthiness": 3,
            "path_to_bounded_autonomy": 4,
            "profitability_testability_gain": 2,
            "live_execution_allowed": False,
            "required_data": [
                "More recent venue-captured OHLCV and fee/slippage assumptions.",
                "Walk-forward evidence that beats placebos after costs.",
            ],
            "replay_blockers": [
                "Current baseline strategy evidence remains weak after costs.",
            ],
            "validation_blockers": [
                "Need stronger OOS and promotion-readiness evidence before capital changes.",
            ],
            "recommendation": "CONTINUE_AS_INFRASTRUCTURE_ONLY",
        },
        {
            "lane_id": "prediction_market_replay_input_infrastructure",
            "description": "Normalize public/read-only prediction-market snapshots and manifests.",
            "research_worthiness": 5,
            "path_to_bounded_autonomy": 3,
            "profitability_testability_gain": 5,
            "live_execution_allowed": False,
            "required_data": [
                "Public market state snapshots.",
                "Orderbook/trade records or archive manifests with provenance.",
                "Reference dataset manifests for future robustness checks.",
            ],
            "replay_blockers": [
                "Queue position, fills, fees, latency, and adverse selection remain unmodeled.",
                "Manifests alone do not prove record-level replay completeness.",
            ],
            "validation_blockers": [
                "Replay inputs must pass structure and quality gates before replay design.",
                "Replay-input readiness is not profitability or live readiness.",
            ],
            "recommendation": "SELECT_NOW",
        },
        {
            "lane_id": "narrow_alternative_prediction_market_research",
            "description": "Search for a new prediction-market research lane after replay inputs exist.",
            "research_worthiness": 2,
            "path_to_bounded_autonomy": 2,
            "profitability_testability_gain": 2,
            "live_execution_allowed": False,
            "required_data": [
                "Normalized replay candidates from multiple venues or sources.",
                "Resolved labels and baseline comparisons.",
            ],
            "replay_blockers": [
                "No new credible signal family has been identified yet.",
            ],
            "validation_blockers": [
                "Would be premature before replay-input quality is known.",
            ],
            "recommendation": "DEFER",
        },
    ]


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_next_lane_selection.json"
    md_path = root / "latest_next_lane_selection.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 28 Next Lane Selection",
        "",
        "Research-only lane selection report. No execution authority.",
        "",
        f"Status: {payload['selection_status']}",
        f"Selected lane: {payload['selected_lane_id']}",
        f"Live promotion: {payload['live_promotion_status']}",
        "",
        "## Candidate Lanes",
    ]
    lines.extend(
        f"- {lane['lane_id']}: {lane['recommendation']}" for lane in payload["candidate_lanes"]
    )
    lines.extend(["", "## Decision Rules"])
    lines.extend(f"- {item}" for item in payload["decision_rules"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
