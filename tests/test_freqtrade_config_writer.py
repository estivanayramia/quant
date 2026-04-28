from __future__ import annotations

import json
from pathlib import Path

import pytest

from quant_os.integrations.freqtrade.config_writer import write_freqtrade_dry_run_config


def test_freqtrade_config_generated(local_project):
    path = write_freqtrade_dry_run_config()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert path == Path("freqtrade/user_data/config/config.dry-run.generated.json")
    assert payload["dry_run"] is True
    assert payload["trading_mode"] == "spot"
    assert payload["live_trading_allowed"] is False


def test_freqtrade_config_generation_rejects_exchange_key_env(local_project, monkeypatch):
    monkeypatch.setenv("EXCHANGE_API_KEY", "not-a-real-key-but-present")
    with pytest.raises(RuntimeError, match="Refusing to generate"):
        write_freqtrade_dry_run_config()
