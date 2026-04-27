from __future__ import annotations

from pathlib import Path

from quant_os.adapters.event_store_jsonl import JsonlEventStore
from quant_os.integrations.freqtrade.safety import validate_freqtrade_config


def freqtrade_guard(
    config_path: str | Path = "freqtrade/user_data/config/config.dry-run.generated.json",
    event_store: JsonlEventStore | None = None,
):
    return validate_freqtrade_config(config_path, event_store=event_store)
