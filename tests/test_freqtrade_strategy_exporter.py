from __future__ import annotations

from quant_os.integrations.freqtrade.strategy_exporter import export_quant_os_strategy


def test_freqtrade_strategy_scaffold_generated(local_project):
    path = export_quant_os_strategy()
    content = path.read_text(encoding="utf-8")
    assert path.name == "QuantOSDryRunStrategy.py"
    assert "Dry-run research only" in content
    assert "can_short = False" in content
    assert "return 1.0" in content
    assert "does not call AI" in content
