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
    Path("configs/risk_limits.yaml").write_text(
        yaml.safe_dump(RiskLimits().model_dump()), encoding="utf-8"
    )
    return tmp_path
