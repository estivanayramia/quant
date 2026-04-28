from __future__ import annotations

from pathlib import Path

from quant_os.integrations.freqtrade.trade_reporting import write_freqtrade_trade_report


def test_trade_reports_are_generated(local_project):
    payload = write_freqtrade_trade_report()
    assert payload["live_trading_enabled"] is False
    assert Path("reports/freqtrade/trades/latest_trade_report.md").exists()
    assert Path("reports/freqtrade/trades/latest_trade_report.json").exists()
