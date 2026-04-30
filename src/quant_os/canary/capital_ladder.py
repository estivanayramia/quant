from __future__ import annotations

from typing import Any

from quant_os.canary.policy import CANARY_ROOT, load_canary_config, write_canary_report

CAPITAL_JSON = CANARY_ROOT / "latest_capital_ladder.json"
CAPITAL_MD = CANARY_ROOT / "latest_capital_ladder.md"


def build_capital_ladder(write: bool = True) -> dict[str, Any]:
    config = load_canary_config()
    ladder = config.get("capital_ladder", {})
    payload = {
        "status": "PLANNING_ONLY",
        "current_stage": "stage_0",
        "current_stage_label": ladder.get("stage_0", {}).get("label", "planning_only"),
        "stages": ladder,
        "automatic_progression_enabled": False,
        "live_trading_enabled": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "next_commands": ["make.cmd canary-preflight", "make.cmd canary-readiness"],
    }
    if write:
        write_canary_report(CAPITAL_JSON, CAPITAL_MD, "Canary Capital Ladder", payload)
    return payload
