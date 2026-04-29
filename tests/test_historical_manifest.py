from __future__ import annotations

from pathlib import Path

from quant_os.data.historical_import import import_historical_csv
from quant_os.data.historical_manifest import build_historical_manifest

FIXTURES = Path(__file__).parent / "fixtures" / "historical"


def test_historical_manifest_includes_raw_and_normalized_hashes(local_project) -> None:
    import_historical_csv(FIXTURES / "sample_ohlcv_standard.csv")
    manifest = build_historical_manifest()
    assert manifest["raw_sha256"]
    assert manifest["normalized_sha256"]
    assert manifest["license_note"]
    assert Path("reports/historical/manifests/latest_manifest.json").exists()
