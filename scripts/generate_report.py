from __future__ import annotations

from quant_os.adapters.event_store_jsonl import JsonlEventStore
from quant_os.ops.reporting import generate_daily_report

if __name__ == "__main__":
    print(generate_daily_report(JsonlEventStore()))
