from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quant_os.canary.arm_token import validate_arm_token
from quant_os.canary.final_gate import evaluate_final_gate
from quant_os.canary.permissions_import import validate_latest_permission_manifest
from quant_os.canary.stoploss_proof import build_stoploss_proof
from quant_os.governance.live_canary_approval import live_canary_approval_guard
from quant_os.live_canary.adapter import build_live_canary_adapter
from quant_os.live_canary.config import live_execution_safety_blockers, load_live_execution_config
from quant_os.live_canary.credential_loader import load_live_credentials
from quant_os.live_canary.exchange_port import LiveCanaryExchangePort
from quant_os.live_canary.live_kill_switch import KILL_SWITCH_PATH, read_live_kill_switch
from quant_os.live_canary.notional_limits import validate_notional_limit
from quant_os.live_canary.reporting import LIVE_CANARY_ROOT, write_live_canary_report
from quant_os.live_canary.symbol_allowlist import validate_symbol_allowed
from quant_os.proving.incident_log import summarize_incidents
from quant_os.proving.readiness import evaluate_proving_readiness
from quant_os.security.live_exchange_guard import live_exchange_guard
from quant_os.security.live_trading_guard import live_trading_guard
from quant_os.security.stoploss_exchange_guard import stoploss_exchange_guard

PREPARE_JSON = LIVE_CANARY_ROOT / "latest_prepare.json"
PREPARE_MD = LIVE_CANARY_ROOT / "latest_prepare.md"
PREFLIGHT_JSON = LIVE_CANARY_ROOT / "latest_preflight.json"
PREFLIGHT_MD = LIVE_CANARY_ROOT / "latest_preflight.md"


def prepare_live_canary(
    *,
    credential_path: str | Path | None = None,
    adapter: LiveCanaryExchangePort | None = None,
    write: bool = True,
) -> dict[str, Any]:
    config = load_live_execution_config()
    adapter = adapter or build_live_canary_adapter()
    capabilities = adapter.capabilities()
    credential = load_live_credentials(credential_path)
    permission = validate_latest_permission_manifest()
    approval = live_canary_approval_guard()
    arm = validate_arm_token()
    stoploss = stoploss_exchange_guard(capabilities)
    kill_switch = read_live_kill_switch()
    blockers = _unique(
        live_execution_safety_blockers(config)
        + credential.get("blockers", [])
        + permission.get("blockers", [])
        + approval.reasons
        + arm.get("blockers", [])
        + stoploss.reasons
        + (["LIVE_KILL_SWITCH_ACTIVE"] if kill_switch.get("active") else [])
    )
    status = "READY_FOR_PREFLIGHT" if not blockers else "BLOCKED"
    payload = {
        "status": status,
        "generated_at": datetime.now(UTC).isoformat(),
        "mode": "fake" if getattr(adapter, "is_fake", False) else "blocked",
        "real_order_possible": False,
        "real_order_attempted": False,
        "credential_status": credential["status"],
        "permission_manifest_status": permission.get("status"),
        "approval_status": approval.details.get("status"),
        "arming_status": arm["status"],
        "adapter_available": capabilities.adapter_available,
        "stoploss_capability": capabilities.supports_stoploss_on_exchange,
        "kill_switch_status": kill_switch.get("status"),
        "allowed_symbols": config.get("allowed_symbols", []),
        "max_order_notional_usd": config.get("max_order_notional_usd", 25),
        "blockers": blockers,
        "warnings": [
            "Live canary prepare does not connect to an exchange or place orders.",
            "Credentials are masked and never written to reports.",
        ],
        "live_promotion_status": "LIVE_BLOCKED",
        "next_commands": ["make.cmd canary-live-preflight", "make.cmd canary-live-status"],
    }
    if write:
        write_live_canary_report(PREPARE_JSON, PREPARE_MD, "Live Canary Prepare", payload)
    return payload


def run_live_preflight(
    *,
    symbol: str | None = None,
    notional_usd: float | None = None,
    credential_path: str | Path | None = None,
    adapter: LiveCanaryExchangePort | None = None,
    kill_switch_path: str | Path = KILL_SWITCH_PATH,
    write: bool = True,
) -> dict[str, Any]:
    config = load_live_execution_config()
    adapter = adapter or build_live_canary_adapter()
    capabilities = adapter.capabilities()
    prepare = prepare_live_canary(credential_path=credential_path, adapter=adapter, write=True)
    live_guard = live_trading_guard()
    exchange_guard = live_exchange_guard()
    permission = validate_latest_permission_manifest()
    approval = live_canary_approval_guard()
    arm = validate_arm_token()
    final_gate = evaluate_final_gate(write=False)
    stoploss_proof = build_stoploss_proof(write=False)
    stoploss = stoploss_exchange_guard(capabilities)
    proving = evaluate_proving_readiness(write=False)
    incidents = summarize_incidents()
    kill_switch = read_live_kill_switch(kill_switch_path)
    checks: dict[str, Any] = {
        "prepare_status": prepare["status"],
        "live_trading_guard": "PASS" if live_guard.passed else "FAIL",
        "live_exchange_guard": "PASS" if exchange_guard.passed else "FAIL",
        "permission_manifest": permission.get("status"),
        "approval": "PASS" if approval.passed else "FAIL",
        "arming_token": arm["status"],
        "final_gate": final_gate.get("final_gate_status"),
        "stoploss_exchange_guard": "PASS" if stoploss.passed else "FAIL",
        "stoploss_proof": stoploss_proof.get("design_status"),
        "proving_readiness": proving.get("readiness_status"),
        "unresolved_incidents": incidents.get("unresolved_count"),
        "kill_switch": kill_switch.get("status"),
    }
    blockers = _unique(
        prepare["blockers"]
        + live_guard.reasons
        + exchange_guard.reasons
        + permission.get("blockers", [])
        + approval.reasons
        + arm.get("blockers", [])
        + final_gate.get("blockers", [])
        + stoploss.reasons
        + stoploss_proof.get("blockers", [])
        + (
            ["PROVING_STATUS_NOT_DRY_RUN_PROVEN"]
            if proving.get("readiness_status") != "DRY_RUN_PROVEN"
            else []
        )
        + (["UNRESOLVED_INCIDENTS_PRESENT"] if incidents.get("unresolved_count", 0) else [])
        + (["LIVE_KILL_SWITCH_ACTIVE"] if kill_switch.get("active") else [])
    )
    if symbol is not None:
        symbol_check = validate_symbol_allowed(symbol)
        checks["symbol_allowlist"] = symbol_check["status"]
        blockers.extend(symbol_check["blockers"])
    if notional_usd is not None:
        notional_check = validate_notional_limit(notional_usd)
        checks["notional_limit"] = notional_check["status"]
        blockers.extend(notional_check["blockers"])
    if not capabilities.adapter_available:
        blockers.append("LIVE_ADAPTER_UNAVAILABLE")
    blockers = _unique(blockers)
    preflight_status = "PREFLIGHT_PASS" if not blockers else "PREFLIGHT_FAIL"
    payload = {
        "status": "LIVE_BLOCKED" if blockers else "PREFLIGHT_PASS",
        "preflight_status": preflight_status,
        "generated_at": datetime.now(UTC).isoformat(),
        "mode": "fake" if getattr(adapter, "is_fake", False) else "blocked",
        "real_order_possible": bool(not blockers and not getattr(adapter, "is_fake", False)),
        "real_order_attempted": False,
        "checks": checks,
        "adapter_capabilities": capabilities.__dict__,
        "allowed_symbols": config.get("allowed_symbols", []),
        "max_order_notional_usd": config.get("max_order_notional_usd", 25),
        "max_open_positions": config.get("max_open_positions", 1),
        "blockers": blockers,
        "warnings": [
            "Preflight is fail-closed and does not place orders.",
            "Autonomous systems cannot call live fire.",
        ],
        "live_promotion_status": "LIVE_BLOCKED",
        "next_commands": ["make.cmd canary-live-status", "make.cmd canary-live-report"],
    }
    if write:
        write_live_canary_report(PREFLIGHT_JSON, PREFLIGHT_MD, "Live Canary Preflight", payload)
    return payload


def _unique(items: list[str]) -> list[str]:
    return sorted({str(item) for item in items if str(item)})

