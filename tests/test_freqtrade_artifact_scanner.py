from __future__ import annotations

import shutil
from pathlib import Path

from quant_os.integrations.freqtrade.artifact_scanner import scan_freqtrade_artifacts


def test_scanner_finds_safe_json_fixture(local_project):
    root = Path("freqtrade/user_data")
    root.mkdir(parents=True)
    shutil.copyfile(
        Path(__file__).parent / "fixtures/freqtrade/dryrun_trades_sample.json",
        root / "dryrun_trades_sample.json",
    )
    payload = scan_freqtrade_artifacts()
    assert payload["artifacts_found"] == 1
    assert payload["artifacts"][0]["artifact_type"] == "json"


def test_scanner_excludes_suspicious_secret_like_files(local_project):
    root = Path("freqtrade/user_data")
    root.mkdir(parents=True)
    (root / "exchange_secret.json").write_text("{}", encoding="utf-8")
    payload = scan_freqtrade_artifacts()
    assert payload["artifacts_found"] == 0
    assert payload["skipped"][0]["reason"] == "EXCLUDED_SUSPICIOUS_NAME"
