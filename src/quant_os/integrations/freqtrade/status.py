from __future__ import annotations

from quant_os.integrations.freqtrade.dry_run_adapter import FreqtradeDryRunAdapter


def get_freqtrade_status() -> dict[str, object]:
    return FreqtradeDryRunAdapter().get_status()
