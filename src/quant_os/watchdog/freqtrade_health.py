from __future__ import annotations

from quant_os.integrations.freqtrade.operational_status import build_operational_status


def freqtrade_health_check() -> dict[str, object]:
    status = build_operational_status()
    return {
        "passed": bool(status["config_valid"]),
        "status": status,
        "critical": False,
    }
