from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.autonomy.canary_grade_live_sim_common import RESUME_COMMAND, ROOT, canary_safe_payload
from quant_os.autonomy.live_market_sim_common import load_json
from quant_os.readiness.canary_readiness_common import write_json_markdown_report

REPORT_DIR = ROOT / "fresh_repro"
REQUIRED_REPORTS = {
    "observer": "reports/canary_grade_live_sim/crypto/latest_observer.json",
    "intents": "reports/canary_grade_live_sim/crypto/latest_intents.json",
    "fills": "reports/canary_grade_live_sim/crypto/latest_fills.json",
    "ledger": "reports/canary_grade_live_sim/crypto/latest_ledger.json",
    "pnl": "reports/canary_grade_live_sim/crypto/latest_pnl.json",
    "reconciliation": "reports/canary_grade_live_sim/crypto/latest_reconciliation.json",
    "repeatability": "reports/canary_grade_live_sim/repeatability/latest_repeatability.json",
    "capacity": "reports/canary_grade_live_sim/capacity/latest_capacity.json",
}


def build_canary_grade_fresh_repro(
    *,
    output_root: str | Path = ".",
    proof_command_passed: bool = False,
    proof_command: str = ".\\make.cmd canary-grade-live-sim-smoke",
) -> dict[str, Any]:
    missing_reports = [
        label
        for label, report_path in REQUIRED_REPORTS.items()
        if load_json(report_path, output_root=output_root) is None
    ]
    blockers: list[str] = []
    if not proof_command_passed:
        blockers.append("FRESH_WORKTREE_REPRO_NOT_RUN")
    if missing_reports:
        blockers.append("REQUIRED_REPORTS_MISSING")

    status = "FRESH_REPRO_PASSED" if not blockers else "FRESH_REPRO_BLOCKED"
    return canary_safe_payload(
        schema_version="canary_grade_fresh_repro_v1",
        status=status,
        proof_command=proof_command,
        proof_command_passed=proof_command_passed,
        required_reports=REQUIRED_REPORTS,
        missing_reports=missing_reports,
        public_network_dependency_declared=True,
        fixture_safe_smoke_command=".\\make.cmd canary-grade-live-sim-smoke",
        public_network_command=RESUME_COMMAND,
        hidden_local_state_dependency=False,
        blockers=blockers,
        next_action="Run readiness canary-grade-live-sim."
        if status == "FRESH_REPRO_PASSED"
        else "Run the full canary-grade smoke/public workflow before final readiness.",
        exact_resume_command=RESUME_COMMAND,
    )


def write_canary_grade_fresh_repro_report(
    *,
    output_root: str | Path = ".",
    proof_command_passed: bool = False,
    proof_command: str = ".\\make.cmd canary-grade-live-sim-smoke",
) -> dict[str, Any]:
    payload = build_canary_grade_fresh_repro(
        output_root=output_root,
        proof_command_passed=proof_command_passed,
        proof_command=proof_command,
    )
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_fresh_repro.json",
        md_name="latest_fresh_repro.md",
        title="Canary-Grade Fresh Worktree Reproducibility",
        summary="Fresh-repro gate for the canary-grade fake-money public-market simulation.",
    )
    return payload
