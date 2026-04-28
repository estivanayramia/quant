from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from quant_os.monitoring.divergence import check_dryrun_divergence
from quant_os.monitoring.dryrun_comparison import build_dryrun_comparison
from quant_os.monitoring.dryrun_history import DRYRUN_ROOT

LIVE_BLOCKERS = [
    "No multi-week dry-run evidence yet.",
    "No real exchange reconciliation exists in this phase.",
    "No stoploss-on-exchange proof exists.",
    "No API-key permission verification exists.",
    "No live canary policy implementation exists.",
    "No human approval gate implementation exists.",
    "Live trading is disabled by constitution.",
]


def check_promotion_readiness(write: bool = True) -> dict[str, Any]:
    comparison = build_dryrun_comparison(write=True)
    divergence = check_dryrun_divergence(write=True)
    blockers = []
    if comparison["status"] == "FAIL":
        blockers.append("DRY_RUN_COMPARISON_FAILED")
    if divergence["status"] == "FAIL":
        blockers.append("DRY_RUN_DIVERGENCE_FAILED")
    unsafe_failures = comparison.get("unsafe_failures", []) + divergence.get("failures", [])
    dry_run_ready = not unsafe_failures and divergence["status"] in {"PASS", "WARN"}
    status = "DRY_RUN_READY" if dry_run_ready else "NOT_ELIGIBLE"
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": status,
        "dry_run_ready": dry_run_ready,
        "live_promotion_status": "TINY_LIVE_BLOCKED",
        "live_eligible": False,
        "live_promotion_allowed": False,
        "blockers": sorted(set(blockers)),
        "warnings": comparison.get("warnings", []) + divergence.get("warnings", []),
        "live_blockers": LIVE_BLOCKERS,
        "next_allowed_statuses": ["research", "shadow", "dry_run_ready"],
        "explicitly_not_allowed": ["paper_without_future_gate", "tiny_live", "live_trading"],
    }
    if write:
        (DRYRUN_ROOT / "latest_promotion_readiness.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
        )
    return payload
