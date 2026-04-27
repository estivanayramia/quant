from __future__ import annotations

from quant_os.adapters.event_store_jsonl import JsonlEventStore
from quant_os.projections.rebuild import rebuild_read_models

if __name__ == "__main__":
    print(rebuild_read_models(JsonlEventStore()))
