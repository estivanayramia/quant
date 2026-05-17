from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.readiness.canary_readiness_common import safety_payload, write_json_markdown_report

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
    payload = safety_payload(
        schema_version="first_dollar_human_review_v1",
        status="HUMAN_REVIEW_PACKET_READY",
        allowed_statuses=["HUMAN_REVIEW_PACKET_READY", "HUMAN_REVIEW_PACKET_BLOCKED"],
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
