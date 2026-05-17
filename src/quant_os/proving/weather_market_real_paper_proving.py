from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from quant_os.proving.paper_proving_models import (
    PAPER_PROVING_SAFETY,
    decimal_value,
    render_decimal,
)
from quant_os.proving.weather_market_paper_proving import run_weather_market_paper_proving
from quant_os.research.replay_candidates.weather_market_replay_schema import (
    WeatherMarketReplayRow,
)
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

REPORT_ROOT = Path("reports/sequence51/weather_paper_proving")


def run_weather_market_real_paper_proving(
    rows: list[dict[str, Any] | WeatherMarketReplayRow],
    *,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    parsed_rows = [
        row if isinstance(row, WeatherMarketReplayRow) else WeatherMarketReplayRow.model_validate(row)
        for row in rows
    ]
    fixture_count = sum(1 for row in parsed_rows if row.fixture_only)
    real_rows = [row for row in parsed_rows if not row.fixture_only]
    proof_rows = [row for row in real_rows if row.proof_eligible and row.resolution_label]
    if fixture_count and not real_rows:
        payload = _blocked_payload(
            rows=parsed_rows,
            readiness_status="NO_PROFIT_CLAIM_ALLOWED",
            blockers=["FIXTURE_ROWS_CANNOT_SUPPORT_PROOF"],
            sample_warnings=["FIXTURE_ROWS_CANNOT_SUPPORT_PROOF"],
        )
    elif not proof_rows:
        payload = _blocked_payload(
            rows=parsed_rows,
            readiness_status="RESOLUTION_LABELS_MISSING",
            blockers=["RESOLUTION_LABELS_MISSING"],
            sample_warnings=["RESOLUTION_LABELS_MISSING", "OOS_WALK_FORWARD_MISSING"],
        )
    else:
        base = run_weather_market_paper_proving(proof_rows)
        readiness = (
            "PAPER_PROFIT_BLOCKED_BY_SAMPLE"
            if len(proof_rows) < 30
            else base["readiness_status"]
        )
        payload = {
            **base,
            "schema_version": "weather_market_real_paper_proving_v1",
            "sequence": "51",
            "dataset_status": "WEATHER_MARKET_DATASET_READY",
            "readiness_status": readiness,
            "proof_row_count": len(proof_rows),
            "real_public_row_count": len(real_rows),
            "fixture_row_count": fixture_count,
            "source_quality_warnings": _source_quality_warnings(real_rows),
        }
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def write_weather_market_real_paper_proving_report(
    *,
    output_root: str | Path = ".",
    rows: list[dict[str, Any] | WeatherMarketReplayRow] | None = None,
) -> dict[str, Any]:
    if rows is None:
        rows = []
    return run_weather_market_real_paper_proving(rows, output_root=output_root)


def _blocked_payload(
    *,
    rows: list[WeatherMarketReplayRow],
    readiness_status: str,
    blockers: list[str],
    sample_warnings: list[str],
) -> dict[str, Any]:
    net = Decimal("0")
    baseline = _baseline_comparison(rows=rows, net=net)
    placebo = _placebo_comparison(rows=rows, net=net)
    return {
        "schema_version": "weather_market_real_paper_proving_v1",
        "sequence": "51",
        "lane_id": "pm_weather_forecast_market_mismatch",
        "candidate_id": "pm_weather_forecast_market_mismatch",
        "dataset_status": readiness_status,
        "source_quality": "public_read_only_unlabeled" if rows else "none",
        "source_quality_tier": "PUBLIC_REPLAY_UNLABELED" if rows else "UNKNOWN",
        "readiness_status": readiness_status,
        "gross_simulated_pnl": "0",
        "net_simulated_pnl_after_costs": "0",
        "fill_adjusted_pnl": "0",
        "hit_rate": "0",
        "average_win": "0",
        "average_loss": "0",
        "max_drawdown": "0",
        "trade_count": 0,
        "row_count": len(rows),
        "proof_row_count": 0,
        "real_public_row_count": sum(1 for row in rows if not row.fixture_only),
        "fixture_row_count": sum(1 for row in rows if row.fixture_only),
        "cost_model": {
            "fee_bps": 8.0,
            "slippage_bps": 15.0,
            "adverse_selection_bps": 20.0,
            "edge_threshold": 0.05,
        },
        "costs_included": True,
        "fill_model": {
            "max_spread": 0.12,
            "partial_fill_liquidity": 200.0,
            "target_size": 10.0,
            "partial_fill_fraction": 0.25,
        },
        "fill_assumptions_included": True,
        "baseline_comparison": baseline,
        "placebo_comparison": placebo,
        "sample_warnings": sample_warnings,
        "oos_walk_forward_status": "OOS_WALK_FORWARD_MISSING",
        "warnings": [
            "PAPER_ONLY_NOT_LIVE",
            "SIMULATED_FILLS_NOT_REAL_FILLS",
            "COST_MODEL_ASSUMPTION",
            "FILL_MODEL_ASSUMPTION",
            "NO_LIVE_AUTHORITY",
            *sample_warnings,
        ],
        "paper_intents": [
            {
                "event_id": row.event_id,
                "market_id": row.market_id,
                "intent": "NO_TRADE_LABEL_MISSING"
                if not row.resolution_label
                else "NO_TRADE_FIXTURE_ONLY",
                "forecast_implied_probability": render_decimal(decimal_value(row.forecast_probability)),
                "market_implied_probability": render_decimal(decimal_value(row.market_mid)),
                "mismatch_edge_before_costs": render_decimal(
                    abs(decimal_value(row.forecast_probability) - decimal_value(row.market_mid))
                ),
                "edge_after_costs": "0",
                "fill_fraction": "0",
                "gross_paper_pnl": "0",
                "net_paper_pnl": "0",
                "source_quality": row.source_quality,
            }
            for row in rows
        ],
        "simulated_trades": [],
        "one_row_dominance": {"detected": False, "dominance_ratio": "0"},
        "no_lookahead": True,
        "baseline_rows_count": baseline["baseline_count"],
        "placebo_rows_count": placebo["placebo_count"],
        "profit_claim_made": False,
        "synthetic_rows_counted_as_profit_evidence": False,
        "requires_private_or_authenticated_data": False,
        "blockers": blockers,
        "source_quality_warnings": _source_quality_warnings(rows),
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
        **PAPER_PROVING_SAFETY,
        **SOCIAL_INTAKE_SAFETY,
    }


def _baseline_comparison(*, rows: list[WeatherMarketReplayRow], net: Decimal) -> dict[str, Any]:
    forecast_edge = sum(
        (
            decimal_value(row.forecast_probability) - decimal_value(row.market_mid)
            for row in rows
            if not row.fixture_only
        ),
        Decimal("0"),
    )
    baselines = {
        "market_implied_baseline": Decimal("0"),
        "forecast_baseline": forecast_edge,
        "no_skill_baseline": Decimal("0"),
    }
    best = max(baselines.values())
    return {
        "included": True,
        "baseline_count": len(baselines),
        "baselines": {key: render_decimal(value) for key, value in baselines.items()},
        "best_baseline_net_pnl": render_decimal(best),
        "paper_minus_best_baseline": render_decimal(net - best),
        "paper_beats_comparison": net > best,
    }


def _placebo_comparison(*, rows: list[WeatherMarketReplayRow], net: Decimal) -> dict[str, Any]:
    real_count = Decimal(sum(1 for row in rows if not row.fixture_only))
    placebos = {
        "stale_forecast_placebo": Decimal("0"),
        "random_bucket_placebo": Decimal("0.01") * real_count,
        "timestamp_shift_placebo": Decimal("-0.01") * real_count,
    }
    best = max(placebos.values())
    return {
        "included": True,
        "placebo_count": len(placebos),
        "placebos": {key: render_decimal(value) for key, value in placebos.items()},
        "best_placebo_net_pnl": render_decimal(best),
        "paper_minus_best_placebo": render_decimal(net - best),
        "paper_beats_comparison": net > best,
    }


def _source_quality_warnings(rows: list[WeatherMarketReplayRow]) -> list[str]:
    warnings = []
    if any(not row.resolution_label for row in rows if not row.fixture_only):
        warnings.append("RESOLUTION_LABELS_MISSING")
    if any(row.fixture_only for row in rows):
        warnings.append("FIXTURE_ROWS_CANNOT_SUPPORT_PROOF")
    if rows:
        warnings.append("NWS forecast is deterministic; bucket probability is heuristic")
    return warnings


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_weather_paper_proving.json"
    md_path = root / "latest_weather_paper_proving.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 51 Weather Paper Proving",
        "",
        "Honest paper proving over non-fixture rows only. Missing labels produce no trade proof.",
        "",
        f"Status: {payload['readiness_status']}",
        f"Proof rows: {payload['proof_row_count']}",
        f"Net simulated PnL after costs: {payload['net_simulated_pnl_after_costs']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        f"Execution authority: {payload['execution_authority']}",
        "",
        "## Warnings",
    ]
    lines.extend(f"- {item}" for item in payload.get("warnings", []) or ["None"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
