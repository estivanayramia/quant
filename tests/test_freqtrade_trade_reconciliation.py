from __future__ import annotations

import json

from quant_os.integrations.freqtrade.config_writer import write_freqtrade_dry_run_config
from quant_os.integrations.freqtrade.trade_artifacts import DryRunTradeRecord
from quant_os.integrations.freqtrade.trade_reconciliation import reconcile_freqtrade_trades


def _record() -> DryRunTradeRecord:
    return DryRunTradeRecord(
        record_id="r1",
        source="json",
        source_file="fixture.json",
        pair="BTC/USDT",
        symbol="BTC-USDT",
        side="long",
        stake_amount=10,
        dry_run=True,
    )


def test_trade_reconciliation_unavailable_when_no_artifacts_exist(local_project):
    payload = reconcile_freqtrade_trades(records=[], expected_records=[])
    assert payload["status"] == "UNAVAILABLE"


def test_trade_reconciliation_warns_for_unmatched_safe_records(local_project):
    payload = reconcile_freqtrade_trades(records=[_record()], expected_records=[])
    assert payload["status"] == "WARN"
    assert payload["unmatched_freqtrade_records"]


def test_trade_reconciliation_fails_on_live_mode_evidence(local_project):
    path = write_freqtrade_dry_run_config()
    config = json.loads(path.read_text(encoding="utf-8"))
    config["dry_run"] = False
    path.write_text(json.dumps(config), encoding="utf-8")
    payload = reconcile_freqtrade_trades(records=[_record()], expected_records=[])
    assert payload["status"] == "FAIL"


def test_trade_reconciliation_fails_on_credentials_detected(local_project):
    path = write_freqtrade_dry_run_config()
    config = json.loads(path.read_text(encoding="utf-8"))
    config["exchange"]["secret"] = "present"
    path.write_text(json.dumps(config), encoding="utf-8")
    payload = reconcile_freqtrade_trades(records=[_record()], expected_records=[])
    assert payload["status"] == "FAIL"
