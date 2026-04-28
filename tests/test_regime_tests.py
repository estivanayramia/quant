from __future__ import annotations

from pathlib import Path

from quant_os.research.regime_tests import classify_regimes, run_regime_tests


def test_regime_tests_report_generated(local_project, spy_frame) -> None:
    regimes = classify_regimes(spy_frame)
    assert "regime" in regimes.columns
    payload = run_regime_tests()
    assert payload["status"] in {"PASS", "WARN"}
    assert Path("reports/strategy/regime/latest_regime_tests.json").exists()
