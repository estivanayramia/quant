from __future__ import annotations

import json
from pathlib import Path

from quant_os.integrations.freqtrade.config_writer import write_freqtrade_dry_run_config
from quant_os.integrations.freqtrade.runner import FreqtradeRunner


def _mutate(payload_updates: dict) -> None:
    path = write_freqtrade_dry_run_config()
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.update(payload_updates)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def test_start_command_refuses_unsafe_existing_config(local_project, monkeypatch):
    _mutate({"dry_run": False})

    def unsafe_prepare(self):
        from quant_os.integrations.freqtrade.safety import validate_freqtrade_config

        validate_freqtrade_config(Path("freqtrade/user_data/config/config.dry-run.generated.json"))

    monkeypatch.setattr(FreqtradeRunner, "prepare", unsafe_prepare)
    result = FreqtradeRunner().start()
    assert result.status == "FAIL"
    assert "DRY_RUN_NOT_TRUE" in result.message


def test_start_command_validates_dry_run_true_without_docker(local_project, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _name: None)
    result = FreqtradeRunner().start()
    assert result.status == "UNAVAILABLE"
    assert Path("reports/freqtrade/manifests/latest_operation_manifest.json").exists()


def test_start_command_rejects_keys_and_live_flag(local_project, monkeypatch):
    _mutate({"live_trading_allowed": True, "exchange": {"key": "abc", "secret": ""}})

    def unsafe_prepare(self):
        from quant_os.integrations.freqtrade.safety import validate_freqtrade_config

        validate_freqtrade_config(Path("freqtrade/user_data/config/config.dry-run.generated.json"))

    monkeypatch.setattr(FreqtradeRunner, "prepare", unsafe_prepare)
    result = FreqtradeRunner().start()
    assert result.status == "FAIL"
    assert "LIVE_TRADING_ALLOWED" in result.message or "EXCHANGE_SECRET_PRESENT" in result.message
