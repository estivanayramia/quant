from __future__ import annotations

import json
from pathlib import Path

from quant_os.integrations.freqtrade.config_writer import write_freqtrade_dry_run_config
from quant_os.integrations.freqtrade.dry_run_adapter import FreqtradeDryRunAdapter
from quant_os.integrations.freqtrade.reconciliation import reconcile_freqtrade


def _ready() -> None:
    adapter = FreqtradeDryRunAdapter()
    adapter.generate_config()
    strategy = adapter.export_strategy()
    manifest = adapter.write_run_manifest()
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    import hashlib

    payload["strategy_sha256"] = hashlib.sha256(strategy.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def test_reconciliation_passes_or_warns_safe_generated_config(local_project):
    _ready()
    payload = reconcile_freqtrade()
    assert payload["status"] in {"PASS", "WARN"}


def test_reconciliation_fails_unsafe_config(local_project):
    _ready()
    path = write_freqtrade_dry_run_config()
    config = json.loads(path.read_text(encoding="utf-8"))
    config["dry_run"] = False
    path.write_text(json.dumps(config), encoding="utf-8")
    payload = reconcile_freqtrade()
    assert payload["status"] == "FAIL"


def test_reconciliation_warns_when_docker_unavailable(local_project, monkeypatch):
    _ready()
    monkeypatch.setattr("shutil.which", lambda _name: None)
    payload = reconcile_freqtrade()
    assert any(
        check["name"] == "docker_available" and check["status"] == "WARN"
        for check in payload["checks"]
    )


def test_reconciliation_detects_missing_strategy(local_project):
    _ready()
    Path("freqtrade/user_data/strategies/QuantOSDryRunStrategy.py").unlink()
    payload = reconcile_freqtrade()
    assert payload["status"] == "FAIL"
