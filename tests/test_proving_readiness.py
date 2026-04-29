from __future__ import annotations

from pathlib import Path

import yaml

from quant_os.proving.incident_log import append_incidents, create_incident
from quant_os.proving.readiness import evaluate_proving_readiness


def _safe_records(count: int) -> list[dict[str, object]]:
    return [
        {
            "run_id": f"run_{index}",
            "timestamp": f"2024-01-{index + 1:02d}T00:00:00+00:00",
            "run_status": "completed",
            "proving_blockers": [],
            "warnings": [],
            "top_strategy_id": "baseline",
            "leaderboard_hash": "same",
        }
        for index in range(count)
    ]


def test_critical_incidents_block_readiness(local_project) -> None:
    append_incidents(
        [
            create_incident(
                severity="CRITICAL",
                source="test",
                category="LIVE_DANGER_EVIDENCE",
                summary="live danger",
            )
        ]
    )
    readiness = evaluate_proving_readiness(_safe_records(14))
    assert readiness["readiness_status"] == "PROVING_UNSTABLE"
    assert readiness["live_promotion_status"] == "LIVE_BLOCKED"


def test_dry_run_proven_can_be_reached_for_synthetic_safe_history(local_project) -> None:
    Path("configs/proving_mode.yaml").write_text(
        yaml.safe_dump({"readiness": {"minimum_successful_runs_future": 3}}),
        encoding="utf-8",
    )
    readiness = evaluate_proving_readiness(_safe_records(3))
    assert readiness["readiness_status"] == "DRY_RUN_PROVEN"
    assert readiness["live_ready"] is False
