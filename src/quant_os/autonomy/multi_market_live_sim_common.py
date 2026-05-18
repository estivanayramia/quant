from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from quant_os.autonomy.live_market_sim_common import load_json, sim_safety_payload
from quant_os.readiness.canary_readiness_common import utc_now

ROOT = Path("reports/multi_market_live_sim")
STATE_JSON = ROOT / "state" / "latest_state.json"
STATE_MD = ROOT / "state" / "latest_state.md"
RESUME_COMMAND = ".\\make.cmd multi-market-live-sim-smoke"


def mm_hash(payload: Any, *, length: int = 16) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:length]


def load_multi_market_state(*, output_root: str | Path = ".") -> dict[str, Any]:
    return load_json(STATE_JSON, output_root=output_root) or empty_multi_market_state(output_root=output_root)


def write_multi_market_state(*, output_root: str | Path = ".", **updates: Any) -> dict[str, Any]:
    state = load_multi_market_state(output_root=output_root)
    state.update(updates)
    state["updated_at"] = utc_now()
    root = Path(output_root)
    path = root / STATE_JSON
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    _write_state_md(root, state)
    return state


def empty_multi_market_state(*, output_root: str | Path = ".") -> dict[str, Any]:
    return sim_safety_payload(
        schema_version="multi_market_live_sim_state_v1",
        updated_at=utc_now(),
        current_branch=_current_branch(Path(output_root)),
        current_pr="55",
        status="MULTI_MARKET_LIVE_SIM_CHECKPOINTED_NOT_COMPLETE",
        exact_resume_command=RESUME_COMMAND,
        market_families={
            "weather_prediction_markets": _family("weather_prediction_markets"),
            "crypto_spot": _family("crypto_spot"),
            "prediction_market_structural": _family("prediction_market_structural"),
            "etf_equity": _family("etf_equity"),
        },
        hidden_local_state_dependency=False,
        unsafe_action_attempts=0,
        auth_key_order_attempts=0,
    )


def family_from_payload(market_family: str, payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = payload or {}
    return _family(
        market_family,
        status=payload.get("status", "NOT_RUN"),
        observations_count=int(payload.get("observation_count") or payload.get("observations_count") or 0),
        eligible_fake_intents_count=int(payload.get("eligible_intent_count") or 0),
        fake_fills_count=int(payload.get("fake_fill_count") or 0),
        fake_no_fill_count=int(payload.get("fake_no_fill_count") or 0),
        resolved_outcomes_or_future_marks_count=int(
            payload.get("resolved_outcome_count") or payload.get("completed_mark_count") or 0
        ),
        pending_outcomes_count=int(payload.get("pending_outcome_count") or 0),
        fake_gross_pnl=float(payload.get("fake_gross_pnl") or 0.0),
        fake_net_pnl=float(payload.get("fake_net_pnl") or 0.0),
        baseline_pnl=float(payload.get("baseline_pnl") or 0.0),
        placebo_pnl=float(payload.get("placebo_pnl") or 0.0),
        reconciliation_status=payload.get("reconciliation_status") or payload.get("status", "NOT_RUN"),
        blockers=list(payload.get("blockers", []) or []),
        next_action=payload.get("next_action", "Run the next safe data-only stage."),
        active_instruments=payload.get("active_instruments", []),
    )


def safe_report_payload(**fields: Any) -> dict[str, Any]:
    defaults = {
        "request_signing_enabled": False,
        "api_keys_loaded": False,
        "private_keys_loaded": False,
        "authenticated_endpoint_called": False,
        "checked_account_balance": False,
        "checked_portfolio": False,
    }
    defaults.update(fields)
    return sim_safety_payload(**defaults)


def _family(
    market_family: str,
    *,
    status: str = "NOT_RUN",
    observations_count: int = 0,
    eligible_fake_intents_count: int = 0,
    fake_fills_count: int = 0,
    fake_no_fill_count: int = 0,
    resolved_outcomes_or_future_marks_count: int = 0,
    pending_outcomes_count: int = 0,
    fake_gross_pnl: float = 0.0,
    fake_net_pnl: float = 0.0,
    baseline_pnl: float = 0.0,
    placebo_pnl: float = 0.0,
    reconciliation_status: str = "NOT_RUN",
    blockers: list[str] | None = None,
    next_action: str = "Not started.",
    active_instruments: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "market_family": market_family,
        "active_instruments": active_instruments or [],
        "observations_count": observations_count,
        "eligible_fake_intents_count": eligible_fake_intents_count,
        "fake_fills_count": fake_fills_count,
        "fake_no_fill_count": fake_no_fill_count,
        "resolved_outcomes_or_future_marks_count": resolved_outcomes_or_future_marks_count,
        "pending_outcomes_count": pending_outcomes_count,
        "fake_gross_pnl": round(fake_gross_pnl, 6),
        "fake_net_pnl": round(fake_net_pnl, 6),
        "baseline_pnl": round(baseline_pnl, 6),
        "placebo_pnl": round(placebo_pnl, 6),
        "reconciliation_status": reconciliation_status,
        "status": status,
        "blockers": blockers or [],
        "next_action": next_action,
        "exact_resume_command": RESUME_COMMAND,
        "safety_flags": sim_safety_payload(),
    }


def _write_state_md(root: Path, state: dict[str, Any]) -> None:
    path = root / STATE_MD
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Multi-Market Live Sim State",
        "",
        f"Status: {state.get('status')}",
        f"Current branch: {state.get('current_branch')}",
        f"Current PR: {state.get('current_pr')}",
        f"Resume: `{state.get('exact_resume_command')}`",
        "",
    ]
    for family, payload in (state.get("market_families") or {}).items():
        lines.extend(
            [
                f"## {family}",
                f"- Status: {payload.get('status')}",
                f"- Observations: {payload.get('observations_count', 0)}",
                f"- Eligible fake intents: {payload.get('eligible_fake_intents_count', 0)}",
                f"- Fake fills: {payload.get('fake_fills_count', 0)}",
                f"- Completed marks/outcomes: {payload.get('resolved_outcomes_or_future_marks_count', 0)}",
                f"- Pending outcomes: {payload.get('pending_outcomes_count', 0)}",
                f"- Fake net PnL: {payload.get('fake_net_pnl', 0.0)}",
                f"- Reconciliation: {payload.get('reconciliation_status')}",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def _current_branch(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return "unknown"
    return result.stdout.strip() or "unknown"
