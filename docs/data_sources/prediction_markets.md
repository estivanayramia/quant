# Prediction Market Data Sources

This setup is read-only by design. It adds market-data inspection paths without private keys,
signing, order placement, wallet mirroring, or live trading authority.

## Official Polymarket CLOB

- Official Python clients: `py-clob-client-v2` and legacy `py-clob-client`.
- Local isolated requirements: `tools/requirements-polymarket-readonly.txt`.
- Smoke check: `scripts/data/polymarket_readonly_check.py`.
- Allowed use here: Level 0 public methods such as markets, order books, server time,
  last-trade price, and price history when the endpoint supports it.
- Intentionally excluded: private key setup, API credential derivation, order builders,
  order placement, cancellations, allowances, signing, user trades, and wallet flows.

## poly_data

Local reference clone target: `external/poly_data/` (ignored).

It is useful as an external research reference because it organizes:

- market metadata,
- raw `OrderFilled` events,
- processed trade rows.

Keep it separate from runtime code. Do not run its full update pipeline casually; its own
README notes that initial collection can take days and create large local data.

An isolated import-only environment may live at `external/poly_data/.venv/` for reference
inspection. It is ignored and must not be used by the quant runtime.

## pmxt Polymarket Archive

Archive index: `https://archive.pmxt.dev/Polymarket/v2/`.

The archive provides hourly Polymarket orderbook snapshots in Parquet. Individual files can
be hundreds of MB, so `scripts/data/pmxt_orderbook_sample.py` lists candidates by default and
only downloads when `--download` is explicitly provided. Samples belong under ignored
`data/external/pmxt_orderbooks/`.

Expand later by pinning exact hours and maximum sizes. Do not bulk mirror the archive from
this repo unless a separate storage plan exists.

## prediction-market-backtesting

Local reference clone target: `external/prediction-market-backtesting/` (ignored).

It matters as a reference because it explores prediction-market-specific replay ideas,
NautilusTrader-based architecture, and Polymarket/Kalshi adapter patterns. Treat it as
inspiration only until this repo has its own deterministic, safety-reviewed integration plan.
