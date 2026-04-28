from __future__ import annotations

from pathlib import Path

import yaml

from quant_os.research.research_evidence_report import write_research_evidence_report
from tests.test_expanded_demo_data import _small_dataset_config


def test_research_evidence_report_generated(local_project) -> None:
    Path("configs/datasets.yaml").write_text(
        yaml.safe_dump(_small_dataset_config()), encoding="utf-8"
    )
    report = write_research_evidence_report()
    assert report["live_promotion_status"] == "LIVE_BLOCKED"
    assert Path("reports/evidence/latest_research_evidence_report.md").exists()
