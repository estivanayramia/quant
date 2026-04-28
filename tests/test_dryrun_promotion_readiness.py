from __future__ import annotations

from quant_os.integrations.freqtrade.dry_run_adapter import FreqtradeDryRunAdapter
from quant_os.integrations.freqtrade.log_ingestion import ingest_freqtrade_logs
from quant_os.monitoring.promotion_readiness import check_promotion_readiness


def _prepare() -> None:
    adapter = FreqtradeDryRunAdapter()
    adapter.generate_config()
    adapter.export_strategy()
    adapter.write_run_manifest()
    ingest_freqtrade_logs("")


def test_promotion_readiness_blocks_live(local_project):
    _prepare()
    payload = check_promotion_readiness()
    assert payload["live_promotion_status"] == "TINY_LIVE_BLOCKED"
    assert payload["live_eligible"] is False


def test_promotion_readiness_allows_dry_run_ready_if_safe(local_project):
    _prepare()
    payload = check_promotion_readiness()
    assert payload["status"] == "DRY_RUN_READY"
    assert payload["dry_run_ready"] is True
