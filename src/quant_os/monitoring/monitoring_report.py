from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from quant_os.monitoring.divergence import check_dryrun_divergence
from quant_os.monitoring.dryrun_comparison import build_dryrun_comparison
from quant_os.monitoring.dryrun_history import (
    DRYRUN_ROOT,
    append_history_record,
    ensure_dryrun_monitoring_dirs,
)
from quant_os.monitoring.freshness import dryrun_freshness_summary
from quant_os.monitoring.promotion_readiness import check_promotion_readiness


def generate_dryrun_monitoring_report() -> dict[str, Any]:
    ensure_dryrun_monitoring_dirs()
    history = append_history_record()
    comparison = build_dryrun_comparison(write=True)
    divergence = check_dryrun_divergence(write=True)
    promotion = check_promotion_readiness(write=True)
    freshness = dryrun_freshness_summary()
    status = _aggregate_report_status(comparison, divergence, promotion)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": status,
        "dry_run_only": True,
        "live_trading_enabled": False,
        "history_records_count": history["records_count"],
        "latest_comparison_status": comparison["status"],
        "latest_divergence_status": divergence["status"],
        "latest_promotion_status": promotion["status"],
        "live_promotion_status": promotion["live_promotion_status"],
        "blockers": promotion["blockers"] + [item["name"] for item in divergence["failures"]],
        "warnings": _warning_names(comparison) + _warning_names(divergence),
        "freshness": freshness,
        "comparison": comparison,
        "divergence": divergence,
        "promotion_readiness": promotion,
        "latest_report_path": "reports/dryrun/latest_monitoring_report.md",
        "next_manual_commands": [
            "make.cmd dryrun-history",
            "make.cmd dryrun-compare",
            "make.cmd dryrun-divergence-check",
            "make.cmd dryrun-monitor-report",
            "make.cmd dryrun-promote-check",
        ],
    }
    (DRYRUN_ROOT / "latest_monitoring_report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    (DRYRUN_ROOT / "latest_monitoring_report.md").write_text(_markdown(payload), encoding="utf-8")
    return payload


def _aggregate_report_status(
    comparison: dict[str, Any], divergence: dict[str, Any], promotion: dict[str, Any]
) -> str:
    if comparison["status"] == "FAIL" or divergence["status"] == "FAIL":
        return "FAIL"
    if comparison["status"] == "WARN" or divergence["status"] == "WARN":
        return "WARN"
    if promotion["status"] != "DRY_RUN_READY":
        return "WARN"
    return "PASS"


def _warning_names(payload: dict[str, Any]) -> list[str]:
    return [
        str(item.get("name", item.get("status", "warning"))) for item in payload.get("warnings", [])
    ]


def _markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Dry-Run Monitoring Report",
        "",
        "Dry-run only. No live trading. No real-money trading.",
        "",
        f"Status: {payload['status']}",
        f"Comparison: {payload['latest_comparison_status']}",
        f"Divergence: {payload['latest_divergence_status']}",
        f"Promotion readiness: {payload['latest_promotion_status']}",
        f"Live promotion: {payload['live_promotion_status']}",
        f"History records: {payload['history_records_count']}",
        "",
        "## Blockers",
    ]
    blockers = payload.get("blockers") or ["None for dry-run monitoring; live remains blocked."]
    lines.extend(f"- {blocker}" for blocker in blockers)
    lines.extend(["", "## Warnings"])
    warnings = payload.get("warnings") or ["None"]
    lines.extend(f"- {warning}" for warning in warnings)
    lines.extend(["", "## Artifact Freshness"])
    for name, check in payload["freshness"]["checks"].items():
        lines.append(f"- {name}: {check['status']} ({check['reason']})")
    lines.extend(["", "## Next Commands"])
    lines.extend(f"- `{command}`" for command in payload["next_manual_commands"])
    lines.extend(
        [
            "",
            "Trade-level Freqtrade-vs-QuantOS reconciliation is unavailable until structured Freqtrade dry-run trade artifacts are ingested. This report does not claim live readiness.",
        ]
    )
    return "\n".join(lines) + "\n"
