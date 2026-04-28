from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from quant_os.integrations.freqtrade.trade_artifacts import (
    ensure_trade_report_dir,
    write_json_report,
)
from quant_os.integrations.freqtrade.trade_reconciliation import reconcile_freqtrade_trades


def write_freqtrade_trade_report() -> dict[str, Any]:
    reconciliation = reconcile_freqtrade_trades(write=True)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "dry_run_only": True,
        "live_trading_enabled": False,
        "trade_reconciliation_status": reconciliation["status"],
        "trade_level_comparison_available": reconciliation["trade_level_comparison_available"],
        "unsafe_evidence_count": len(reconciliation["failures"]),
        "warnings": reconciliation["warnings"],
        "failures": reconciliation["failures"],
        "unmatched_quantos_expected_records": reconciliation["unmatched_quantos_expected_records"],
        "unmatched_freqtrade_records": reconciliation["unmatched_freqtrade_records"],
        "unavailable_fields": _unavailable_fields(reconciliation),
        "next_commands": [
            "make.cmd freqtrade-artifacts-scan",
            "make.cmd freqtrade-trades-ingest",
            "make.cmd freqtrade-trade-reconcile",
        ],
    }
    root = ensure_trade_report_dir()
    write_json_report(root / "latest_trade_report.json", payload)
    lines = [
        "# Freqtrade Trade Artifact Report",
        "",
        "Dry-run only. No live trading. No real-money trading.",
        "",
        f"Trade reconciliation status: {payload['trade_reconciliation_status']}",
        f"Trade-level comparison available: {payload['trade_level_comparison_available']}",
        f"Unsafe evidence count: {payload['unsafe_evidence_count']}",
        "",
        "## Warnings",
    ]
    lines.extend(f"- {warning}" for warning in (payload["warnings"] or ["None"]))
    lines.extend(["", "## Failures"])
    lines.extend(f"- {failure}" for failure in (payload["failures"] or ["None"]))
    lines.extend(["", "## Next Commands"])
    lines.extend(f"- `{command}`" for command in payload["next_commands"])
    (root / "latest_trade_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


def _unavailable_fields(reconciliation: dict[str, Any]) -> list[str]:
    if reconciliation["status"] == "UNAVAILABLE":
        return ["trade_records", "quantos_expected_records", "trade_level_match_metrics"]
    fields = []
    text = json.dumps(reconciliation, default=str)
    if "PNL_UNAVAILABLE" in text:
        fields.append("profit_abs")
    if "EXIT_EVIDENCE_UNAVAILABLE" in text:
        fields.append("exit_reason_or_close_date")
    return fields
