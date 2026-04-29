from __future__ import annotations

import os
import time
from pathlib import Path

from quant_os.proving.blockers import collect_proving_blockers
from quant_os.proving.freshness import evaluate_freshness


def test_stale_artifacts_create_blockers(tmp_path: Path) -> None:
    artifact = tmp_path / "old.json"
    artifact.write_text("{}", encoding="utf-8")
    old = time.time() - 100 * 3600
    os.utime(artifact, (old, old))
    freshness = evaluate_freshness(
        artifacts={"old_report": str(artifact)}, warn_hours=24, fail_hours=72
    )
    assert freshness["status"] == "FAIL"
    assert freshness["failures"] == ["STALE_ARTIFACT_FAIL:old_report"]


def test_repeated_warnings_create_warn_state(local_project) -> None:
    records = [
        {"run_status": "completed", "proving_blockers": [], "warnings": ["WARN"], "top_strategy_id": "a"}
        for _ in range(3)
    ]
    summary = collect_proving_blockers(records, minimum_successful_runs=1)
    assert "REPEATED_WARNINGS" in summary["warnings"]
