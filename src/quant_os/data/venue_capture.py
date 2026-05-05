from __future__ import annotations

import importlib
import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quant_os.data.warehouse import ensure_local_dirs


def capture_public_venue_snapshot(
    exchange_id: str = "binance",
    symbols: list[str] | None = None,
    timeframe: str = "1m",
    limit: int = 5,
    output_dir: str | Path = "data/venue_capture",
) -> dict[str, Any]:
    ensure_local_dirs()
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if symbols is None:
        symbols = ["BTC/USDT", "ETH/USDT"]

    installed = importlib.util.find_spec("ccxt") is not None
    if not installed:
        raise RuntimeError("ccxt optional dependency is not installed. Run: pip install ccxt")

    ccxt_module = importlib.import_module("ccxt")
    exchange_cls: Any = getattr(ccxt_module, exchange_id)
    exchange = exchange_cls({"enableRateLimit": True})

    captured_at = datetime.now(UTC).isoformat()
    snapshot: dict[str, Any] = {
        "source": f"{exchange_id}_public_capture",
        "venue": exchange_id,
        "timeframe": timeframe,
        "captured_at": captured_at,
        "symbols": {},
    }

    for symbol in symbols:
        safe_sym = symbol.replace("/", "")
        ticker = exchange.fetch_ticker(symbol)
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

        snapshot["symbols"][safe_sym] = {
            "book_ticker": {
                "symbol": safe_sym,
                "bidPrice": str(ticker.get("bid", 0.0)),
                "bidQty": str(ticker.get("bidVolume", 0.0)),
                "askPrice": str(ticker.get("ask", 0.0)),
                "askQty": str(ticker.get("askVolume", 0.0)),
                "received_at": ticker.get("datetime") or captured_at,
            },
            "klines": ohlcv,
        }

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    filename = f"{exchange_id}_public_snapshot_{timestamp}.json"
    filepath = out_dir / filename

    with filepath.open("w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)

    return {
        "status": "PASS",
        "venue": exchange_id,
        "captured_at": captured_at,
        "file_path": str(filepath),
        "symbols": symbols,
    }
