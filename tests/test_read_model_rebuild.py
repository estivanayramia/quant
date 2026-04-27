from __future__ import annotations

import duckdb

from quant_os.core.events import EventType, make_event
from quant_os.projections.rebuild import rebuild_read_models


def test_read_models_rebuild_from_event_ledger(event_store, tmp_path):
    event_store.append(make_event(EventType.DATA_SEEDED, "demo", {"rows": 1}))
    db_path = rebuild_read_models(event_store, tmp_path / "read.duckdb")
    with duckdb.connect(str(db_path)) as con:
        count = con.execute("select count(*) from events").fetchone()[0]
    assert count == 1
