from __future__ import annotations

from pathlib import Path

import yaml

from quant_os.autonomy.supervisor import Supervisor
from quant_os.data.dataset_manifest import build_dataset_manifest
from quant_os.data.dataset_quality import run_dataset_quality
from quant_os.data.dataset_splits import build_dataset_splits
from quant_os.data.evidence_scoring import calculate_evidence_score
from quant_os.data.expanded_demo_data import seed_expanded_demo_data
from quant_os.data.leakage_checks import run_leakage_checks
from quant_os.research.leaderboard import build_strategy_leaderboard
from quant_os.research.research_evidence_report import write_research_evidence_report
from tests.test_expanded_demo_data import _small_dataset_config


def test_phase8_smoke_passes(local_project) -> None:
    Path("configs/datasets.yaml").write_text(
        yaml.safe_dump(_small_dataset_config()), encoding="utf-8"
    )
    assert seed_expanded_demo_data()["rows"] > 0
    assert build_dataset_manifest()["files"]
    assert run_dataset_quality()["status"] in {"PASS", "WARN"}
    splits = build_dataset_splits()
    assert splits["status"] == "PASS"
    assert run_leakage_checks(splits_payload=splits)["status"] in {"PASS", "WARN"}
    score = calculate_evidence_score()
    assert score["live_promotion_status"] == "LIVE_BLOCKED"
    report = write_research_evidence_report()
    assert report["live_promotion_status"] == "LIVE_BLOCKED"
    leaderboard = build_strategy_leaderboard()
    assert "evidence_penalty" in leaderboard
    state = Supervisor().run_once()
    assert (
        state.dataset_evidence_summary["dataset_evidence"]["live_promotion_status"]
        == "LIVE_BLOCKED"
    )
