from __future__ import annotations

from typing import Any

from quant_os.data.weather.weather_market_capture_plan import build_weather_market_capture_plan


def build_weather_market_manual_capture_instructions() -> dict[str, Any]:
    plan = build_weather_market_capture_plan()
    return {
        "schema_version": "weather_market_manual_capture_instructions_v1",
        "sequence": "50",
        "status": plan["status"],
        "capture_root": plan["capture_root"],
        "operator_instructions": plan["operator_instructions"],
        "exact_next_commands": plan["exact_next_commands"],
        "execution_authority": "NONE",
        "live_trading_enabled": False,
    }

