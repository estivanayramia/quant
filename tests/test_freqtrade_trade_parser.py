from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from quant_os.integrations.freqtrade.trade_parser import (
    parse_json_artifact,
    parse_jsonl_artifact,
    parse_log_artifact,
    parse_sqlite_artifact,
)


def test_json_trade_parser_handles_list_format(local_project):
    path = Path("trades.json")
    path.write_text(
        json.dumps([{"pair": "BTC/USDT", "open_rate": 50000, "stake_amount": 10, "dry_run": True}])
    )
    parsed = parse_json_artifact(path)
    assert len(parsed.records) == 1


def test_json_trade_parser_handles_trades_key(local_project):
    path = Path("trades.json")
    path.write_text(json.dumps({"trades": [{"pair": "ETH/USDT", "dry_run": True}]}))
    parsed = parse_json_artifact(path)
    assert parsed.records[0]["pair"] == "ETH/USDT"


def test_jsonl_parser_handles_malformed_lines_gracefully(local_project):
    path = Path("trades.jsonl")
    path.write_text(
        '{"pair":"BTC/USDT","open_rate":50000,"dry_run":true}\nnot-json\n',
        encoding="utf-8",
    )
    parsed = parse_jsonl_artifact(path)
    assert len(parsed.records) == 1
    assert any("MALFORMED_JSONL_LINE" in warning for warning in parsed.warnings)


def test_log_parser_detects_warning_and_error(local_project):
    path = Path(__file__).parent / "fixtures/freqtrade/dryrun_log_sample.txt"
    parsed = parse_log_artifact(path)
    assert parsed.records
    assert parsed.warnings
    assert parsed.errors


def test_sqlite_parser_read_failure_does_not_crash(local_project):
    path = Path("not-a-db.sqlite")
    path.write_text("not sqlite", encoding="utf-8")
    parsed = parse_sqlite_artifact(path)
    assert parsed.warnings


def test_sqlite_parser_reads_tiny_synthetic_trades_table(local_project):
    path = Path("sample.sqlite")
    con = sqlite3.connect(path)
    try:
        con.execute(
            "create table trades (id integer, pair text, stake_amount real, dry_run boolean)"
        )
        con.execute("insert into trades values (1, 'BTC/USDT', 10.0, 1)")
        con.commit()
    finally:
        con.close()
    parsed = parse_sqlite_artifact(path)
    assert len(parsed.records) == 1
