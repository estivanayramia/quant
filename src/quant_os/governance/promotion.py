from __future__ import annotations


def research_to_shadow_allowed(
    *,
    backtest_completed: bool,
    placebo_completed: bool,
    slippage_stress_completed: bool,
    risk_firewall_compatible: bool,
    data_quality_ok: bool,
    kill_switch_active: bool,
    quarantined: bool,
) -> bool:
    return all(
        [
            backtest_completed,
            placebo_completed,
            slippage_stress_completed,
            risk_firewall_compatible,
            data_quality_ok,
            not kill_switch_active,
            not quarantined,
        ]
    )


def paper_or_live_promotion_allowed() -> bool:
    return False
