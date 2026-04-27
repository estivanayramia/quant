from __future__ import annotations

from pathlib import Path

from quant_os.security.config_guard import config_guard


def test_config_guard_passes_safe_defaults(local_project):
    assert config_guard().passed


def test_config_guard_rejects_live_config(local_project):
    Path("configs/execution.yaml").write_text("live_trading_enabled: true\n", encoding="utf-8")
    result = config_guard()
    assert not result.passed
    assert any(reason.startswith("LIVE_FLAG_TRUE") for reason in result.reasons)
