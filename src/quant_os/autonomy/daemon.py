from __future__ import annotations

import json
from pathlib import Path

from quant_os.adapters.event_store_jsonl import JsonlEventStore
from quant_os.autonomy.scheduler import LocalScheduler, SchedulerResult
from quant_os.core.events import EventType, make_event
from quant_os.watchdog.process_lock import ProcessLock, lock_exists

STOP_FILE = Path("reports/autonomy/daemon.stop")
LOCK_FILE = Path("reports/autonomy/daemon.lock")


def run_daemon(interval_minutes: int = 60, max_cycles: int | None = None) -> SchedulerResult:
    event_store = JsonlEventStore()
    STOP_FILE.parent.mkdir(parents=True, exist_ok=True)
    if STOP_FILE.exists():
        STOP_FILE.unlink()
    with ProcessLock(LOCK_FILE):
        event_store.append(
            make_event(
                EventType.DAEMON_STARTED,
                "autonomous-daemon",
                {"interval_minutes": interval_minutes, "max_cycles": max_cycles},
            )
        )
        scheduler = LocalScheduler()
        if max_cycles is not None:
            result = scheduler.run(interval_minutes=interval_minutes, max_cycles=max_cycles)
        else:
            result = _run_until_stop(scheduler, interval_minutes)
        event_store.append(
            make_event(EventType.DAEMON_STOPPED, "autonomous-daemon", result.__dict__)
        )
        return result


def _run_until_stop(scheduler: LocalScheduler, interval_minutes: int) -> SchedulerResult:
    cycles = 0
    failures = 0
    while not STOP_FILE.exists():
        result = scheduler.run(interval_minutes=interval_minutes, max_cycles=1)
        cycles += result.cycles
        failures = result.consecutive_failures
    return SchedulerResult(cycles=cycles, consecutive_failures=failures, stopped=True)


def daemon_status() -> dict[str, object]:
    return {
        "running": lock_exists(LOCK_FILE),
        "stop_requested": STOP_FILE.exists(),
        "heartbeat_exists": Path("reports/heartbeat.json").exists(),
    }


def stop_daemon() -> dict[str, object]:
    STOP_FILE.parent.mkdir(parents=True, exist_ok=True)
    STOP_FILE.write_text(json.dumps({"stop_requested": True}), encoding="utf-8")
    return daemon_status()
