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
INDEPENDENT_PROOF_REPORTS = {
    **REQUIRED_REPORTS,
    "readiness": "reports/canary_grade_live_sim/final/latest_canary_grade_live_sim_readiness.json",
}
PUBLIC_KRAKEN_SOURCE = "kraken_public_rest_unauthenticated_recent_ohlc"


def build_canary_grade_fresh_repro(
    *,
    output_root: str | Path = ".",
    proof_command_passed: bool = False,
    proof_command: str = ".\\make.cmd canary-grade-live-sim-smoke",
    proof_output_root: str | Path | None = None,
    independent_clean_checkout_verified: bool = False,
    proof_head_oid: str | None = None,
) -> dict[str, Any]:
    report_check_root = (
        proof_output_root
        if independent_clean_checkout_verified and proof_output_root is not None
        else output_root
    )
    missing_reports = [
        label
        for label, report_path in REQUIRED_REPORTS.items()
        if load_json(report_path, output_root=report_check_root) is None
    ]
    blockers: list[str] = []
    if not proof_command_passed:
        blockers.append("FRESH_WORKTREE_REPRO_NOT_RUN")
    if missing_reports:
        blockers.append("REQUIRED_REPORTS_MISSING")

    independent = _verify_independent_public_proof(
        output_root=output_root,
        proof_output_root=proof_output_root,
        independent_clean_checkout_verified=independent_clean_checkout_verified,
    )
    blockers.extend(independent["blockers"])
    blockers = list(dict.fromkeys(blockers))

    if not blockers and independent_clean_checkout_verified:
        status = "INDEPENDENT_FRESH_WORKTREE_PROOF_PASSED"
    else:
        status = "FRESH_REPRO_PASSED" if not blockers else "FRESH_REPRO_BLOCKED"
    independent_status = (
        "INDEPENDENT_FRESH_WORKTREE_PROOF_PASSED"
        if status == "INDEPENDENT_FRESH_WORKTREE_PROOF_PASSED"
        else "INDEPENDENT_FRESH_WORKTREE_PROOF_BLOCKED"
    )
    return canary_safe_payload(
        schema_version="canary_grade_fresh_repro_v1",
        status=status,
        allowed_statuses=[
            "FRESH_REPRO_PASSED",
            "FRESH_REPRO_BLOCKED",
            "INDEPENDENT_FRESH_WORKTREE_PROOF_PASSED",
        ],
        attestation_scope=(
            "independent_clean_worktree_public_network"
            if status == "INDEPENDENT_FRESH_WORKTREE_PROOF_PASSED"
            else "same_worktree_command_completion"
        ),
        independent_fresh_worktree_proof_status=independent_status,
        independent_clean_checkout_verified=(
            status == "INDEPENDENT_FRESH_WORKTREE_PROOF_PASSED"
        ),
        independent_clean_checkout_required_for_merge=True,
        proof_command=proof_command,
        proof_command_passed=proof_command_passed,
        proof_output_root=str(proof_output_root) if proof_output_root is not None else None,
        proof_head_oid=proof_head_oid,
        public_data_source=independent.get("public_data_source"),
        required_reports=REQUIRED_REPORTS,
        missing_reports=missing_reports,
        independent_proof_summary=independent["summary"],
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
    proof_output_root: str | Path | None = None,
    independent_clean_checkout_verified: bool = False,
    proof_head_oid: str | None = None,
) -> dict[str, Any]:
    payload = build_canary_grade_fresh_repro(
        output_root=output_root,
        proof_command_passed=proof_command_passed,
        proof_command=proof_command,
        proof_output_root=proof_output_root,
        independent_clean_checkout_verified=independent_clean_checkout_verified,
        proof_head_oid=proof_head_oid,
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


def _verify_independent_public_proof(
    *,
    output_root: str | Path,
    proof_output_root: str | Path | None,
    independent_clean_checkout_verified: bool,
) -> dict[str, Any]:
    blockers: list[str] = []
    summary: dict[str, Any] = {}
    if not independent_clean_checkout_verified:
        return {"blockers": blockers, "summary": summary, "public_data_source": None}
    if proof_output_root is None:
        return {
            "blockers": ["INDEPENDENT_PROOF_OUTPUT_ROOT_MISSING"],
            "summary": summary,
            "public_data_source": None,
        }
    try:
        output_resolved = Path(output_root).resolve()
        proof_resolved = Path(proof_output_root).resolve()
    except OSError:
        return {
            "blockers": ["INDEPENDENT_PROOF_OUTPUT_ROOT_INVALID"],
            "summary": summary,
            "public_data_source": None,
        }
    if output_resolved == proof_resolved:
        blockers.append("INDEPENDENT_PROOF_ROOT_MATCHES_CURRENT_WORKTREE")

    reports = {
        name: load_json(path, output_root=proof_resolved)
        for name, path in INDEPENDENT_PROOF_REPORTS.items()
    }
    missing = [name for name, payload in reports.items() if payload is None]
    if missing:
        blockers.append("INDEPENDENT_PROOF_REQUIRED_REPORTS_MISSING")
        summary["missing_reports"] = missing
        reports = {name: payload or {} for name, payload in reports.items()}
    else:
        reports = {name: payload or {} for name, payload in reports.items()}

    readiness = reports["readiness"]
    observer = reports["observer"]
    pnl = reports["pnl"]
    repeatability = reports["repeatability"]
    reconciliation = reports["reconciliation"]
    capacity = reports["capacity"]
    public_data_source = str(observer.get("source") or "")
    summary.update(
        {
            "proof_output_root": str(proof_resolved),
            "readiness_status": readiness.get("status"),
            "observation_count": int(observer.get("observation_count") or 0),
            "eligible_intent_count": int(reports["intents"].get("eligible_intent_count") or 0),
            "fake_fill_count": int(reports["fills"].get("fake_fill_count") or 0),
            "completed_mark_count": int(pnl.get("completed_mark_count") or 0),
            "fake_net_pnl": float(pnl.get("fake_net_pnl") or readiness.get("fake_net_pnl") or 0.0),
            "public_data_source": public_data_source,
            "repeatability_status": repeatability.get("status"),
            "capacity_status": capacity.get("status"),
            "reconciliation_status": reconciliation.get("status"),
        }
    )

    if readiness.get("status") != "CANARY_GRADE_LIVE_SIM_PROFITABILITY_PROVEN":
        blockers.append("INDEPENDENT_PROOF_READINESS_NOT_PROVEN")
    if public_data_source != PUBLIC_KRAKEN_SOURCE:
        blockers.append("INDEPENDENT_PROOF_NOT_REAL_PUBLIC_KRAKEN")
    if "fixture" in public_data_source.lower():
        blockers.append("INDEPENDENT_PROOF_FIXTURE_SOURCE")
    if float(readiness.get("fake_net_pnl") or pnl.get("fake_net_pnl") or 0.0) <= 0.0:
        blockers.append("INDEPENDENT_PROOF_FAKE_NET_PNL_NOT_POSITIVE")
    if readiness.get("baseline_beaten") is not True:
        blockers.append("INDEPENDENT_PROOF_BASELINE_NOT_BEATEN")
    if readiness.get("placebo_beaten") is not True:
        blockers.append("INDEPENDENT_PROOF_PLACEBO_NOT_BEATEN")
    if repeatability.get("status") != "REPEATABILITY_PASSED":
        blockers.append("INDEPENDENT_PROOF_REPEATABILITY_NOT_PASSED")
    if capacity.get("status") != "CAPACITY_TINY_CANARY_PASSED":
        blockers.append("INDEPENDENT_PROOF_CAPACITY_NOT_PASSED")
    if reconciliation.get("status") != "CANARY_GRADE_RECONCILIATION_PASSED":
        blockers.append("INDEPENDENT_PROOF_RECONCILIATION_NOT_PASSED")
    if int(reconciliation.get("reconciliation_failures") or 0) != 0:
        blockers.append("INDEPENDENT_PROOF_RECONCILIATION_FAILURES_PRESENT")
    mark_rows = list(pnl.get("pnl_rows") or [])
    if mark_rows and not all(
        str(row.get("mark_timestamp")) > str(row.get("entry_timestamp")) for row in mark_rows
    ):
        blockers.append("INDEPENDENT_PROOF_LOOKAHEAD_DETECTED")
    blockers.extend(_safety_blockers(reports))
    return {
        "blockers": list(dict.fromkeys(blockers)),
        "summary": summary,
        "public_data_source": public_data_source or None,
    }


def _safety_blockers(reports: dict[str, dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    expected_false = [
        "live_trading_enabled",
        "order_transmission_enabled",
        "authenticated_requests_enabled",
        "request_signing_enabled",
        "api_keys_loaded",
        "private_keys_loaded",
        "authenticated_endpoint_called",
        "checked_account_balance",
        "checked_portfolio",
    ]
    expected_zero = ["actual_order_count", "actual_cancel_count", "unsafe_action_attempts"]
    for name, payload in reports.items():
        for key in expected_false:
            if payload.get(key) is True:
                blockers.append(f"INDEPENDENT_PROOF_UNSAFE_FLAG_TRUE:{name}:{key}")
        for key in expected_zero:
            if int(payload.get(key) or 0) != 0:
                blockers.append(f"INDEPENDENT_PROOF_UNSAFE_COUNTER_NONZERO:{name}:{key}")
        if payload.get("execution_authority") not in {None, "NONE"}:
            blockers.append(f"INDEPENDENT_PROOF_EXECUTION_AUTHORITY_NOT_NONE:{name}")
        if payload.get("hidden_local_state_dependency") is True:
            blockers.append(f"INDEPENDENT_PROOF_HIDDEN_LOCAL_STATE:{name}")
    return blockers
