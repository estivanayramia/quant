from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.readiness.canary_readiness_common import (
    load_gate_payload,
    safety_payload,
    write_json_markdown_report,
)

REPORT_DIR = Path("reports/first_dollar_preflight/human_review")

REQUIRED_CONFIRMATIONS = [
    "I reviewed the paper candidate audit.",
    "I reviewed no-lookahead lineage.",
    "I reviewed replay recompute.",
    "I reviewed robustness.",
    "I reviewed cost/fill stress.",
    "I reviewed bounded shadow rehearsal.",
    "I reviewed dry-run parity.",
    "I reviewed risk envelope.",
    "I reviewed kill switch.",
    "I reviewed reconciliation.",
    "I reviewed manual packet.",
    "I understand this does not place an order.",
    "I understand live trading remains disabled.",
    "I understand API/private keys are not loaded.",
    "I understand a later first-dollar trade requires separate manual action.",
    "I accept the possibility of losing the full tiny canary amount.",
]


def build_first_dollar_human_review(
    *,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    eligibility = load_gate_payload(
        "reports/first_dollar_preflight/current_market/latest_current_market_eligibility.json",
        output_root=output_root,
    ) or {}
    forecast = eligibility.get("forecast_evidence") or load_gate_payload(
        "reports/first_dollar_preflight/current_forecast/latest_current_forecast.json",
        output_root=output_root,
    ) or {}
    preview = load_gate_payload(
        "reports/first_dollar_preflight/order_preview/latest_order_preview.json",
        output_root=output_root,
    ) or {}
    required_statements = [
        "This packet does not place or authorize an order.",
        "Separate human action is required for first-dollar execution.",
    ]
    payload = safety_payload(
        schema_version="first_dollar_human_review_v1",
        status="HUMAN_REVIEW_PACKET_READY",
        allowed_statuses=["HUMAN_REVIEW_PACKET_READY", "HUMAN_REVIEW_PACKET_BLOCKED"],
        selected_market=eligibility.get("market"),
        forecast_evidence=forecast,
        orderbook_evidence={
            "orderbook_ts": (eligibility.get("market") or {}).get("orderbook_ts"),
            "market_evidence_hash": eligibility.get("market_evidence_hash"),
        },
        reason_for_candidate_signal=preview.get("reason_code")
        or "Current public forecast bucket maps to selected market and eligibility gates passed.",
        no_transmit_order_preview_path="reports/first_dollar_preflight/order_preview/latest_order_preview.json",
        risk_envelope={
            "max_contracts": preview.get("max_contracts", 1),
            "max_nominal_exposure": preview.get("max_nominal_exposure", 1.0),
            "max_total_loss": preview.get("max_total_loss", 1.0),
        },
        max_loss=preview.get("max_total_loss", 1.0),
        kill_switch="python -m quant_os.cli risk weather-canary-kill-switch",
        reconciliation_command="python -m quant_os.cli execution weather-canary-reconciliation",
        required_statements=required_statements,
        required_confirmations=REQUIRED_CONFIRMATIONS,
        confirmation_checkboxes={item: False for item in REQUIRED_CONFIRMATIONS},
        human_confirmation_collected=False,
        separate_manual_action_required_for_first_dollar=True,
        api_keys_loaded=False,
        private_keys_loaded=False,
        blockers=[],
        next_action="Human review remains required before any later first-dollar action.",
    )
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_human_review.json",
        md_name="latest_human_review.md",
        title="First-Dollar Human Review",
        summary="Manual review checklist. This packet does not arm or transmit orders.",
    )
    return payload


def write_first_dollar_human_review_report(
    *,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    return build_first_dollar_human_review(output_root=output_root)
