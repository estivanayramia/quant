from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AutonomousPolicy:
    allow_live_trading: bool = False
    allow_real_broker_calls: bool = False
    allow_real_ai_calls: bool = False
    allow_external_alerts: bool = False
    stop_on_safety_failure: bool = True

    def assert_safe(self) -> None:
        if self.allow_live_trading or self.allow_real_broker_calls:
            msg = "Autonomous policy forbids live trading and real broker calls."
            raise RuntimeError(msg)
