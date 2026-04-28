from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from quant_os.core.ids import deterministic_id


class TaskStatus(StrEnum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class RunStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskResult(BaseModel):
    name: str
    status: TaskStatus
    started_at: str
    completed_at: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    critical: bool = True
    error: str | None = None


class AutonomousRunState(BaseModel):
    run_id: str
    runbook: str
    started_at: str
    completed_at: str | None = None
    status: RunStatus = RunStatus.RUNNING
    task_statuses: list[TaskResult] = Field(default_factory=list)
    failure_reasons: list[str] = Field(default_factory=list)
    safety_checks: dict[str, Any] = Field(default_factory=dict)
    risk_state: dict[str, Any] = Field(default_factory=dict)
    kill_switch_state: dict[str, Any] = Field(default_factory=dict)
    quarantined_strategies: list[str] = Field(default_factory=list)
    backtest_summary: dict[str, Any] = Field(default_factory=dict)
    tournament_summary: dict[str, Any] = Field(default_factory=dict)
    shadow_summary: dict[str, Any] = Field(default_factory=dict)
    drift_summary: dict[str, Any] = Field(default_factory=dict)
    freqtrade_summary: dict[str, Any] = Field(default_factory=dict)
    dryrun_monitoring_summary: dict[str, Any] = Field(default_factory=dict)
    freqtrade_trade_artifacts_summary: dict[str, Any] = Field(default_factory=dict)
    strategy_research_summary: dict[str, Any] = Field(default_factory=dict)
    dataset_evidence_summary: dict[str, Any] = Field(default_factory=dict)
    report_paths: dict[str, str] = Field(default_factory=dict)


def new_run_state(runbook: str) -> AutonomousRunState:
    started = datetime.now(UTC).isoformat()
    run_id = deterministic_id("run", runbook, started, length=20)
    return AutonomousRunState(run_id=run_id, runbook=runbook, started_at=started)
