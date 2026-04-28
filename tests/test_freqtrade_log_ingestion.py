from __future__ import annotations

from pathlib import Path

from quant_os.integrations.freqtrade.log_ingestion import ingest_freqtrade_logs, parse_log_line


def test_logs_command_handles_empty_no_logs(local_project):
    payload = ingest_freqtrade_logs("")
    assert payload["line_count"] == 0
    assert Path("reports/freqtrade/logs/latest_logs.json").exists()


def test_log_ingestion_handles_raw_lines(local_project):
    payload = ingest_freqtrade_logs("unstructured dry-run line BTC/USDT\n")
    assert payload["line_count"] == 1
    assert payload["dry_run_indicators"] == 1
    assert payload["pairs"] == ["BTC/USDT"]


def test_log_ingestion_extracts_warnings_errors():
    warning = parse_log_line("2026-01-01 00:00:00 WARNING dry-run warning ETH/USDT")
    error = parse_log_line("2026-01-01 00:00:01 ERROR dry-run failed BTC/USDT")
    assert warning.warning is True
    assert error.error is True
