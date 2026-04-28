from __future__ import annotations

import ast
from pathlib import Path

import yaml

from quant_os.cli import smoke
from quant_os.risk.limits import RiskLimits


def test_smoke_workflow_completes(local_project):
    smoke()
    assert Path("reports/daily_report.md").exists()
    assert Path("reports/daily_report.json").exists()
    assert Path("data/read_models/quant_os.duckdb").exists()


def test_no_real_api_keys_or_live_default(local_project):
    limits = yaml.safe_load(Path("configs/risk_limits.yaml").read_text(encoding="utf-8"))
    assert limits["allow_live_trading"] is False
    assert RiskLimits.from_yaml().allow_live_trading is False


def test_no_real_broker_sdks_imported():
    blocked = ["alpaca", "freqtrade", "nautilus_trader", "quantconnect", "ccxt"]
    source_files = list(Path("src").rglob("*.py"))
    for path in source_files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in blocked
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in blocked
