from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb

from quant_os.integrations.freqtrade.trade_artifacts import DryRunTradeRecord


def rebuild_freqtrade_trades_projection(
    records: list[DryRunTradeRecord | dict[str, Any]],
    db_path: str | Path = "data/read_models/quant_os.duckdb",
) -> Path:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path))
    try:
        con.execute("drop table if exists freqtrade_dryrun_trades")
        con.execute(
            """
            create table freqtrade_dryrun_trades (
                record_id varchar,
                source varchar,
                source_file varchar,
                strategy_name varchar,
                pair varchar,
                symbol varchar,
                side varchar,
                status varchar,
                open_date varchar,
                close_date varchar,
                open_rate double,
                close_rate double,
                amount double,
                stake_amount double,
                profit_abs double,
                profit_ratio double,
                exit_reason varchar,
                dry_run boolean,
                parsed_at varchar,
                raw_payload_json varchar
            )
            """
        )
        rows = []
        for item in records:
            record = (
                item
                if isinstance(item, DryRunTradeRecord)
                else DryRunTradeRecord.model_validate(item)
            )
            rows.append(
                (
                    record.record_id,
                    record.source,
                    record.source_file,
                    record.strategy_name,
                    record.pair,
                    record.symbol,
                    record.side,
                    record.status,
                    record.open_date,
                    record.close_date,
                    record.open_rate,
                    record.close_rate,
                    record.amount,
                    record.stake_amount,
                    record.profit_abs,
                    record.profit_ratio,
                    record.exit_reason,
                    record.dry_run,
                    record.parsed_at,
                    json.dumps(record.raw_payload, sort_keys=True, default=str),
                )
            )
        if rows:
            con.executemany(
                "insert into freqtrade_dryrun_trades values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                rows,
            )
    finally:
        con.close()
    return path
