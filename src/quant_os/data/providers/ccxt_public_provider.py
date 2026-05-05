from __future__ import annotations

import importlib
import importlib.util
from typing import Any

import pandas as pd

from quant_os.data.normalization import normalize_dataset_frame
from quant_os.data.providers.base import ProviderAvailability
from quant_os.data.schemas import DatasetKind


class CcxtPublicProvider:
    name = "CCXT_PUBLIC"

    def __init__(self, enabled: bool = False, exchange: str = "binance") -> None:
        self.enabled = enabled
        self.exchange = exchange

    def availability(self) -> ProviderAvailability:
        installed = importlib.util.find_spec("ccxt") is not None
        return ProviderAvailability(
            name=self.name,
            enabled=self.enabled,
            available=bool(self.enabled and installed),
            requires_network=True,
            requires_keys=False,
            reason="available for public market data"
            if self.enabled and installed
            else "ccxt optional public-data dependency is disabled or not installed; no network in CI",
        )

    def fetch_ohlcv(
        self,
        symbol: str,
        *,
        timeframe: str = "1m",
        limit: int = 500,
    ) -> pd.DataFrame:
        availability = self.availability()
        if not availability.available:
            msg = availability.reason
            raise RuntimeError(msg)
        ccxt_module = importlib.import_module("ccxt")
        exchange_cls: Any = getattr(ccxt_module, self.exchange)
        exchange = exchange_cls({"enableRateLimit": True})
        rows = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        frame = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], unit="ms", utc=True)
        frame["symbol"] = symbol
        frame["venue"] = self.exchange
        frame["timeframe"] = timeframe
        frame["source"] = "ccxt_public"
        return normalize_dataset_frame(frame, DatasetKind.CANDLE)
