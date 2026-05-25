from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from quant_os.data.weather.current_weather_forecast_match import write_current_forecast_match_report
from quant_os.data.weather.current_weather_market_discovery import (
    write_current_weather_market_discovery_report,
)
from quant_os.readiness.canary_readiness_common import (
    load_gate_payload,
    safety_payload,
    utc_now,
    write_json_markdown_report,
)
from quant_os.readiness.current_market_eligibility import write_current_market_eligibility_report
from quant_os.readiness.first_dollar_preflight import write_first_dollar_preflight_report

REPORT_DIR = Path("reports/live_market_paper_rehearsal/observer")
STATE_DIR = Path("reports/live_market_paper_rehearsal/state")
STATE_JSON = STATE_DIR / "latest_state.json"
STATE_MD = STATE_DIR / "latest_state.md"


def build_live_market_paper_observer(
    *,
    output_root: str | Path = ".",
    now_ts: str | None = None,
    current_market_payload: dict[str, Any] | None = None,
    preflight_payload: dict[str, Any] | None = None,
    public_network_ok: bool = False,
) -> dict[str, Any]:
    now_ts = now_ts or utc_now()
    if public_network_ok and current_market_payload is None:
        write_current_weather_market_discovery_report(
            output_root=output_root,
            public_network_ok=True,
        )
        write_current_forecast_match_report(output_root=output_root, public_network_ok=True)
        current_market_payload = write_current_market_eligibility_report(output_root=output_root)
        preflight_payload = write_first_dollar_preflight_report(output_root=output_root)
    current_market_payload = current_market_payload or load_gate_payload(
        "reports/first_dollar_preflight/current_market/latest_current_market_eligibility.json",
        output_root=output_root,
    ) or {}
    preflight_payload = preflight_payload or load_gate_payload(
        "reports/first_dollar_preflight/final/latest_first_dollar_preflight.json",
        output_root=output_root,
    ) or {}
    market = current_market_payload.get("market")
    forecast = current_market_payload.get("forecast_evidence") or {}
    eligible = current_market_payload.get("status") == "CURRENT_MARKET_ELIGIBILITY_PASSED"
    preflight_ready = preflight_payload.get("status") == "FIRST_DOLLAR_PREFLIGHT_READY"
    no_current_market = (
        current_market_payload.get("status") == "CURRENT_MARKET_ELIGIBILITY_NO_CURRENT_MARKET"
        or preflight_payload.get("status") == "FIRST_DOLLAR_PREFLIGHT_STRUCTURALLY_READY_NO_CURRENT_MARKET"
    )
    blockers: list[str] = []
    if eligible:
        status = "LIVE_MARKET_OBSERVATION_READY"
        observation_kind = "ELIGIBLE_MARKET"
    elif no_current_market:
        status = "LIVE_MARKET_OBSERVATION_NO_ELIGIBLE_MARKET"
        observation_kind = "NO_CURRENT_ELIGIBLE_MARKET"
    else:
        status = "LIVE_MARKET_OBSERVATION_BLOCKED"
        observation_kind = "MARKET_OR_FORECAST_BLOCKED"
        blockers.extend(current_market_payload.get("blockers", []) or ["CURRENT_MARKET_NOT_ELIGIBLE"])
    data_ts = (market or {}).get("orderbook_ts") or forecast.get("known_at_ts") or now_ts
    observation = {
        "observation_id": _observation_id(
            data_ts=str(data_ts),
            market=market,
            observation_kind=observation_kind,
            current_market_status=current_market_payload.get("status"),
            blockers=current_market_payload.get("blockers", []) or [],
        ),
        "observed_at": now_ts,
        "data_ts": data_ts,
        "observation_kind": observation_kind,
        "eligible_market": eligible,
        "preflight_ready": preflight_ready,
        "preflight_status": preflight_payload.get("status"),
        "current_market_status": current_market_payload.get("status"),
        "market": market,
        "forecast_evidence": forecast,
        "market_evidence_hash": current_market_payload.get("market_evidence_hash")
        or (market or {}).get("market_evidence_hash"),
        "forecast_evidence_hash": current_market_payload.get("forecast_evidence_hash")
        or forecast.get("evidence_hash"),
        "source_reports": {
            "preflight": "reports/first_dollar_preflight/final/latest_first_dollar_preflight.json",
            "current_market": "reports/first_dollar_preflight/current_market/latest_current_market_eligibility.json",
        },
    }
    payload = safety_payload(
        schema_version="live_market_paper_observer_v1",
        status=status,
        allowed_statuses=[
            "LIVE_MARKET_OBSERVATION_READY",
            "LIVE_MARKET_OBSERVATION_NO_ELIGIBLE_MARKET",
            "LIVE_MARKET_OBSERVATION_BLOCKED",
        ],
        public_read_only=True,
        public_network_used=public_network_ok,
        public_network_optional_flag="--public-network-ok",
        authenticated_endpoint_called=False,
        checked_account_balance=False,
        checked_portfolio=False,
        observation=observation,
        observation_id=observation["observation_id"],
        market=market,
        forecast_evidence=forecast,
        blockers=blockers,
        api_keys_loaded=False,
        private_keys_loaded=False,
        next_action="Generate fake-money no-transmit paper intent."
        if eligible
        else "Keep scanning public markets and record no-current-market observations."
        if no_current_market
        else "Keep scanning public markets until eligibility passes.",
    )
    return payload


def write_live_market_paper_observer_report(
    *,
    output_root: str | Path = ".",
    now_ts: str | None = None,
    current_market_payload: dict[str, Any] | None = None,
    preflight_payload: dict[str, Any] | None = None,
    public_network_ok: bool = False,
) -> dict[str, Any]:
    payload = build_live_market_paper_observer(
        output_root=output_root,
        now_ts=now_ts,
        current_market_payload=current_market_payload,
        preflight_payload=preflight_payload,
        public_network_ok=public_network_ok,
    )
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_observer.json",
        md_name="latest_observer.md",
        title="Live Market Paper Observer",
        summary="Public read-only live-market paper observation. No credentials, auth, orders, cancels, or signing.",
    )
    _write_state(output_root=output_root, observer_payload=payload)
    return payload


def _observation_id(
    *,
    data_ts: str,
    market: dict[str, Any] | None,
    observation_kind: str,
    current_market_status: str | None,
    blockers: list[str],
) -> str:
    raw = json.dumps(
        {
            "data_ts": data_ts,
            "ticker": (market or {}).get("ticker"),
            "kind": observation_kind,
            "current_market_status": current_market_status,
            "blockers": sorted(blockers),
        },
        sort_keys=True,
    )
    return f"obs_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _write_state(*, output_root: str | Path, observer_payload: dict[str, Any]) -> None:
    root = Path(output_root)
    state_path = root / STATE_JSON
    existing: dict[str, Any] = {}
    if state_path.exists():
        existing = json.loads(state_path.read_text(encoding="utf-8"))
    observations = list(existing.get("observations", []) or [])
    observation = observer_payload["observation"]
    if observation["observation_id"] not in {item.get("observation_id") for item in observations}:
        observations.append(observation)
    state = safety_payload(
        schema_version="live_market_paper_rehearsal_state_v1",
        updated_at=utc_now(),
        current_branch=_current_branch(root),
        active_market=(observation.get("market") or {}).get("ticker"),
        observation_count=len(observations),
        observations=observations,
        no_transmit_intents_generated=existing.get("no_transmit_intents_generated", 0),
        fake_fills=existing.get("fake_fills", 0),
        fake_position_state=existing.get("fake_position_state", "NO_POSITION"),
        fake_pnl=existing.get("fake_pnl", {"mark_to_market_pnl": 0.0, "realized_pnl": 0.0}),
        fake_reconciliation_state=existing.get("fake_reconciliation_state", "NOT_RUN"),
        pending_resolutions=existing.get("pending_resolutions", []),
        blockers=observer_payload.get("blockers", []),
        next_action=observer_payload.get("next_action"),
        exact_resume_command=(
            "python -m quant_os.cli autonomy live-market-paper-observer --public-network-ok"
        ),
        api_keys_loaded=False,
        private_keys_loaded=False,
    )
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    md_path = root / STATE_MD
    md_path.write_text(
        "\n".join(
            [
                "# Live Market Paper Rehearsal State",
                "",
                f"Observation count: {state['observation_count']}",
                f"Active market: {state['active_market'] or 'None'}",
                f"Fake position state: {state['fake_position_state']}",
                f"Reconciliation state: {state['fake_reconciliation_state']}",
                f"Next action: {state['next_action']}",
                f"Resume: `{state['exact_resume_command']}`",
                f"Live trading enabled: {state['live_trading_enabled']}",
                f"Execution authority: {state['execution_authority']}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


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
    branch = result.stdout.strip()
    return branch or "unknown"
