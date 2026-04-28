from __future__ import annotations

from pathlib import Path

import yaml

from quant_os.data.dataset_manifest import build_dataset_manifest
from tests.test_expanded_demo_data import _small_dataset_config


def test_dataset_manifest_includes_hashes(local_project) -> None:
    Path("configs/datasets.yaml").write_text(
        yaml.safe_dump(_small_dataset_config()), encoding="utf-8"
    )
    manifest = build_dataset_manifest()
    assert manifest["files"]
    assert all(item["sha256"] for item in manifest["files"])
    assert Path("reports/datasets/latest_manifest.json").exists()
