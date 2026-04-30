from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quant_os.data.loaders import load_yaml

CANARY_ROOT = Path("reports/canary")
POLICY_JSON = CANARY_ROOT / "latest_policy.json"
POLICY_MD = CANARY_ROOT / "latest_policy.md"
CONFIG_PATH = Path("configs/live_canary.yaml")


def load_canary_config(config_path: str | Path = CONFIG_PATH) -> dict[str, Any]:
    path = Path(config_path)
    if not path.exists():
        return {
            "enabled": False,
            "live_trading_allowed": False,
            "paper_trading_allowed": False,
            "dry_run_required": True,
            "human_approval_required": True,
            "exchange_keys_allowed": False,
            "withdrawal_permissions_allowed": False,
            "futures_allowed": False,
            "margin_allowed": False,
            "leverage_allowed": False,
            "shorting_allowed": False,
            "options_allowed": False,
            "preflight": {},
            "capital_ladder": {
                "stage_0": {"label": "planning_only", "max_order_notional": 0, "live_allowed": False}
            },
        }
    return load_yaml(path)


def build_canary_policy(write: bool = True) -> dict[str, Any]:
    config = load_canary_config()
    payload = {
        "status": "PLANNING_ONLY",
        "generated_at": datetime.now(UTC).isoformat(),
        "objective": "Define future tiny crypto spot canary gates without enabling live trading.",
        "not_profit_phase": True,
        "planning_and_gating_only": True,
        "live_trading_enabled": False,
        "live_trading_allowed": bool(config.get("live_trading_allowed", False)),
        "allowed_market_future": "crypto_spot_only",
        "forbidden_markets": ["equities_live", "futures", "margin", "leverage", "shorts", "options"],
        "future_order_limits": {
            "max_order_notional_stage_1_usd": 25,
            "max_open_positions": 1,
            "max_daily_loss_usd": 10,
            "max_weekly_loss_usd": 25,
        },
        "required_controls": [
            "kill_switch",
            "strategy_quarantine",
            "deterministic_risk_firewall",
            "stoploss_on_exchange_future_proof",
            "restricted_exchange_permissions",
            "withdrawals_disabled",
            "ip_allowlist_future",
            "human_approval",
            "rollback_runbook",
            "incident_response_runbook",
        ],
        "proof_thresholds_before_consideration": {
            "proving_status": config.get("preflight", {}).get("require_proving_status", "DRY_RUN_PROVEN"),
            "minimum_successful_runs_future": config.get("preflight", {}).get(
                "require_min_successful_runs_future", 14
            ),
            "zero_unresolved_incidents": True,
            "trade_reconciliation_required": True,
            "historical_evidence_required": True,
            "dryrun_monitoring_required": True,
        },
        "live_promotion_status": "LIVE_BLOCKED",
        "next_commands": [
            "make.cmd canary-checklist",
            "make.cmd canary-preflight",
            "make.cmd canary-readiness",
        ],
    }
    if write:
        write_canary_report(POLICY_JSON, POLICY_MD, "Tiny-Live Canary Policy", payload)
    return payload


def write_canary_report(json_path: Path, md_path: Path, title: str, payload: dict[str, Any]) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")
    lines = [
        f"# {title}",
        "",
        "Planning/gating only. Live trading is disabled. No real orders are possible. No keys are used.",
        "",
        f"Status: {payload.get('status', payload.get('readiness_status', 'UNKNOWN'))}",
        f"Live promotion: {payload.get('live_promotion_status', 'LIVE_BLOCKED')}",
        "",
    ]
    blockers = payload.get("blockers") or []
    if blockers:
        lines.append("## Blockers")
        lines.extend(f"- {item}" for item in blockers)
        lines.append("")
    warnings = payload.get("warnings") or []
    if warnings:
        lines.append("## Warnings")
        lines.extend(f"- {item}" for item in warnings)
        lines.append("")
    next_commands = payload.get("next_commands") or []
    if next_commands:
        lines.append("## Next Commands")
        lines.extend(f"- `{command}`" for command in next_commands)
        lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
