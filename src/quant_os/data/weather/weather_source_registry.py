from __future__ import annotations

from typing import Any

from quant_os.data.weather.weather_source_policy import build_weather_source_policy


def build_weather_source_registry() -> dict[str, Any]:
    policy = build_weather_source_policy()
    return {
        "schema_version": "weather_source_registry_v1",
        "sequence": "50",
        "registry_status": "WEATHER_SOURCE_POLICY_REGISTRY_READY",
        "source_count": len(policy["sources"]),
        "sources": policy["sources"],
        "public_read_only_only": policy["public_read_only_only"],
        "execution_authority": "NONE",
        "live_trading_enabled": False,
    }

