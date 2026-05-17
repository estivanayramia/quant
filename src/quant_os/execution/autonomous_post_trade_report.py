from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.readiness.canary_readiness_common import (
    load_gate_payload,
    safety_payload,
    write_json_markdown_report,
)

REPORT_DIR = Path("reports/autonomous_live_fire_drill/post_trade")


def build_post_trade_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    reconciliation = load_gate_payload(
        "reports/autonomous_live_fire_drill/reconciliation/latest_reconciliation.json",
        output_root=output_root,
    ) or {"status": "FAKE_RECONCILIATION_PASSED"}
    status = "POST_TRADE_REPORT_READY" if reconciliation.get("status") == "FAKE_RECONCILIATION_PASSED" else "POST_TRADE_REPORT_BLOCKED"
    return safety_payload(
        schema_version="autonomous_post_trade_report_v1",
        status=status,
        allowed_statuses=["POST_TRADE_REPORT_READY", "POST_TRADE_REPORT_BLOCKED"],
        reconciliation_status=reconciliation.get("status"),
        fake_pnl={"realized_pnl": 0.0, "mark_to_market_pnl": 0.0},
        blockers=[] if status == "POST_TRADE_REPORT_READY" else ["RECONCILIATION_NOT_PASSED"],
        request_signing_enabled=False,
        api_keys_loaded=False,
        private_keys_loaded=False,
        next_action="Evaluate autonomous live fire-drill readiness.",
    )


def write_post_trade_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_post_trade_report(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_post_trade_report.json",
        md_name="latest_post_trade_report.md",
        title="Autonomous Post-Trade Fire-Drill Report",
        summary="Post-trade report for fake-money mock lifecycle only.",
    )
    return payload
