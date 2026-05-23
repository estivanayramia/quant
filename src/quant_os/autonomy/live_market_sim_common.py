from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from quant_os.readiness.canary_readiness_common import safety_payload, utc_now

ROOT = Path("reports/live_market_sim_profitability")
STATE_DIR = ROOT / "state"
STATE_JSON = STATE_DIR / "latest_state.json"
STATE_MD = STATE_DIR / "latest_state.md"
RESUME_COMMAND = ".\\make.cmd live-market-sim-profitability-public-run"
ACTIVE_POLICY_VERSION = "strict_weather_yes_v3_public_l2_costed_no_near_certain_opposite"


def sim_safety_payload(**overrides: Any) -> dict[str, Any]:
    defaults = {
        "request_signing_enabled": False,
        "api_keys_loaded": False,
        "private_keys_loaded": False,
        "authenticated_endpoint_called": False,
        "checked_account_balance": False,
        "checked_portfolio": False,
    }
    defaults.update(overrides)
    return safety_payload(**defaults)


def hash_payload(payload: Any, *, length: int = 16) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:length]


def load_json(path: str | Path, *, output_root: str | Path = ".") -> dict[str, Any] | None:
    resolved = Path(output_root) / Path(path)
    if not resolved.exists():
        return None
    return json.loads(resolved.read_text(encoding="utf-8"))


def load_state(*, output_root: str | Path = ".") -> dict[str, Any]:
    return load_json(STATE_JSON, output_root=output_root) or _empty_state(output_root=output_root)


def write_state(*, output_root: str | Path = ".", **updates: Any) -> dict[str, Any]:
    state = load_state(output_root=output_root)
    for key, value in updates.items():
        if isinstance(value, list) and key in {"observations", "intents", "fills", "ledger_entries"}:
            state[key] = _merge_by_id(list(state.get(key, []) or []), value)
        else:
            state[key] = value
    _refresh_counts(state)
    state["updated_at"] = utc_now()
    root = Path(output_root)
    path = root / STATE_JSON
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    _write_state_md(root, state)
    return state


def reset_state(
    *,
    output_root: str | Path = ".",
    previous_run_archive: str | None = None,
    previous_run_status: str | None = None,
) -> dict[str, Any]:
    state = _empty_state(output_root=output_root)
    state["previous_run_archive"] = previous_run_archive
    state["previous_run_status"] = previous_run_status
    root = Path(output_root)
    path = root / STATE_JSON
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    _write_state_md(root, state)
    return state


def _empty_state(*, output_root: str | Path) -> dict[str, Any]:
    root = Path(output_root)
    now = utc_now()
    branch = _current_branch(root)
    return sim_safety_payload(
        schema_version="live_market_sim_profitability_state_v1",
        updated_at=now,
        current_branch=branch,
        current_pr="55",
        run_id=f"lmsr_{hash_payload({'branch': branch, 'ts': now})}",
        active_policy_version=ACTIVE_POLICY_VERSION,
        active_candidate="pm_weather_forecast_market_mismatch",
        market_series_watched=["KXHIGHNY", "KXHIGHAUS", "KXHIGHCHI", "KXHIGHMIA", "KXHIGHLAX"],
        observations=[],
        intents=[],
        fills=[],
        no_fills=[],
        ledger_entries=[],
        outcomes=[],
        observations_count=0,
        eligible_intent_count=0,
        fake_fill_count=0,
        fake_no_fill_count=0,
        resolved_outcome_count=0,
        pending_outcome_count=0,
        fake_gross_pnl=0.0,
        fake_net_pnl=0.0,
        baseline_pnl=0.0,
        placebo_pnl=0.0,
        reconciliation_status="NOT_RUN",
        current_blockers=[],
        next_action="Run live-market simulated profitability observation.",
        exact_resume_command=RESUME_COMMAND,
        hidden_local_state_dependency=False,
        unsafe_action_attempts=0,
        auth_key_order_attempts=0,
    )


def _merge_by_id(existing: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ids = {
        item.get("observation_id")
        or item.get("fake_client_order_id")
        or item.get("fake_fill_id")
        or item.get("ledger_entry_id")
        for item in existing
    }
    merged = list(existing)
    for item in incoming:
        key = (
            item.get("observation_id")
            or item.get("fake_client_order_id")
            or item.get("fake_fill_id")
            or item.get("ledger_entry_id")
        )
        if key not in ids:
            merged.append(item)
            ids.add(key)
    return merged


def _refresh_counts(state: dict[str, Any]) -> None:
    observations = list(state.get("observations", []) or [])
    intents = list(state.get("intents", []) or [])
    fills = list(state.get("fills", []) or [])
    no_fills = list(state.get("no_fills", []) or [])
    outcomes = list(state.get("outcomes", []) or [])
    state["observations_count"] = len(observations)
    state["eligible_intent_count"] = len(intents)
    state["fake_fill_count"] = len(fills)
    state["fake_no_fill_count"] = len(no_fills)
    state["resolved_outcome_count"] = len([item for item in outcomes if item.get("outcome_status") == "RESOLVED"])
    state["pending_outcome_count"] = len([item for item in outcomes if item.get("outcome_status") == "PENDING"])


def _write_state_md(root: Path, state: dict[str, Any]) -> None:
    md = root / STATE_MD
    md.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Live Market Simulated Profitability State",
        "",
        f"Current branch: {state.get('current_branch')}",
        f"Current PR: {state.get('current_pr')}",
        f"Run ID: {state.get('run_id')}",
        f"Active policy version: {state.get('active_policy_version')}",
        f"Active candidate: {state.get('active_candidate')}",
        f"Market series watched: {', '.join(state.get('market_series_watched', []))}",
        f"Observations count: {state.get('observations_count', 0)}",
        f"Eligible intent count: {state.get('eligible_intent_count', 0)}",
        f"Fake fill count: {state.get('fake_fill_count', 0)}",
        f"Fake no-fill count: {state.get('fake_no_fill_count', 0)}",
        f"Resolved outcome count: {state.get('resolved_outcome_count', 0)}",
        f"Pending outcome count: {state.get('pending_outcome_count', 0)}",
        f"Fake gross PnL: {state.get('fake_gross_pnl', 0.0)}",
        f"Fake net PnL: {state.get('fake_net_pnl', 0.0)}",
        f"Baseline PnL: {state.get('baseline_pnl', 0.0)}",
        f"Placebo PnL: {state.get('placebo_pnl', 0.0)}",
        f"Reconciliation status: {state.get('reconciliation_status')}",
        f"Current blockers: {', '.join(state.get('current_blockers', []) or ['None'])}",
        f"Previous run archive: {state.get('previous_run_archive')}",
        f"Previous run status: {state.get('previous_run_status')}",
        f"Next action: {state.get('next_action')}",
        f"Resume: `{state.get('exact_resume_command')}`",
        f"Live trading enabled: {state.get('live_trading_enabled')}",
        f"Execution authority: {state.get('execution_authority')}",
    ]
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
