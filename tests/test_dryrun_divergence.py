from __future__ import annotations

import json
from pathlib import Path

from quant_os.integrations.freqtrade.dry_run_adapter import FreqtradeDryRunAdapter
from quant_os.monitoring.divergence import check_dryrun_divergence


def _prepare() -> FreqtradeDryRunAdapter:
    adapter = FreqtradeDryRunAdapter()
    adapter.generate_config()
    adapter.export_strategy()
    adapter.write_run_manifest()
    return adapter


def test_divergence_detects_strategy_hash_mismatch(local_project):
    _prepare()
    manifest_path = Path("reports/freqtrade/latest_manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["strategy_sha256"] = "bad-hash"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    payload = check_dryrun_divergence()
    assert payload["status"] == "FAIL"


def test_divergence_detects_missing_config(local_project):
    _prepare()
    Path("freqtrade/user_data/config/config.dry-run.generated.json").unlink()
    payload = check_dryrun_divergence()
    assert payload["status"] == "FAIL"


def test_divergence_detects_missing_strategy(local_project):
    _prepare()
    Path("freqtrade/user_data/strategies/QuantOSDryRunStrategy.py").unlink()
    payload = check_dryrun_divergence()
    assert payload["status"] == "FAIL"
