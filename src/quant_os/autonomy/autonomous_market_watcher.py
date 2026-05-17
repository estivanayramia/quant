from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quant_os.readiness.canary_readiness_common import (
    load_gate_payload,
    safety_payload,
    utc_now,
    write_json_markdown_report,
)

REPORT_DIR = Path("reports/autonomous_live_fire_drill/watcher")
STATE_DIR = Path("reports/autonomous_live_fire_drill/state")
STATE_JSON = STATE_DIR / "latest_state.json"
STATE_MD = STATE_DIR / "latest_state.md"


def build_autonomous_market_watcher(
    *,
    output_root: str | Path = ".",
    now_ts: str | None = None,
    market_payload: dict[str, Any] | None = None,
    forecast_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    now_ts = now_ts or utc_now()
    market_payload = market_payload or load_gate_payload(
        "reports/first_dollar_preflight/current_market/latest_current_market_eligibility.json",
        output_root=output_root,
    ) or {"status": "CURRENT_MARKET_ELIGIBILITY_NO_CURRENT_MARKET", "market": None}
    forecast_payload = forecast_payload or market_payload.get("forecast_evidence")
    market = market_payload.get("market")
    blockers: list[str] = []
    state = "eligible"
    if not market:
        state = "no current market"
        blockers.append("NO_CURRENT_MARKET")
    elif market.get("status") not in {None, "active", "open"}:
        state = "closed"
        blockers.append("MARKET_CLOSED")
    elif not forecast_payload:
        state = "missing forecast"
        blockers.append("MISSING_FORECAST")
    elif _is_stale(str(market.get("orderbook_ts") or ""), now_ts, max_age_minutes=10):
        state = "stale"
        blockers.append("STALE_DATA")
    elif float(market.get("spread") or 0.0) > 0.05:
        state = "spread too wide"
        blockers.append("SPREAD_TOO_WIDE")
    elif float(market.get("liquidity") or 0.0) < 5.0:
        state = "liquidity too thin"
        blockers.append("LIQUIDITY_TOO_THIN")
    elif not forecast_payload.get("bucket_match", True):
        state = "price discipline blocked"
        blockers.append("PRICE_DISCIPLINE_BLOCKED")
    elif forecast_payload.get("source_blocked"):
        state = "source blocked"
        blockers.append("SOURCE_BLOCKED")

    status = "AUTONOMOUS_WATCHER_READY" if not blockers else "AUTONOMOUS_WATCHER_NO_ELIGIBLE_MARKET"
    if "SOURCE_BLOCKED" in blockers:
        status = "AUTONOMOUS_WATCHER_BLOCKED"
    market_hash = market_payload.get("market_evidence_hash") or (market or {}).get("market_evidence_hash")
    forecast_hash = market_payload.get("forecast_evidence_hash") or (forecast_payload or {}).get("evidence_hash")
    return safety_payload(
        schema_version="autonomous_market_watcher_v1",
        status=status,
        allowed_statuses=[
            "AUTONOMOUS_WATCHER_READY",
            "AUTONOMOUS_WATCHER_NO_ELIGIBLE_MARKET",
            "AUTONOMOUS_WATCHER_BLOCKED",
        ],
        observed_at=now_ts,
        approved_public_series=["KXHIGHNY", "KXHIGHLAX", "KXHIGHAUS"],
        market_state=state,
        classification_reasons=blockers,
        blockers=blockers,
        market=market,
        forecast_evidence=forecast_payload,
        market_evidence_hash=market_hash,
        forecast_evidence_hash=forecast_hash,
        no_lookahead_enforced=True,
        public_read_only=True,
        authenticated_endpoint_called=False,
        request_signing_enabled=False,
        api_keys_loaded=False,
        private_keys_loaded=False,
        checked_account_balance=False,
        checked_portfolio=False,
        next_action="Run autonomous decision engine."
        if status == "AUTONOMOUS_WATCHER_READY"
        else "Continue data-only public monitoring.",
    )


def write_autonomous_market_watcher_report(
    *,
    output_root: str | Path = ".",
    now_ts: str | None = None,
    market_payload: dict[str, Any] | None = None,
    forecast_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = build_autonomous_market_watcher(
        output_root=output_root,
        now_ts=now_ts,
        market_payload=market_payload,
        forecast_payload=forecast_payload,
    )
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_watcher.json",
        md_name="latest_watcher.md",
        title="Autonomous Live Fire-Drill Watcher",
        summary="Public read-only watcher. No credentials, auth, orders, cancels, or signing.",
    )
    _write_state(output_root=output_root, watcher_payload=payload)
    return payload


def _is_stale(ts: str, now_ts: str, *, max_age_minutes: int) -> bool:
    if not ts:
        return True
    try:
        data_ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        now = datetime.fromisoformat(now_ts.replace("Z", "+00:00"))
    except ValueError:
        return True
    if data_ts.tzinfo is None:
        data_ts = data_ts.replace(tzinfo=UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    return (now - data_ts).total_seconds() > max_age_minutes * 60


def _write_state(*, output_root: str | Path, watcher_payload: dict[str, Any]) -> None:
    root = Path(output_root)
    path = root / STATE_JSON
    existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    observations = list(existing.get("observations", []) or [])
    observations.append(
        {
            "status": watcher_payload["status"],
            "market_state": watcher_payload["market_state"],
            "market_ticker": (watcher_payload.get("market") or {}).get("ticker"),
            "observed_at": watcher_payload["observed_at"],
        }
    )
    state = safety_payload(
        schema_version="autonomous_live_fire_drill_state_v1",
        updated_at=utc_now(),
        current_branch=_current_branch(root),
        current_pr=55,
        current_candidate="pm_weather_forecast_market_mismatch",
        current_market=(watcher_payload.get("market") or {}).get("ticker"),
        fire_drill_stage="watcher",
        observations_count=len(observations),
        fake_intents_count=existing.get("fake_intents_count", 0),
        mock_accepted_count=existing.get("mock_accepted_count", 0),
        mock_rejected_count=existing.get("mock_rejected_count", 0),
        fake_fills_count=existing.get("fake_fills_count", 0),
        fake_no_fills_count=existing.get("fake_no_fills_count", 0),
        fake_cancels_timeouts_count=existing.get("fake_cancels_timeouts_count", 0),
        fake_positions=existing.get("fake_positions", []),
        fake_pnl=existing.get("fake_pnl", {"realized_pnl": 0.0, "mark_to_market_pnl": 0.0}),
        reconciliation_status=existing.get("reconciliation_status", "NOT_RUN"),
        kill_switch_status=existing.get("kill_switch_status", "NOT_RUN"),
        safety_flags={
            "live_trading_enabled": False,
            "execution_authority": "NONE",
            "order_transmission_enabled": False,
            "authenticated_requests_enabled": False,
            "api_keys_loaded": False,
            "private_keys_loaded": False,
            "request_signing_enabled": False,
            "actual_order_count": 0,
            "actual_cancel_count": 0,
        },
        blockers=watcher_payload.get("blockers", []),
        next_action=watcher_payload.get("next_action"),
        exact_resume_command="cd C:\\Users\\estiv\\quant; .\\make.cmd autonomous-live-fire-drill-smoke",
        observations=observations,
        api_keys_loaded=False,
        private_keys_loaded=False,
        request_signing_enabled=False,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    (root / STATE_MD).write_text(
        "\n".join(
            [
                "# Autonomous Live Fire-Drill State",
                "",
                f"Stage: {state['fire_drill_stage']}",
                f"Observations: {state['observations_count']}",
                f"Current market: {state['current_market'] or 'None'}",
                f"Reconciliation: {state['reconciliation_status']}",
                f"Kill switch: {state['kill_switch_status']}",
                f"Next action: {state['next_action']}",
                f"Resume: `{state['exact_resume_command']}`",
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
    return result.stdout.strip() or "unknown"
