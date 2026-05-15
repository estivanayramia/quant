from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.research.replay_candidates.pm_crypto_updown_schema import CANDIDATE_ID
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

REPORT_ROOT = Path("reports/sequence45/bounded_shadow_rehearsal")


def build_pm_crypto_updown_bounded_shadow_rehearsal_report(
    *,
    candidate_decision: dict[str, Any],
) -> dict[str, Any]:
    ready = bool(candidate_decision.get("ready_for_bounded_shadow_rehearsal"))
    if not ready:
        return {
            "schema_version": "pm_crypto_updown_bounded_shadow_rehearsal_report_v1",
            "sequence": "45",
            "candidate_id": CANDIDATE_ID,
            "status": "BOUNDED_SHADOW_REHEARSAL_BLOCKED",
            "package_created": False,
            "blocked_reason": candidate_decision.get("decision_status"),
            "blockers": candidate_decision.get("blockers", []),
            "offline_only": True,
            "network_fetch_attempted": False,
            **SOCIAL_INTAKE_SAFETY,
            "live_allowed": False,
            "live_promotion_status": "LIVE_BLOCKED",
            "evidence_only": True,
        }
    return {
        "schema_version": "pm_crypto_updown_bounded_shadow_rehearsal_report_v1",
        "sequence": "45",
        "candidate_id": CANDIDATE_ID,
        "status": "BOUNDED_SHADOW_REHEARSAL_SPEC_READY",
        "package_created": True,
        "offline_only": True,
        "rehearsal_duration": "5 resolved UP/DOWN windows or 1 local operator session, whichever ends first",
        "max_intents_per_window": 1,
        "max_nominal_hypothetical_exposure_usd": 10.0,
        "risk_blockers": [
            "live trading remains disabled",
            "candidate decision must stay READY_FOR_BOUNDED_SHADOW_REHEARSAL",
            "cost/fill policy must keep nonzero conservative intents",
            "anti-overfit guard must remain passing",
            "baseline/placebo separation must remain passing",
        ],
        "required_reports": [
            "reports/sequence45/candidate_decision/latest_pm_crypto_updown_candidate_decision.json",
            "reports/sequence45/baseline_placebo/latest_baseline_placebo_update.json",
            "reports/sequence45/overfit_guard/latest_overfit_guard_update.json",
            "reports/sequence45/bounded_shadow_rehearsal/latest_bounded_shadow_rehearsal.json",
        ],
        "stop_conditions": [
            "decision gate no longer ready",
            "allowed primary intents fall below threshold",
            "allowed real-cached intents fall below threshold",
            "one-row dominance appears",
            "any live/canary/execution authority appears",
        ],
        "failure_conditions": [
            "baseline or placebo regains dominance",
            "cost/fill adjusted result is not positive",
            "synthetic rows become primary proof",
            "operator attempts live routing or wallet access",
        ],
        "next_validation_commands": [
            ".\\make.cmd sequence45-smoke",
            ".\\make.cmd sequence44-smoke",
            "python -m quant_os.cli guard-live",
        ],
        "order_routing_enabled": False,
        "order_signing_enabled": False,
        "order_cancellation_enabled": False,
        "wallet_signing_enabled": False,
        "network_fetch_attempted": False,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_pm_crypto_updown_bounded_shadow_rehearsal_report(
    *,
    candidate_decision: dict[str, Any],
    output_root: str | Path = ".",
) -> dict[str, Any]:
    payload = build_pm_crypto_updown_bounded_shadow_rehearsal_report(
        candidate_decision=candidate_decision,
    )
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_bounded_shadow_rehearsal.json"
    md_path = root / "latest_bounded_shadow_rehearsal.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 45 Bounded Shadow Rehearsal",
        "",
        "Offline-only bounded shadow rehearsal package or blocked report.",
        "",
        f"Status: {payload['status']}",
        f"Package created: {payload['package_created']}",
        f"Offline only: {payload['offline_only']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        f"Execution authority: {payload['execution_authority']}",
    ]
    if payload["package_created"]:
        lines.extend(
            [
                f"Max intents per window: {payload['max_intents_per_window']}",
                f"Max nominal hypothetical exposure USD: {payload['max_nominal_hypothetical_exposure_usd']}",
                "",
                "## Stop Conditions",
            ]
        )
        lines.extend(f"- {item}" for item in payload["stop_conditions"])
    else:
        lines.extend(["", "## Blockers"])
        lines.extend(f"- {item}" for item in payload["blockers"] or ["None"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
