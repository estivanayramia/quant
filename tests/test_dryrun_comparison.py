from __future__ import annotations

import json
from pathlib import Path

from quant_os.integrations.freqtrade.dry_run_adapter import FreqtradeDryRunAdapter
from quant_os.integrations.freqtrade.log_ingestion import ingest_freqtrade_logs
from quant_os.integrations.freqtrade.operational_status import write_operational_status_report
from quant_os.integrations.freqtrade.reconciliation import reconcile_freqtrade
from quant_os.monitoring.dryrun_comparison import build_dryrun_comparison


def _prepare() -> Path:
    adapter = FreqtradeDryRunAdapter()
    config = adapter.generate_config()
    adapter.export_strategy()
    adapter.write_run_manifest()
    ingest_freqtrade_logs("")
    write_operational_status_report()
    reconcile_freqtrade()
    return config


def test_comparison_passes_or_warns_safe_generated_config(local_project, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _name: None)
    _prepare()
    payload = build_dryrun_comparison()
    assert payload["status"] in {"PASS", "WARN"}
    assert not payload["unsafe_failures"]


def test_comparison_warns_when_logs_unavailable(local_project):
    adapter = FreqtradeDryRunAdapter()
    adapter.generate_config()
    adapter.export_strategy()
    adapter.write_run_manifest()
    payload = build_dryrun_comparison()
    assert any(check["name"] == "logs_available" for check in payload["warnings"])


def test_comparison_fails_dry_run_false(local_project):
    path = _prepare()
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["dry_run"] = False
    path.write_text(json.dumps(payload), encoding="utf-8")
    comparison = build_dryrun_comparison()
    assert comparison["status"] == "FAIL"


def test_comparison_fails_live_flag(local_project):
    path = _prepare()
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["live_trading_allowed"] = True
    path.write_text(json.dumps(payload), encoding="utf-8")
    comparison = build_dryrun_comparison()
    assert comparison["status"] == "FAIL"


def test_comparison_fails_keys(local_project):
    path = _prepare()
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["exchange"]["key"] = "not-a-real-key-but-present"
    path.write_text(json.dumps(payload), encoding="utf-8")
    comparison = build_dryrun_comparison()
    assert comparison["status"] == "FAIL"
