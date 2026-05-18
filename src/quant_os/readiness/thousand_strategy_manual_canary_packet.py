from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.readiness.money_worthy_strategy_readiness import SUCCESS
from quant_os.readiness.money_worthy_strategy_readiness_report import (
    write_money_worthy_strategy_readiness_report,
)
from quant_os.research.strategy_factory.campaign_common import (
    safe_payload,
    write_campaign_state,
    write_json_md,
)


def write_thousand_strategy_manual_canary_packet(
    *,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    readiness = write_money_worthy_strategy_readiness_report(output_root=output_root)
    ready = readiness["status"] == SUCCESS
    payload = safe_payload(
        status=(
            "FIRST_TINY_MANUAL_CANARY_PACKET_READY"
            if ready
            else "FIRST_TINY_MANUAL_CANARY_PACKET_BLOCKED"
        ),
        selected_strategy_id=(readiness.get("current_best_candidate") or {}).get("id"),
        readiness_status=readiness["status"],
        risk_envelope={"max_manual_canary_usd": 1.0, "human_only": True},
        no_transmit_preview=None,
        kill_switch="manual_stop_no_automation",
        post_canary_reconciliation_command=(
            "python -m quant_os.cli readiness money-worthy-strategy"
        ),
        human_credential_boundary="No credentials, arming, signing, or order transmission in code.",
        live_order_authorized_or_placed=False,
    )
    write_campaign_state(
        output_root=output_root,
        money_worthy_readiness_status=readiness["status"],
        manual_canary_packet_status=payload["status"],
    )
    return write_json_md(
        payload,
        output_root=output_root,
        report_dir="manual_canary_packet",
        json_name="latest_manual_canary_packet.json",
        md_name="latest_manual_canary_packet.md",
        title="First Tiny Manual Canary Packet",
        lines=[f"Status: {payload['status']}", f"Readiness: {readiness['status']}"],
    )
