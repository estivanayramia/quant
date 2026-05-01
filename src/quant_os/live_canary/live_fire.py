from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quant_os.core.ids import deterministic_client_order_id
from quant_os.governance.live_attempt_registry import (
    append_live_attempt,
    create_live_attempt_record,
)
from quant_os.live_canary.adapter import build_live_canary_adapter
from quant_os.live_canary.config import load_live_execution_config
from quant_os.live_canary.exchange_port import ExchangeOrderRequest, LiveCanaryExchangePort
from quant_os.live_canary.live_kill_switch import KILL_SWITCH_PATH, read_live_kill_switch
from quant_os.live_canary.live_preflight import run_live_preflight
from quant_os.live_canary.notional_limits import validate_notional_limit
from quant_os.live_canary.reporting import LIVE_CANARY_ROOT, write_live_canary_report
from quant_os.live_canary.symbol_allowlist import validate_symbol_allowed
from quant_os.security.stoploss_exchange_guard import stoploss_exchange_guard

FIRE_JSON = LIVE_CANARY_ROOT / "latest_fire_attempt.json"
FIRE_MD = LIVE_CANARY_ROOT / "latest_fire_attempt.md"


def fire_live_canary(
    *,
    symbol: str,
    notional_usd: float,
    side: str = "buy",
    confirm_live_fire: bool = False,
    credential_path: str | Path | None = None,
    adapter: LiveCanaryExchangePort | None = None,
    allow_fake_gate_override: bool = False,
    gate_override: dict[str, Any] | None = None,
    kill_switch_path: str | Path = KILL_SWITCH_PATH,
    write: bool = True,
) -> dict[str, Any]:
    adapter = adapter or build_live_canary_adapter()
    config = load_live_execution_config()
    capabilities = adapter.capabilities()
    created_at = datetime.now(UTC)
    client_order_id = deterministic_client_order_id("tiny_live_canary", symbol, side, created_at, 1)
    blockers: list[str] = []
    if not confirm_live_fire:
        blockers.append("LIVE_FIRE_CONFIRMATION_MISSING")
    if side.lower() not in {"buy", "sell"}:
        blockers.append("LIVE_FIRE_SIDE_NOT_SUPPORTED")
    symbol_check = validate_symbol_allowed(symbol)
    notional_check = validate_notional_limit(notional_usd)
    blockers.extend(symbol_check["blockers"])
    blockers.extend(notional_check["blockers"])
    stoploss = stoploss_exchange_guard(capabilities)
    blockers.extend(stoploss.reasons)
    kill_switch = read_live_kill_switch(kill_switch_path)
    if kill_switch.get("active"):
        blockers.append("LIVE_KILL_SWITCH_ACTIVE")
    if len(adapter.get_open_positions()) >= int(config.get("max_open_positions", 1)):
        blockers.append("LIVE_MAX_OPEN_POSITION_ALREADY_REACHED")
    fake_mode = bool(getattr(adapter, "is_fake", False))
    if gate_override is not None:
        if not (allow_fake_gate_override and fake_mode):
            blockers.append("LIVE_GATE_OVERRIDE_REQUIRES_FAKE_ADAPTER")
        blockers.extend(gate_override.get("blockers", []))
    else:
        preflight = run_live_preflight(
            symbol=symbol,
            notional_usd=notional_usd,
            credential_path=credential_path,
            adapter=adapter,
            kill_switch_path=kill_switch_path,
            write=True,
        )
        blockers.extend(preflight.get("blockers", []))
    blockers = sorted(set(blockers))
    attempt = create_live_attempt_record(
        symbol=symbol,
        notional_usd=notional_usd,
        status="BLOCKED" if blockers else "ATTEMPTED",
        blockers=blockers,
        client_order_id=client_order_id,
        fake_mode=fake_mode,
    )
    append_live_attempt(attempt)
    order_result = None
    real_order_attempted = False
    if not blockers:
        request = ExchangeOrderRequest(
            symbol=symbol.upper(),
            side=side.lower(),
            notional_usd=notional_usd,
            client_order_id=client_order_id,
        )
        order_result = adapter.place_order(request)
        real_order_attempted = not fake_mode
        attempt = {
            **attempt,
            "status": order_result.status,
            "exchange_order_id": order_result.exchange_order_id,
            "filled_notional_usd": order_result.filled_notional_usd,
            "real_order_attempted": real_order_attempted,
        }
        append_live_attempt(attempt)
    status = "BLOCKED" if blockers else (order_result.status if order_result else "ATTEMPTED")
    payload = {
        "status": status,
        "generated_at": created_at.isoformat(),
        "mode": "fake" if fake_mode else "real_capable_blocked",
        "symbol": symbol.upper(),
        "side": side.lower(),
        "notional_usd": notional_usd,
        "client_order_id": client_order_id,
        "adapter_available": capabilities.adapter_available,
        "real_order_possible": bool(not blockers and not fake_mode),
        "real_order_attempted": real_order_attempted,
        "fake_mode": fake_mode,
        "order_result": order_result.__dict__ if order_result else None,
        "attempt_record": attempt,
        "allowed_symbols": config.get("allowed_symbols", []),
        "max_order_notional_usd": config.get("max_order_notional_usd", 25),
        "blockers": blockers,
        "warnings": [
            "No autonomous process may invoke this command.",
            "Default install remains blocked unless every local gate passes.",
        ],
        "live_promotion_status": "LIVE_BLOCKED",
        "next_commands": ["make.cmd canary-live-reconcile", "make.cmd canary-live-stop"],
    }
    if write:
        write_live_canary_report(FIRE_JSON, FIRE_MD, "Live Canary Fire Attempt", payload)
    return payload

