from __future__ import annotations

import json
from pathlib import Path

import pytest

from quant_os.integrations.freqtrade.config_writer import write_freqtrade_dry_run_config
from quant_os.integrations.freqtrade.safety import FreqtradeSafetyError, validate_freqtrade_config


def _config(local_project) -> tuple[Path, dict]:
    path = write_freqtrade_dry_run_config()
    payload = json.loads(path.read_text(encoding="utf-8"))
    return path, payload


def _mutate(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def test_freqtrade_safety_accepts_safe_config(local_project):
    path, _ = _config(local_project)
    assert validate_freqtrade_config(path).passed


@pytest.mark.parametrize(
    ("path_parts", "value", "reason"),
    [
        (["dry_run"], False, "DRY_RUN_NOT_TRUE"),
        (["live_trading_allowed"], True, "LIVE_TRADING_ALLOWED"),
        (["exchange", "key"], "abc", "EXCHANGE_SECRET_PRESENT"),
        (["exchange", "secret"], "abc", "EXCHANGE_SECRET_PRESENT"),
        (["futures"], True, "FUTURES_ENABLED"),
        (["margin_mode"], "isolated", "MARGIN_MODE_ENABLED"),
        (["leverage"], 2, "LEVERAGE_ABOVE_ONE"),
        (["shorting"], True, "SHORTING_ENABLED"),
        (["telegram", "enabled"], True, "TELEGRAM_ENABLED"),
        (["api_server", "enabled"], True, "API_SERVER_ENABLED"),
        (["force_entry_enable"], True, "FORCE_ENTRY_ENABLED"),
    ],
)
def test_freqtrade_safety_rejects_critical_unsafe_values(
    local_project,
    path_parts,
    value,
    reason,
):
    path, payload = _config(local_project)
    target = payload
    for part in path_parts[:-1]:
        target = target[part]
    target[path_parts[-1]] = value
    _mutate(path, payload)
    with pytest.raises(FreqtradeSafetyError, match=reason):
        validate_freqtrade_config(path)


def test_freqtrade_safety_rejects_dry_run_wallet(local_project):
    path, payload = _config(local_project)
    payload["dry_run_wallet"] = 1000
    _mutate(path, payload)
    with pytest.raises(FreqtradeSafetyError, match="DRY_RUN_WALLET_PRESENT"):
        validate_freqtrade_config(path)


def test_freqtrade_safety_rejects_config_outside_repo_config_dir(local_project):
    outside = Path("unsafe.json")
    outside.write_text("{}", encoding="utf-8")
    with pytest.raises(FreqtradeSafetyError, match="CONFIG_PATH_OUTSIDE"):
        validate_freqtrade_config(outside)
