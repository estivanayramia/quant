from __future__ import annotations

from pathlib import Path

from quant_os.adapters.read_model_duckdb import DuckDBReadModelStore
from quant_os.ports.event_store import EventStorePort


def rebuild_read_models(
    event_store: EventStorePort,
    output_path: str | Path = "data/read_models/quant_os.duckdb",
) -> Path:
    return DuckDBReadModelStore(output_path).rebuild(event_store.read_all())
