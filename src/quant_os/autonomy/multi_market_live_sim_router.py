from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.autonomy.live_market_sim_common import load_json
from quant_os.autonomy.multi_market_live_sim_common import (
    ROOT,
    safe_report_payload,
    write_multi_market_state,
)
from quant_os.readiness.canary_readiness_common import write_json_markdown_report

REPORT_DIR = ROOT / "router"


def build_multi_market_live_sim_router(
    *,
    output_root: str | Path = ".",
    weather_profitability: dict[str, Any] | None = None,
    crypto_profitability: dict[str, Any] | None = None,
    pm_structural_profitability: dict[str, Any] | None = None,
    etf_profitability: dict[str, Any] | None = None,
) -> dict[str, Any]:
    weather_profitability = weather_profitability or load_json(
        "reports/live_market_sim_profitability/final/latest_live_market_sim_profitability.json",
        output_root=output_root,
    ) or {}
    crypto_profitability = crypto_profitability or load_json(
        "reports/multi_market_live_sim/crypto_spot/latest_crypto_profitability.json",
        output_root=output_root,
    ) or {}
    pm_structural_profitability = pm_structural_profitability or load_json(
        "reports/multi_market_live_sim/prediction_market_structural/latest_pm_structural_profitability.json",
        output_root=output_root,
    ) or {}
    etf_profitability = etf_profitability or load_json(
        "reports/multi_market_live_sim/etf_equity/latest_etf_profitability.json",
        output_root=output_root,
    ) or {}
    market_family_statuses = {
        "weather_prediction_markets": weather_profitability.get("status", "NOT_RUN"),
        "crypto_spot": crypto_profitability.get("status", "NOT_RUN"),
        "prediction_market_structural": pm_structural_profitability.get("status", "NOT_RUN"),
        "etf_equity": etf_profitability.get("status", "NOT_RUN"),
    }
    blockers: list[str] = []
    selected = None
    if crypto_profitability.get("status") != "CRYPTO_LIVE_SIM_PROFITABILITY_PROVEN":
        selected = "crypto_spot"
    elif weather_profitability.get("status") in {
        "LIVE_MARKET_SIMULATED_PROFITABILITY_PENDING_OUTCOMES",
        "WEATHER_LIVE_SIM_PENDING_OUTCOMES",
    } or not pm_structural_profitability:
        selected = "prediction_market_structural"
    elif not etf_profitability:
        selected = "etf_equity"
    if selected:
        status = "MARKET_FAMILY_SELECTED"
    else:
        status = "HUMAN_DATA_OR_CREDENTIAL_BOUNDARY_REACHED"
        blockers.append("NO_SAFE_DATA_ONLY_MARKET_FAMILY_AVAILABLE")
    return safe_report_payload(
        schema_version="multi_market_live_sim_router_v1",
        status=status,
        allowed_statuses=[
            "MULTI_MARKET_ROUTER_READY",
            "MARKET_FAMILY_SELECTED",
            "MARKET_FAMILY_BLOCKED",
            "HUMAN_DATA_OR_CREDENTIAL_BOUNDARY_REACHED",
        ],
        selected_market_family=selected,
        market_family_order=[
            "crypto_spot",
            "weather_prediction_markets",
            "prediction_market_structural",
            "etf_equity",
        ],
        market_family_statuses=market_family_statuses,
        skipped_reasons={
            "weather_prediction_markets": "pending outcomes do not block crypto routing"
            if weather_profitability.get("pending_outcome_count", 0)
            else "",
            "etf_equity": "requires approved public source policy before use",
        },
        blockers=blockers,
        next_action=f"Run {selected} data-only live simulation lane." if selected else "Stop at human data boundary.",
    )


def write_multi_market_live_sim_router_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_multi_market_live_sim_router(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_router.json",
        md_name="latest_router.md",
        title="Multi-Market Live Sim Router",
        summary="Routes among safe public-data fake-money market families without waiting on weather outcomes.",
    )
    write_multi_market_state(output_root=output_root, router=payload)
    return payload
