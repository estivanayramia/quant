from __future__ import annotations

from pathlib import Path


def health_check() -> dict[str, bool]:
    return {
        "configs_present": Path("configs/risk_limits.yaml").exists(),
        "live_default_false": "allow_live_trading: false"
        in Path("configs/risk_limits.yaml").read_text(encoding="utf-8"),
        "event_dir_present": Path("data/events").exists(),
    }
