from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from quant_os.adapters.event_store_jsonl import JsonlEventStore
from quant_os.data.demo_data import generate_demo_ohlcv
from quant_os.risk.limits import RiskLimits


@pytest.fixture()
def event_store(tmp_path: Path) -> JsonlEventStore:
    return JsonlEventStore(tmp_path / "events.jsonl")


@pytest.fixture()
def spy_frame():
    return generate_demo_ohlcv(["SPY"], periods=120, seed=123)


@pytest.fixture()
def local_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    Path("configs").mkdir()
    Path("data").mkdir()
    Path("reports").mkdir()
    Path("pyproject.toml").write_text("[project]\nname='test'\n", encoding="utf-8")
    Path("configs/risk_limits.yaml").write_text(
        yaml.safe_dump(RiskLimits().model_dump()), encoding="utf-8"
    )
    Path("configs/autonomy.yaml").write_text(
        yaml.safe_dump(
            {
                "autonomy_enabled": True,
                "live_trading_enabled": False,
                "paper_trading_enabled": False,
                "dry_run_enabled": False,
                "external_alerts_enabled": False,
                "real_ai_providers_enabled": False,
            }
        ),
        encoding="utf-8",
    )
    Path("configs/execution.yaml").write_text(
        yaml.safe_dump({"live_trading_enabled": False, "mode": "simulated"}),
        encoding="utf-8",
    )
    Path("configs/integrations.yaml").write_text(
        yaml.safe_dump(
            {
                "integrations": {
                    "freqtrade": {"enabled": False, "live_trading_allowed": False},
                    "alpaca": {"enabled": False, "live_trading_allowed": False},
                    "ai": {"provider": "mock", "allow_real_provider_calls": False},
                }
            }
        ),
        encoding="utf-8",
    )
    Path("configs/watchdog.yaml").write_text(
        yaml.safe_dump({"watchdog": {"require_live_trading_disabled": True}}),
        encoding="utf-8",
    )
    Path("configs/strategies.yaml").write_text(
        yaml.safe_dump(
            {
                "strategies": {
                    "baseline_ma": {"enabled": True, "quarantined": False},
                    "placebo_random": {"enabled": True, "quarantined": False},
                }
            }
        ),
        encoding="utf-8",
    )
    return tmp_path
