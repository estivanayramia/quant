from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.autonomy.canary_grade_live_sim_common import ROOT, canary_safe_payload
from quant_os.autonomy.live_market_sim_common import load_json
from quant_os.readiness.canary_readiness_common import write_json_markdown_report

REPORT_DIR = ROOT / "manual_canary_packet"


def build_canary_grade_manual_packet(*, output_root: str | Path = ".") -> dict[str, Any]:
    readiness = load_json(
        "reports/canary_grade_live_sim/final/latest_canary_grade_live_sim_readiness.json",
        output_root=output_root,
    ) or {}
    repeatability = load_json(
        "reports/canary_grade_live_sim/repeatability/latest_repeatability.json",
        output_root=output_root,
    ) or {}
    capacity = load_json("reports/canary_grade_live_sim/capacity/latest_capacity.json", output_root=output_root) or {}
    proven = readiness.get("status") == "CANARY_GRADE_LIVE_SIM_PROFITABILITY_PROVEN"
    return canary_safe_payload(
        schema_version="canary_grade_manual_packet_v1",
        status="FIRST_TINY_MANUAL_CANARY_PACKET_READY" if proven else "FIRST_TINY_MANUAL_CANARY_PACKET_BLOCKED",
        candidate_summary={
            "market_family": "crypto_spot",
            "assets_tested": readiness.get("assets_tested", []),
            "strategies_tested": readiness.get("strategy_families_tested", []),
            "fake_net_pnl": readiness.get("fake_net_pnl", 0.0),
            "sample_count": readiness.get("observations_count", 0),
        },
        repeatability_summary={
            "status": repeatability.get("status"),
            "one_trade_dominance": repeatability.get("one_trade_dominance"),
            "one_window_dominance": repeatability.get("one_window_dominance"),
        },
        capacity_summary={
            "status": capacity.get("status"),
            "max_safe_notional": capacity.get("max_safe_notional"),
            "capacity_by_size": capacity.get("capacity_by_size", {}),
        },
        risk_envelope={
            "tiny_manual_canary_only": True,
            "margin": False,
            "leverage": False,
            "shorting": False,
            "futures_perps_options": False,
        },
        no_transmit_preview={
            "fake_money": True,
            "no_transmit": True,
            "order_transmission_enabled": False,
            "human_approval_required_separately": True,
            "credentials_required_separately": True,
        },
        kill_switch="manual_canary_kill_switch_required_before_any_separate_human_action",
        post_canary_reconciliation_command=".\\make.cmd canary-grade-live-sim-public-run",
        blockers=[] if proven else ["CANARY_GRADE_READINESS_NOT_PROVEN"],
        next_action="Human may review packet; no order is authorized or placed by this report."
        if proven
        else "Continue canary-grade hardening before manual packet review.",
    )


def write_canary_grade_manual_packet_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_canary_grade_manual_packet(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_manual_canary_packet.json",
        md_name="latest_manual_canary_packet.md",
        title="Canary-Grade First Tiny Manual Canary Packet",
        summary="Manual-review packet only. It does not authorize, sign, transmit, route, or place any order.",
    )
    return payload
