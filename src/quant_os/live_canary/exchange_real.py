from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quant_os.live_canary.adapter_settings import load_real_adapter_settings
from quant_os.live_canary.config import load_live_execution_config
from quant_os.live_canary.credential_loader import load_live_credential_secrets
from quant_os.live_canary.exchange_port import (
    ExchangeCapabilities,
    ExchangeOrderRequest,
    ExchangeOrderResult,
    ExchangePosition,
)


def ccxt_dependency_status() -> dict[str, Any]:
    try:
        import ccxt  # type: ignore  # noqa: F401
    except ImportError:
        return {"installed": False, "name": "ccxt", "blockers": ["CCXT_DEPENDENCY_MISSING"]}
    return {"installed": True, "name": "ccxt", "blockers": []}


@dataclass
class KrakenSpotCanaryAdapter:
    settings_path: str | Path | None = None
    credential_path: str | Path | None = None
    is_fake: bool = False
    _settings: dict[str, Any] = field(default_factory=dict)
    _capabilities: ExchangeCapabilities | None = None

    def capabilities(self) -> ExchangeCapabilities:
        if self._capabilities is not None:
            return self._capabilities
        config = load_live_execution_config()
        settings = load_real_adapter_settings(self.settings_path)
        self._settings = settings
        dependency = ccxt_dependency_status()
        notes = []
        blockers = []
        blockers.extend(settings.get("blockers", []))
        blockers.extend(dependency["blockers"])
        adapter_config = config.get("adapter", {})
        if adapter_config.get("real_adapter_enabled") is not True:
            blockers.append("REAL_ADAPTER_NOT_ENABLED")
        if adapter_config.get("live_transport_enabled") is not True:
            blockers.append("REAL_ADAPTER_LIVE_TRANSPORT_DISABLED")
        if config.get("exchange_adapter_enabled") is not True:
            blockers.append("LIVE_EXCHANGE_ADAPTER_DISABLED")
        if blockers:
            notes.extend(sorted(set(blockers)))
        supports_stoploss = settings.get("stoploss_on_exchange_supported")
        if supports_stoploss is None:
            supports_stoploss = False
        self._capabilities = ExchangeCapabilities(
            exchange_name="kraken",
            adapter_available=not blockers,
            spot_only=settings.get("account_mode") == "spot_only",
            supports_market_orders=True,
            supports_stoploss_on_exchange=bool(supports_stoploss),
            supports_margin=False,
            supports_futures=False,
            supports_leverage=False,
            supports_shorting=False,
            notes=notes,
        )
        return self._capabilities

    def get_open_positions(self) -> list[ExchangePosition]:
        capabilities = self.capabilities()
        if not capabilities.adapter_available:
            return []
        # Spot exchanges do not expose positions the same way derivatives do.
        # A future explicit local transport can map non-zero balances here.
        return []

    def place_order(self, request: ExchangeOrderRequest) -> ExchangeOrderResult:
        capabilities = self.capabilities()
        if not capabilities.adapter_available:
            return ExchangeOrderResult(
                status="REJECTED",
                client_order_id=request.client_order_id,
                message="kraken adapter unavailable or blocked",
                raw_payload={"capability_notes": capabilities.notes},
            )
        config = load_live_execution_config()
        if config.get("execution", {}).get("live_order_enabled") is not True:
            return ExchangeOrderResult(
                status="REJECTED",
                client_order_id=request.client_order_id,
                message="live order execution disabled in config",
            )
        try:
            import ccxt  # type: ignore
        except ImportError:
            return ExchangeOrderResult(
                status="REJECTED",
                client_order_id=request.client_order_id,
                message="ccxt dependency missing",
            )
        credentials = load_live_credential_secrets(self.credential_path)
        if credentials["status"] != "PASS":
            return ExchangeOrderResult(
                status="REJECTED",
                client_order_id=request.client_order_id,
                message="live credential guard failed",
                raw_payload={"credential_blockers": credentials.get("blockers", [])},
            )
        secrets = credentials["secrets"]
        # The live transport is intentionally narrow and only reachable after
        # every outer canary gate passes. It still avoids logging credentials.
        exchange = ccxt.kraken(
            {
                "apiKey": secrets.get("api_key"),
                "secret": secrets.get("api_secret"),
                "password": secrets.get("passphrase"),
                "enableRateLimit": True,
            }
        )
        exchange.load_markets()
        ticker = exchange.fetch_ticker(request.symbol)
        last_price = float(ticker.get("last") or ticker.get("close") or 0)
        if last_price <= 0:
            return ExchangeOrderResult(
                status="REJECTED",
                client_order_id=request.client_order_id,
                message="could not determine market price for notional mapping",
            )
        amount = request.notional_usd / last_price
        amount = float(exchange.amount_to_precision(request.symbol, amount))
        order = exchange.create_order(
            request.symbol,
            request.order_type,
            request.side,
            amount,
            None,
            {"clientOrderId": request.client_order_id},
        )
        return ExchangeOrderResult(
            status="FIRED",
            client_order_id=request.client_order_id,
            exchange_order_id=str(order.get("id")) if order else None,
            filled_notional_usd=request.notional_usd,
            message="kraken market order submitted",
            raw_payload={"exchange": "kraken", "order_id_present": bool(order and order.get("id"))},
        )

    def emergency_stop(self) -> dict[str, object]:
        return {
            "status": "STOPPED",
            "exchange_name": "kraken",
            "fake": False,
            "note": "local kill switch activated; no automatic close path is run",
        }
