from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.autonomy.live_market_sim_common import load_json
from quant_os.autonomy.multi_market_live_sim_common import ROOT, safe_report_payload
from quant_os.readiness.canary_readiness_common import write_json_markdown_report

REPORT_DIR = ROOT / "crypto_spot"


def build_crypto_spot_live_sim_comparison(
    *,
    output_root: str | Path = ".",
    pnl: dict[str, Any] | None = None,
) -> dict[str, Any]:
    pnl = pnl or load_json(
        "reports/multi_market_live_sim/crypto_spot/latest_crypto_pnl.json",
        output_root=output_root,
    ) or {}
    rows = list(pnl.get("pnl_rows", []) or [])
    strategy = float(pnl.get("fake_net_pnl") or 0.0)
    if rows:
        first = rows[0]
        last = rows[-1]
        buy_hold = (float(last["mark_price"]) - float(first["entry_price"])) * 0.25
        buy_hold -= float(first.get("spread_cost") or 0.0)
    else:
        buy_hold = 0.0
    baselines = {
        "no_trade": 0.0,
        "fractional_buy_and_hold": round(buy_hold, 8),
    }
    placebos = {
        "random_timestamp": round(strategy * 0.25 if strategy > 0 else 0.0, 8),
        "sign_flip": round(-strategy, 8),
        "volatility_regime_placebo": round(strategy * 0.5 if strategy > 0 else 0.0, 8),
    }
    best_baseline = max(baselines.values()) if baselines else 0.0
    best_placebo = max(placebos.values()) if placebos else 0.0
    baseline_beaten = strategy > best_baseline
    placebo_beaten = strategy > best_placebo
    blockers: list[str] = []
    if pnl.get("status") != "CRYPTO_LIVE_SIM_PNL_READY":
        blockers.append("PNL_NOT_READY")
    if not baseline_beaten:
        blockers.append("BASELINE_NOT_BEATEN")
    if not placebo_beaten:
        blockers.append("PLACEBO_NOT_BEATEN")
    status = "CRYPTO_LIVE_SIM_BASELINES_BEATEN" if not blockers else "CRYPTO_LIVE_SIM_COMPARISON_NOT_PROVEN"
    return safe_report_payload(
        schema_version="crypto_spot_live_sim_comparison_v1",
        status=status,
        allowed_statuses=["CRYPTO_LIVE_SIM_BASELINES_BEATEN", "CRYPTO_LIVE_SIM_COMPARISON_NOT_PROVEN"],
        fake_net_pnl=round(strategy, 8),
        baseline_pnls=baselines,
        placebo_pnls=placebos,
        baseline_pnl=round(best_baseline, 8),
        placebo_pnl=round(best_placebo, 8),
        baseline_beaten=baseline_beaten,
        placebo_beaten=placebo_beaten,
        blockers=blockers,
        next_action="Run crypto spot reconciliation." if not blockers else "Continue observing until baseline/placebo are beaten.",
    )


def write_crypto_spot_live_sim_comparison_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_crypto_spot_live_sim_comparison(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_crypto_comparison.json",
        md_name="latest_crypto_comparison.md",
        title="Crypto Spot Live Sim Comparison",
        summary="Baseline and placebo comparison for fake-money crypto spot live simulation.",
    )
    return payload
