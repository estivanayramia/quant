from __future__ import annotations

from pathlib import Path

import yaml

from quant_os.data.dataset_report import build_dataset_report
from tests.test_expanded_demo_data import _small_dataset_config


def test_dataset_report_generated(local_project) -> None:
    Path("configs/datasets.yaml").write_text(
        yaml.safe_dump(_small_dataset_config()), encoding="utf-8"
    )
    report = build_dataset_report()
    assert report["manifest"]["files"]
    assert Path("reports/datasets/latest_quality.json").exists()
