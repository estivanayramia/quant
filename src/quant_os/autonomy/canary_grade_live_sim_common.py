from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from quant_os.autonomy.live_market_sim_common import load_json, sim_safety_payload
from quant_os.readiness.canary_readiness_common import utc_now

ROOT = Path("reports/canary_grade_live_sim")
STATE_JSON = ROOT / "state" / "latest_state.json"
STATE_MD = ROOT / "state" / "latest_state.md"
RESUME_COMMAND = ".\\make.cmd canary-grade-live-sim-smoke"


def cg_hash(payload: Any, *, length: int = 16) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:length]


def canary_safe_payload(**fields: Any) -> dict[str, Any]:
    defaults = {
        "request_signing_enabled": False,
        "api_keys_loaded": False,
        "private_keys_loaded": False,
        "authenticated_endpoint_called": False,
        "checked_account_balance": False,
        "checked_portfolio": False,
        "unsafe_action_attempts": 0,
        "auth_key_order_attempts": 0,
        "hidden_local_state_dependency": False,
    }
    defaults.update(fields)
    return sim_safety_payload(**defaults)


def load_canary_state(*, output_root: str | Path = ".") -> dict[str, Any]:
    return load_json(STATE_JSON, output_root=output_root) or empty_canary_state(output_root=output_root)


def write_canary_state(*, output_root: str | Path = ".", **updates: Any) -> dict[str, Any]:
    state = load_canary_state(output_root=output_root)
    state.update(updates)
    state["updated_at"] = utc_now()
    root = Path(output_root)
    path = root / STATE_JSON
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    _write_state_md(root, state)
    return state


def empty_canary_state(*, output_root: str | Path = ".") -> dict[str, Any]:
    return canary_safe_payload(
        schema_version="canary_grade_live_sim_state_v1",
        updated_at=utc_now(),
        branch=_current_branch(Path(output_root)),
        pr="55",
        active_market_family="crypto_spot",
        active_strategy="multi_strategy_canary_grade_crypto_spot",
        assets_tested=[],
        venues_tested=[],
        observations_count=0,
        eligible_intent_count=0,
        fake_fill_count=0,
        fake_no_fill_count=0,
        completed_mark_count=0,
        fake_gross_pnl=0.0,
        fake_net_pnl=0.0,
        fees_spread_slippage_assumptions={},
        baseline_pnl=0.0,
        placebo_pnl=0.0,
        one_trade_dominance=1.0,
        one_window_dominance=1.0,
        regime_buckets=[],
        walk_forward_windows=[],
        validation_status="NOT_RUN",
        blockers=[],
        next_action="Run canary-grade crypto live-sim hardening.",
        exact_resume_command=RESUME_COMMAND,
    )


def update_state_from_payload(*, output_root: str | Path, payload: dict[str, Any]) -> dict[str, Any]:
    return write_canary_state(
        output_root=output_root,
        assets_tested=payload.get("assets_tested", []),
        venues_tested=payload.get("venues_tested", []),
        observations_count=int(payload.get("observation_count") or payload.get("observations_count") or 0),
        eligible_intent_count=int(payload.get("eligible_intent_count") or 0),
        fake_fill_count=int(payload.get("fake_fill_count") or 0),
        fake_no_fill_count=int(payload.get("fake_no_fill_count") or 0),
        completed_mark_count=int(payload.get("completed_mark_count") or 0),
        fake_gross_pnl=float(payload.get("fake_gross_pnl") or 0.0),
        fake_net_pnl=float(payload.get("fake_net_pnl") or 0.0),
        baseline_pnl=float(payload.get("baseline_pnl") or 0.0),
        placebo_pnl=float(payload.get("placebo_pnl") or 0.0),
        regime_buckets=payload.get("regime_buckets", []),
        walk_forward_windows=payload.get("walk_forward_windows", []),
        blockers=payload.get("blockers", []),
        next_action=payload.get("next_action", "Run next canary-grade stage."),
        validation_status=payload.get("status", "UPDATED"),
    )


def _write_state_md(root: Path, state: dict[str, Any]) -> None:
    path = root / STATE_MD
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Canary-Grade Live Sim State",
        "",
        f"Branch: {state.get('branch')}",
        f"PR: {state.get('pr')}",
        f"Validation status: {state.get('validation_status')}",
        f"Active market family: {state.get('active_market_family')}",
        f"Active strategy: {state.get('active_strategy')}",
        f"Assets tested: {', '.join(state.get('assets_tested', []) or [])}",
        f"Venues tested: {', '.join(state.get('venues_tested', []) or [])}",
        f"Observations: {state.get('observations_count', 0)}",
        f"Eligible intents: {state.get('eligible_intent_count', 0)}",
        f"Fake fills: {state.get('fake_fill_count', 0)}",
        f"Completed marks: {state.get('completed_mark_count', 0)}",
        f"Fake net PnL: {state.get('fake_net_pnl', 0.0)}",
        f"Baseline PnL: {state.get('baseline_pnl', 0.0)}",
        f"Placebo PnL: {state.get('placebo_pnl', 0.0)}",
        f"One-trade dominance: {state.get('one_trade_dominance')}",
        f"One-window dominance: {state.get('one_window_dominance')}",
        f"Regimes: {', '.join(state.get('regime_buckets', []) or [])}",
        f"Windows: {', '.join(state.get('walk_forward_windows', []) or [])}",
        f"Blockers: {', '.join(state.get('blockers', []) or ['None'])}",
        f"Next action: {state.get('next_action')}",
        f"Resume: `{state.get('exact_resume_command')}`",
        f"Live trading enabled: {state.get('live_trading_enabled')}",
        f"Execution authority: {state.get('execution_authority')}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
