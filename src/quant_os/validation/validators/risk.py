from __future__ import annotations


def risk_blocked(*, kill_switch: bool = False, cap_breach: bool = False) -> bool:
    return kill_switch or cap_breach
