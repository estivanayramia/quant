from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

KILL_SWITCH_PATH = Path("reports/live_canary/live_kill_switch.json")


def read_live_kill_switch(path: str | Path = KILL_SWITCH_PATH) -> dict[str, Any]:
    switch_path = Path(path)
    if not switch_path.exists():
        return {
            "status": "INACTIVE",
            "active": False,
            "reason": None,
            "live_fire_blocked": False,
        }
    try:
        payload = json.loads(switch_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "status": "ACTIVE",
            "active": True,
            "reason": "LIVE_KILL_SWITCH_UNREADABLE",
            "live_fire_blocked": True,
        }
    return payload


def activate_live_kill_switch(
    reason: str = "manual emergency stop",
    *,
    path: str | Path = KILL_SWITCH_PATH,
) -> dict[str, Any]:
    payload = {
        "status": "ACTIVE",
        "active": True,
        "activated_at": datetime.now(UTC).isoformat(),
        "reason": reason,
        "live_fire_blocked": True,
        "live_promotion_status": "LIVE_BLOCKED",
    }
    switch_path = Path(path)
    switch_path.parent.mkdir(parents=True, exist_ok=True)
    switch_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload
