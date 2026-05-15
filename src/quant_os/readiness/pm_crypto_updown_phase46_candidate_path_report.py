from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.readiness.pm_crypto_updown_allowed_intent_decision import (
    evaluate_pm_crypto_updown_allowed_intent_decision,
)
from quant_os.readiness.pm_crypto_updown_phase46_candidate_path import (
    evaluate_pm_crypto_updown_phase46_candidate_path,
)
from quant_os.research.replay_candidates.pm_crypto_updown_allowed_intent_capture_pass import (
    DEFAULT_CAPTURE_ROOT,
    DEFAULT_FIXTURE_ROOT,
    evaluate_pm_crypto_updown_allowed_intent_capture_pass,
)

CANDIDATE_DECISION_REPORT_ROOT = Path("reports/sequence46/candidate_decision")
CANDIDATE_PATH_REPORT_ROOT = Path("reports/sequence46/candidate_path")
BOUNDED_SHADOW_REPORT_ROOT = Path("reports/sequence46/bounded_shadow_rehearsal")
NEXT_HANDOFF_REPORT_ROOT = Path("reports/sequence46/next_candidate_handoff")


def write_pm_crypto_updown_phase46_candidate_decision_report(
    *,
    fixture_root: str | Path | None = None,
    real_cached_artifact_roots: list[str | Path] | None = None,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    payload = evaluate_pm_crypto_updown_allowed_intent_decision(
        fixture_root=fixture_root or DEFAULT_FIXTURE_ROOT,
        real_cached_artifact_roots=real_cached_artifact_roots,
    )
    payload = {**payload, "sequence": "46"}
    payload["report_paths"] = _write_candidate_decision_report(
        payload,
        output_root=output_root,
    )
    return payload


def write_pm_crypto_updown_phase46_candidate_path_report(
    *,
    run_id: str = "pm_crypto_updown_manual_046",
    capture_run_root: str | Path | None = None,
    baseline_real_cached_artifact_roots: list[str | Path] | None = None,
    fixture_root: str | Path | None = None,
    capture_pass: dict[str, Any] | None = None,
    candidate_decision: dict[str, Any] | None = None,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    run_root = Path(capture_run_root) if capture_run_root is not None else DEFAULT_CAPTURE_ROOT / run_id
    roots = list(baseline_real_cached_artifact_roots or []) + [run_root]
    capture_pass = capture_pass or evaluate_pm_crypto_updown_allowed_intent_capture_pass(
        run_id=run_id,
        capture_run_root=run_root,
        baseline_real_cached_artifact_roots=baseline_real_cached_artifact_roots,
        fixture_root=fixture_root or DEFAULT_FIXTURE_ROOT,
    )
    candidate_decision = candidate_decision or write_pm_crypto_updown_phase46_candidate_decision_report(
        fixture_root=fixture_root or DEFAULT_FIXTURE_ROOT,
        real_cached_artifact_roots=roots,
        output_root=output_root,
    )
    payload = evaluate_pm_crypto_updown_phase46_candidate_path(
        capture_pass=capture_pass,
        candidate_decision=candidate_decision,
    )
    payload["report_paths"] = _write_candidate_path_report(payload, output_root=output_root)
    if payload["final_status"] == "READY_FOR_BOUNDED_SHADOW_REHEARSAL":
        bounded = _write_bounded_shadow_rehearsal_report(payload, output_root=output_root)
        payload["bounded_shadow_rehearsal_report_paths"] = bounded["report_paths"]
    if payload["final_status"] in {"DEPRIORITIZE_CANDIDATE", "RETIRE_CANDIDATE"}:
        handoff = _write_next_candidate_handoff(payload, output_root=output_root)
        payload["next_candidate_handoff_report_paths"] = handoff["report_paths"]
    return payload


def _write_candidate_decision_report(
    payload: dict[str, Any],
    *,
    output_root: str | Path,
) -> dict[str, str]:
    root = Path(output_root) / CANDIDATE_DECISION_REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_pm_crypto_updown_candidate_decision.json"
    md_path = root / "latest_pm_crypto_updown_candidate_decision.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 46 PM Crypto UP/DOWN Candidate Decision",
        "",
        "Rerun of the allowed-intent decision stack after the Phase 46 capture pass.",
        "",
        f"Decision status: {payload['decision_status']}",
        f"Ready for bounded shadow rehearsal: {payload['ready_for_bounded_shadow_rehearsal']}",
        f"Allowed primary intents: {payload['allowed_primary_intent_count']} / {payload['minimum_allowed_primary_intents']}",
        f"Allowed real-cached intents: {payload['allowed_real_cached_intent_count']} / {payload['minimum_allowed_real_cached_intents']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def _write_candidate_path_report(
    payload: dict[str, Any],
    *,
    output_root: str | Path,
) -> dict[str, str]:
    root = Path(output_root) / CANDIDATE_PATH_REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_phase46_candidate_path.json"
    md_path = root / "latest_phase46_candidate_path.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 46 Candidate Path",
        "",
        "Hard path decision after one allowed-intent capture/import pass.",
        "",
        f"Final status: {payload['final_status']}",
        f"Allowed primary intents: {payload['allowed_primary_intents_before']} -> {payload['allowed_primary_intents_after']}",
        f"Allowed real-cached intents: {payload['allowed_real_cached_intents_before']} -> {payload['allowed_real_cached_intents_after']}",
        f"Bounded shadow package created: {payload['bounded_shadow_rehearsal_package_created']}",
        f"Next candidate handoff created: {payload['next_candidate_handoff_created']}",
        f"Exact next command: {payload['exact_next_command']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        "",
        "## Blockers",
    ]
    lines.extend(f"- {item}" for item in payload["blockers"] or ["None"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def _write_bounded_shadow_rehearsal_report(
    payload: dict[str, Any],
    *,
    output_root: str | Path,
) -> dict[str, Any]:
    root = Path(output_root) / BOUNDED_SHADOW_REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    report = {
        "schema_version": "pm_crypto_updown_phase46_bounded_shadow_rehearsal_v1",
        "sequence": "46",
        "status": "BOUNDED_SHADOW_REHEARSAL_SPEC_READY",
        "package_created": True,
        "offline_only": True,
        "candidate_path_status": payload["final_status"],
        "order_routing_enabled": False,
        "order_signing_enabled": False,
        "order_cancellation_enabled": False,
        "wallet_signing_enabled": False,
        "live_trading_enabled": False,
        "execution_authority": "NONE",
    }
    json_path = root / "latest_bounded_shadow_rehearsal.json"
    md_path = root / "latest_bounded_shadow_rehearsal.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(
        "\n".join(
            [
                "# Sequence 46 Bounded Shadow Rehearsal",
                "",
                "Offline-only rehearsal package. No order routing, signing, wallet, cancellation, canary, or live authority.",
                "",
                f"Status: {report['status']}",
                f"Live trading enabled: {report['live_trading_enabled']}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    report["report_paths"] = {"json": str(json_path), "markdown": str(md_path)}
    return report


def _write_next_candidate_handoff(
    payload: dict[str, Any],
    *,
    output_root: str | Path,
) -> dict[str, Any]:
    root = Path(output_root) / NEXT_HANDOFF_REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    report = {
        "schema_version": "pm_crypto_updown_phase46_next_candidate_handoff_v1",
        "sequence": "46",
        "status": "NEXT_CANDIDATE_HANDOFF_READY",
        "deprioritized_candidate": "pm_crypto_updown_repricing_lag",
        "final_status": payload["final_status"],
        "exact_blocker": payload["blockers"],
        "revival_requirements": [
            "at least 5 allowed primary intents",
            "at least 3 allowed real-cached intents",
            "candidate separates from market/no-skill/placebo baselines",
            "anti-overfit guard passes without one-row dominance",
        ],
        "next_candidate_families": [
            "pm_lp_refresh_lag_arbitrage",
            "pm_stale_lp_quote_arbitrage",
        ],
        "required_future_data": [
            "CLOB snapshots",
            "public trade/fill events",
            "quote refresh timestamps",
            "two-sided LP behavior",
            "spot directional triggers",
            "taker burst detection",
        ],
        "guardrails": [
            "no copy trading",
            "no wallet mirroring",
            "no authenticated trading",
            "no order placement or cancellation",
        ],
        "live_trading_enabled": False,
        "execution_authority": "NONE",
    }
    json_path = root / "latest_next_candidate_handoff.json"
    md_path = root / "latest_next_candidate_handoff.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 46 Next Candidate Handoff",
        "",
        "Reference-only handoff. This is not execution logic.",
        "",
        f"Final status: {report['final_status']}",
        "",
        "## Why This Candidate Was Stopped",
    ]
    lines.extend(f"- {item}" for item in report["exact_blocker"])
    lines.extend(["", "## Next Candidate Families"])
    lines.extend(f"- {item}" for item in report["next_candidate_families"])
    lines.extend(["", "## Required Future Data"])
    lines.extend(f"- {item}" for item in report["required_future_data"])
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in report["guardrails"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report["report_paths"] = {"json": str(json_path), "markdown": str(md_path)}
    return report
