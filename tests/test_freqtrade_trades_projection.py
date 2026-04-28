from __future__ import annotations

from pathlib import Path

import duckdb

from quant_os.integrations.freqtrade.trade_artifacts import DryRunTradeRecord
from quant_os.projections.freqtrade_trades_projection import rebuild_freqtrade_trades_projection


def test_duckdb_projection_can_store_normalized_records(local_project):
    record = DryRunTradeRecord(
        record_id="r1",
        source="json",
        source_file="fixture.json",
        pair="BTC/USDT",
        symbol="BTC-USDT",
        side="long",
        dry_run=True,
    )
    path = rebuild_freqtrade_trades_projection([record], Path("data/read_models/test.duckdb"))
    con = duckdb.connect(str(path))
    try:
        count = con.execute("select count(*) from freqtrade_dryrun_trades").fetchone()[0]
    finally:
        con.close()
    assert count == 1
