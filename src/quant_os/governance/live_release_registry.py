from __future__ import annotations

from typing import Any


def live_release_registry_status() -> dict[str, Any]:
    return {
        "status": "LIVE_BLOCKED",
        "release_records_count": 0,
        "live_release_enabled": False,
        "reason": "Phase 12 has rehearsal scaffolding only and no live release path.",
    }
