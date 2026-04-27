from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from quant_os.adapters.event_store_jsonl import JsonlEventStore
from quant_os.autonomy.policies import AutonomousPolicy
from quant_os.autonomy.state import (
    AutonomousRunState,
    RunStatus,
    TaskResult,
    TaskStatus,
    new_run_state,
)
from quant_os.autonomy.tasks import task_callable
from quant_os.core.events import EventType, make_event
from quant_os.watchdog.heartbeat import Heartbeat
from quant_os.watchdog.process_lock import ProcessLock

RUNBOOKS: dict[str, list[str]] = {
    "daily_research_cycle": [
        "config_guard",
        "secrets_guard",
        "live_trading_guard",
        "seed_or_load_demo_data",
        "validate_data",
        "build_features",
        "run_baseline_backtest",
        "run_placebo_backtest",
        "run_tournament",
        "rebuild_read_models",
        "run_drift_checks",
        "generate_report",
    ],
    "shadow_cycle": [
        "config_guard",
        "secrets_guard",
        "live_trading_guard",
        "seed_or_load_demo_data",
        "validate_data",
        "run_shadow_mode",
        "rebuild_read_models",
    ],
    "health_check_cycle": [
        "config_guard",
        "secrets_guard",
        "live_trading_guard",
        "run_watchdog_health_checks",
    ],
    "report_cycle": [
        "config_guard",
        "secrets_guard",
        "live_trading_guard",
        "rebuild_read_models",
        "generate_report",
        "send_mock_alert",
    ],
    "full_safe_autonomous_cycle": [
        "config_guard",
        "secrets_guard",
        "live_trading_guard",
        "seed_or_load_demo_data",
        "validate_data",
        "build_features",
        "run_baseline_backtest",
        "run_placebo_backtest",
        "run_tournament",
        "run_slippage_fee_stress",
        "run_shadow_mode",
        "rebuild_read_models",
        "run_drift_checks",
        "run_watchdog_health_checks",
        "generate_report",
        "send_mock_alert",
    ],
}


class RunbookEngine:
    def __init__(
        self,
        event_store: JsonlEventStore | None = None,
        policy: AutonomousPolicy | None = None,
    ) -> None:
        self.event_store = event_store or JsonlEventStore()
        self.policy = policy or AutonomousPolicy()
        self.heartbeat = Heartbeat()

    def run(self, runbook: str = "full_safe_autonomous_cycle") -> AutonomousRunState:
        if runbook not in RUNBOOKS:
            msg = f"unknown runbook {runbook}"
            raise ValueError(msg)
        self.policy.assert_safe()
        state = new_run_state(runbook)
        self.event_store.append(
            make_event(
                EventType.AUTONOMOUS_RUN_STARTED, state.run_id, state.model_dump(mode="json")
            )
        )
        try:
            with ProcessLock("reports/autonomy/run.lock"):
                self.event_store.append(
                    make_event(
                        EventType.HEARTBEAT_STARTED,
                        state.run_id,
                        self.heartbeat.start(state.run_id),
                    )
                )
                self._run_tasks(state, RUNBOOKS[runbook])
                state.status = (
                    RunStatus.COMPLETED if not state.failure_reasons else RunStatus.FAILED
                )
                state.completed_at = _now()
                self.event_store.append(
                    make_event(
                        EventType.HEARTBEAT_COMPLETED,
                        state.run_id,
                        self.heartbeat.complete(state.status.value),
                    )
                )
        except Exception as exc:
            state.status = RunStatus.FAILED
            state.completed_at = _now()
            state.failure_reasons.append(str(exc))
            self.heartbeat.complete("failed")
        self._write_outputs(state)
        self.event_store.append(
            make_event(
                EventType.AUTONOMOUS_RUN_COMPLETED
                if state.status == RunStatus.COMPLETED
                else EventType.AUTONOMOUS_RUN_FAILED,
                state.run_id,
                state.model_dump(mode="json"),
            )
        )
        return state

    def _run_tasks(self, state: AutonomousRunState, tasks: Iterable[str]) -> None:
        for name in tasks:
            result = self._run_task(name)
            state.task_statuses.append(result)
            self._merge_task_details(state, name, result)
            if result.status == TaskStatus.FAILED and result.critical:
                state.failure_reasons.append(f"{name}:{result.error}")
                break

    def _run_task(self, name: str) -> TaskResult:
        started = _now()
        try:
            details = task_callable(name, self.event_store)()
            return TaskResult(
                name=name,
                status=TaskStatus.PASSED,
                started_at=started,
                completed_at=_now(),
                details=details,
            )
        except Exception as exc:
            return TaskResult(
                name=name,
                status=TaskStatus.FAILED,
                started_at=started,
                completed_at=_now(),
                error=str(exc),
            )

    def _merge_task_details(self, state: AutonomousRunState, name: str, result: TaskResult) -> None:
        if name.endswith("guard"):
            state.safety_checks[name] = result.details
        elif name == "run_baseline_backtest":
            state.backtest_summary["baseline"] = result.details
        elif name == "run_placebo_backtest":
            state.backtest_summary["placebo"] = result.details
        elif name == "run_tournament":
            state.tournament_summary = result.details
        elif name == "run_shadow_mode":
            state.shadow_summary = result.details
        elif name == "run_drift_checks":
            state.drift_summary = result.details
        elif name == "generate_report":
            state.report_paths["daily_report"] = "reports/daily_report.md"
            state.report_paths["daily_report_json"] = "reports/daily_report.json"
        state.kill_switch_state = {"active": False}
        state.risk_state = {"live_trading_enabled": False}

    def _write_outputs(self, state: AutonomousRunState) -> None:
        root = Path("reports/autonomy")
        history = root / "history"
        history.mkdir(parents=True, exist_ok=True)
        payload = state.model_dump(mode="json")
        stamp = state.started_at.replace(":", "-").replace("+00:00", "Z")
        latest_json = root / "latest_run.json"
        latest_md = root / "latest_run.md"
        history_json = history / f"{stamp}.json"
        history_md = history / f"{stamp}.md"
        state.report_paths.update(
            {
                "autonomy_latest_json": str(latest_json),
                "autonomy_latest_md": str(latest_md),
                "autonomy_history_json": str(history_json),
                "autonomy_history_md": str(history_md),
            }
        )
        payload = state.model_dump(mode="json")
        latest_json.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        history_json.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        markdown = self._markdown(state)
        latest_md.write_text(markdown, encoding="utf-8")
        history_md.write_text(markdown, encoding="utf-8")

    def _markdown(self, state: AutonomousRunState) -> str:
        lines = [
            "# Autonomous QuantOps Run",
            "",
            f"Run ID: {state.run_id}",
            f"Runbook: {state.runbook}",
            f"Status: {state.status.value}",
            f"Started: {state.started_at}",
            f"Completed: {state.completed_at}",
            "",
            "This is simulation/shadow/paper/dry-run-ready automation only. No live trading.",
            "",
            "## Tasks",
        ]
        for task in state.task_statuses:
            lines.append(f"- {task.status.value}: {task.name} {task.error or ''}".rstrip())
        if state.failure_reasons:
            lines.extend(["", "## Failures"])
            lines.extend(f"- {reason}" for reason in state.failure_reasons)
        return "\n".join(lines) + "\n"


def _now() -> str:
    return datetime.now(UTC).isoformat()
