from __future__ import annotations

from quant_os.adapters.event_store_jsonl import JsonlEventStore
from quant_os.data.demo_data import seed_demo_data

if __name__ == "__main__":
    print(seed_demo_data(event_store=JsonlEventStore()))
