from __future__ import annotations

import json
from typing import Any

from quant_os.data.historical_cache import REPORT_ROOT, load_historical_config, now_utc


def check_historical_providers(write: bool = True) -> dict[str, Any]:
    config = load_historical_config()
    provider_config = config.get("providers", {})
    providers = {
        "LOCAL_FILE": {
            "enabled": bool(provider_config.get("local_file", {}).get("enabled", True)),
            "available": True,
            "requires_network": False,
            "requires_keys": False,
            "status": "available",
        },
        "CCXT_PUBLIC": _disabled_or_unavailable(provider_config.get("ccxt_public", {})),
        "YFINANCE_PUBLIC": _disabled_or_unavailable(provider_config.get("yfinance_public", {})),
    }
    payload = {
        "generated_at": now_utc(),
        "status": "PASS",
        "allow_network_fetch": bool(config.get("allow_network_fetch", False)),
        "internet_required": bool(config.get("internet_required", False)),
        "paid_data_required": bool(config.get("paid_data_required", False)),
        "providers": providers,
        "live_trading_enabled": False,
        "warnings": [
            name for name, info in providers.items() if info["status"] in {"disabled", "unavailable"}
        ],
    }
    if write:
        _write_provider_check(payload)
    return payload


def _disabled_or_unavailable(raw: dict[str, Any]) -> dict[str, Any]:
    enabled = bool(raw.get("enabled", False))
    return {
        "enabled": enabled,
        "available": False if enabled else None,
        "requires_network": bool(raw.get("requires_network", True)),
        "requires_keys": bool(raw.get("requires_keys", False)),
        "status": "unavailable" if enabled else "disabled",
    }


def _write_provider_check(payload: dict[str, Any]) -> None:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    (REPORT_ROOT / "latest_provider_check.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8"
    )
    lines = [
        "# Historical Provider Check",
        "",
        "Provider availability only. Network fetch is disabled by default.",
        "",
        f"Status: {payload['status']}",
        f"Network fetch allowed: {payload['allow_network_fetch']}",
        "",
        "## Providers",
    ]
    for name, info in payload["providers"].items():
        lines.append(f"- {name}: {info['status']}")
    (REPORT_ROOT / "latest_provider_check.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
