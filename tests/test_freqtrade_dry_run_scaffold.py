from __future__ import annotations

import json

from quant_os.integrations.freqtrade.config_writer import write_freqtrade_dry_run_config
from quant_os.integrations.freqtrade.dry_run_adapter import FreqtradeDryRunAdapter


def test_freqtrade_config_is_dry_run_only(local_project):
    path = write_freqtrade_dry_run_config()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["dry_run"] is True
    assert payload["live_trading_allowed"] is False
    assert payload["exchange"]["key"] == ""
    assert payload["exchange"]["secret"] == ""
    assert payload["telegram"]["enabled"] is False
    assert payload["api_server"]["enabled"] is False


def test_freqtrade_adapter_disabled_by_default():
    assert FreqtradeDryRunAdapter().available() is False
