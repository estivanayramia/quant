from __future__ import annotations

from pathlib import Path

from quant_os.research.strategy_ablation import run_strategy_ablation


def test_strategy_ablation_report_is_generated(local_project) -> None:
    payload = run_strategy_ablation()
    assert payload["status"] == "PASS"
    assert Path("reports/strategy/ablation/latest_ablation.json").exists()
