"""Read-only Polymarket CLOB market-data smoke check.

Uses the official py-clob-client without keys, signing, API credentials, or
order methods. The script refuses to run if common Polymarket private-key or
API-credential environment variables are present.
"""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Iterable
from typing import Any


HOST = "https://clob.polymarket.com"
FORBIDDEN_SECRET_ENVS = (
    "POLYMARKET_PRIVATE_KEY",
    "POLYMARKET_PK",
    "PRIVATE_KEY",
    "CLOB_API_KEY",
    "CLOB_SECRET",
    "CLOB_PASS_PHRASE",
    "CLOB_PASS_PHRASE",
)


def fail_if_signing_env_present() -> None:
    present = [name for name in FORBIDDEN_SECRET_ENVS if os.environ.get(name)]
    if present:
        names = ", ".join(sorted(set(present)))
        raise SystemExit(
            f"Refusing read-only check while signing/API credential env vars are set: {names}"
        )


def first_token_ids(markets: Iterable[dict[str, Any]], limit: int) -> list[str]:
    token_ids: list[str] = []
    for market in markets:
        for token in market.get("tokens") or []:
            token_id = token.get("token_id") or token.get("tokenId") or token.get("asset_id")
            if token_id:
                token_ids.append(str(token_id))
        for key in ("token_id", "tokenId", "asset_id", "assetId"):
            if market.get(key):
                token_ids.append(str(market[key]))
        if len(token_ids) >= limit:
            break
    return token_ids[:limit]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--markets-limit", type=int, default=3)
    parser.add_argument("--token-limit", type=int, default=1)
    args = parser.parse_args()

    fail_if_signing_env_present()

    try:
        from py_clob_client_v2 import ClobClient
        from py_clob_client_v2.clob_types import PricesHistoryParams

        client = ClobClient(host=args.host, chain_id=137)
        client_name = "py-clob-client-v2"
    except ImportError:
        try:
            from py_clob_client.client import ClobClient
        except ImportError as exc:
            raise SystemExit(
                "Missing official Polymarket CLOB clients. Install the isolated tool env with: "
                "python -m venv tools/.venv-polymarket-readonly && "
                "tools\\.venv-polymarket-readonly\\Scripts\\python -m pip install -r "
                "tools\\requirements-polymarket-readonly.txt"
            ) from exc

        PricesHistoryParams = None
        client = ClobClient(args.host)
        client_name = "py-clob-client"

    ok = client.get_ok()
    server_time = client.get_server_time()

    if hasattr(client, "get_sampling_simplified_markets"):
        markets_response = client.get_sampling_simplified_markets()
    else:
        markets_response = client.get_simplified_markets()

    markets = markets_response.get("data", [])[: args.markets_limit]
    token_ids = first_token_ids(markets, args.token_limit)
    market_questions: list[str | None] = []
    for market in markets:
        question = market.get("question")
        condition_id = market.get("condition_id")
        if question is None and condition_id and hasattr(client, "get_market"):
            try:
                question = client.get_market(condition_id).get("question")
            except Exception:  # noqa: BLE001 - question enrichment is optional.
                question = None
        market_questions.append(question)

    orderbook: dict[str, Any] | None = None
    last_trade_price: Any = None
    price_history: Any = None
    for token_id in token_ids:
        try:
            book = client.get_order_book(token_id)
            bids = book.get("bids", []) if isinstance(book, dict) else getattr(book, "bids", []) or []
            asks = book.get("asks", []) if isinstance(book, dict) else getattr(book, "asks", []) or []
            orderbook = {"token_id": token_id, "bids": len(bids), "asks": len(asks)}
            break
        except Exception as exc:  # noqa: BLE001 - report client/API failures without hiding them.
            orderbook = {"token_id": token_id, "error": repr(exc)}

    if orderbook and "token_id" in orderbook:
        token_id = str(orderbook["token_id"])
        try:
            last_trade_price = client.get_last_trade_price(token_id)
        except Exception as exc:  # noqa: BLE001
            last_trade_price = {"error": repr(exc)}

        try:
            if PricesHistoryParams is None:
                raise AttributeError("legacy py-clob-client has no get_prices_history support")
            raw_history = client.get_prices_history(PricesHistoryParams(market=token_id, interval="1h"))
            history_rows = raw_history.get("history", raw_history) if isinstance(raw_history, dict) else raw_history
            price_history = {"points": len(history_rows), "sample": history_rows[:3]}
        except Exception as exc:  # noqa: BLE001
            price_history = {"error": repr(exc)}

    print(
        json.dumps(
            {
                "host": args.host,
                "client": client_name,
                "ok": ok,
                "server_time": server_time,
                "markets_returned": len(markets),
                "sample_market_questions": market_questions,
                "sample_token_ids": token_ids,
                "orderbook": orderbook,
                "last_trade_price": last_trade_price,
                "price_history": price_history,
                "signing_enabled": False,
                "orders_enabled": False,
            },
            indent=2,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
