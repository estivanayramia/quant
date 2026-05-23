# PMXT Read-Only Adapter Assessment

PMXT is useful for the live-market simulated profitability campaign only as a read-only data source. It should not be used for live trading, authenticated trading calls, balances, positions, order creation, order submission, order cancellation, request signing, or private key handling.

## Useful Surfaces

- `fetchOrderBook` can provide live and historical L2 prediction-market books with bid/ask levels, timestamps, and depth.
- Historical reconstructed order book ranges can improve no-lookahead replay, conservative fake fills, spread checks, and liquidity-sensitive no-fill decisions.
- Router/catalog market search can improve candidate discovery across venues such as Polymarket, Kalshi, Limitless, Smarkets, and other PMXT-supported venues.
- Execution-price helpers can inform fake fill/no-fill modeling if they can run locally or with public read-only data.

## Disallowed Surfaces

- `createOrder`
- `buildOrder`
- `submitOrder`
- `cancelOrder`
- `fetchBalance`
- `fetchPositions`
- `fetchOpenOrders`
- any venue credential configuration
- any private key, wallet key, broker key, or PMXT API key loading in the autonomous campaign
- any hosted Enterprise SQL or paid/API-key-only dependency for proof status

## Integration Requirements

An implementation must:

- default to disabled and fixture-safe;
- require an explicit `--public-network-ok` style flag for public reads;
- run without PMXT API keys, venue credentials, private keys, browser cookies, or paid APIs;
- produce a source manifest showing endpoint, venue, outcome ID, timestamp, bid/ask/depth snapshot count, and whether the data came from local PMXT or hosted PMXT;
- mark hosted/API-key-required data as advisory only, not proof-grade, unless the campaign rules are explicitly changed;
- keep `live_trading_enabled=false`, `execution_authority=NONE`, `order_transmission_enabled=false`, `authenticated_requests_enabled=false`, `request_signing_enabled=false`, `api_keys_loaded=false`, `private_keys_loaded=false`, `actual_order_count=0`, and `actual_cancel_count=0`;
- reconcile PMXT snapshots into fake intent, fake fill/no-fill, fake ledger, fake mark/outcome, fake PnL, baseline/placebo, and reconciliation reports.

## Recommended First Implementation

Add a fixture-safe adapter that reads a local PMXT-style JSON or Parquet manifest first. Then add an optional public read-only probe that can call unauthenticated local PMXT if installed. Do not use hosted PMXT or PMXT API keys in the profitability proof path.

Suggested modules:

- `src/quant_os/data_sources/pmxt_readonly.py`
- `src/quant_os/autonomy/pmxt_orderbook_observer.py`
- `src/quant_os/autonomy/pmxt_fake_fill_model.py`
- `tests/test_pmxt_readonly_adapter.py`

The adapter should be treated as a way to improve evidence quality, not as a way to bypass negative PnL or baseline/placebo failures.
