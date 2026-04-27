from __future__ import annotations

from quant_os.adapters.event_store_jsonl import JsonlEventStore
from quant_os.adapters.market_data_parquet import LocalParquetMarketData
from quant_os.data.demo_data import seed_demo_data
from quant_os.research.tournament import run_tournament

if __name__ == "__main__":
    store = JsonlEventStore()
    seed_demo_data(event_store=store)
    frame = LocalParquetMarketData().load("SPY")
    print(run_tournament(frame, store))
