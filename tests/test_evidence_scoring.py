from __future__ import annotations

from pathlib import Path

import yaml

from quant_os.data.evidence_scoring import calculate_evidence_score
from tests.test_expanded_demo_data import _small_dataset_config


def test_evidence_score_penalizes_weak_data_and_blocks_live(local_project) -> None:
    Path("configs/datasets.yaml").write_text(
        yaml.safe_dump(_small_dataset_config()), encoding="utf-8"
    )
    score = calculate_evidence_score()
    assert score["live_promotion_status"] == "LIVE_BLOCKED"
    assert score["live_ready"] is False
    assert score["final_evidence_status"] in {
        "INSUFFICIENT",
        "RESEARCH_WEAK",
        "RESEARCH_ACCEPTABLE",
        "SHADOW_CANDIDATE",
        "DRY_RUN_CANDIDATE",
    }
    assert Path("reports/evidence/latest_evidence_score.json").exists()
