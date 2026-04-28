from __future__ import annotations

from pathlib import Path

from quant_os.features.feature_report import write_feature_report
from quant_os.features.feature_store_local import build_feature_frame, write_feature_store


def test_feature_store_builds_local_feature_frame(spy_frame) -> None:
    features = build_feature_frame(spy_frame)
    assert "smc_score" in features.columns
    assert "volume_zscore" in features.columns
    assert len(features) == len(spy_frame)


def test_feature_report_generated(local_project, spy_frame) -> None:
    summary = write_feature_store(spy_frame)
    report = write_feature_report()
    assert Path(summary["features_path"]).exists()
    assert Path(report["report_path"]).exists()
