from __future__ import annotations

from quant_os.adapters.event_store_jsonl import JsonlEventStore
from quant_os.adapters.market_data_parquet import LocalParquetMarketData
from quant_os.data.demo_data import seed_demo_data
from quant_os.research.backtest import run_backtest

if __name__ == "__main__":
    seed_demo_data(event_store=JsonlEventStore())
    frame = LocalParquetMarketData().load("SPY")
    print(run_backtest(frame, event_store=JsonlEventStore()).metrics)
