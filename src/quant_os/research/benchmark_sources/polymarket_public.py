from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

PUBLIC_READ_ONLY_METHODS = (
    "get_ok",
    "get_server_time",
    "get_simplified_markets",
    "get_midpoint",
    "get_price",
    "get_spread",
    "get_prices_history",
    "get_order_book",
    "get_order_books",
)
FORBIDDEN_LIVE_METHODS = (
    "set_api_creds",
    "create_or_derive_api_creds",
    "create_order",
    "create_and_post_order",
    "create_market_order",
    "create_and_post_market_order",
    "post_order",
    "post_orders",
    "cancel",
    "cancel_order",
    "cancel_orders",
    "cancel_market_orders",
    "cancel_all",
    "get_orders",
)


def inspect_polymarket_public(
    *,
    manifest_path: str | Path | None = None,
    optional_import: str = "py_clob_client",
) -> dict[str, Any]:
    return {
        "source_id": "py_clob_client_public",
        "classification": "runtime-safe",
        "read_only": True,
        "optional_import": optional_import,
        "optional_import_available": importlib.util.find_spec(optional_import) is not None,
        "public_read_only_methods": list(PUBLIC_READ_ONLY_METHODS),
        "forbidden_live_methods": list(FORBIDDEN_LIVE_METHODS),
        "requires_wallet": False,
        "signing_required": False,
        "execution_authority_added": False,
        "network_required_for_fixture": False,
        "network_required_for_public_fetch": True,
        "manifest": summarize_polymarket_public_manifest(manifest_path),
    }


def summarize_polymarket_public_manifest(manifest_path: str | Path | None) -> dict[str, Any]:
    if manifest_path is None:
        return {"status": "NOT_PROVIDED", "markets": 0, "orderbooks": 0, "trades": 0}
    path = Path(manifest_path)
    if not path.exists():
        return {"status": "MISSING", "path": str(path), "markets": 0, "orderbooks": 0, "trades": 0}

    payload = json.loads(path.read_text(encoding="utf-8"))
    markets = payload.get("markets", [])
    orderbooks = payload.get("orderbooks", [])
    trades = payload.get("trades", [])
    token_ids = sorted(
        {
            str(token.get("token_id"))
            for market in markets
            for token in market.get("tokens", [])
            if token.get("token_id")
        }
    )
    return {
        "status": "PASS",
        "path": str(path),
        "markets": len(markets),
        "orderbooks": len(orderbooks),
        "trades": len(trades),
        "token_ids": token_ids,
    }
