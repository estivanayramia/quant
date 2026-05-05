from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from quant_os.replay.venue_calibration import run_venue_calibration
from quant_os.research.crypto.candidate_strategies import (
    generate_crypto_candidate_signals,
)
from quant_os.research.crypto.features import build_crypto_features
from quant_os.research.crypto.ingest import build_crypto_research_dataset
from quant_os.research.validation.robustness import regime_summary
from quant_os.research.validation.splits import rolling_walk_forward_splits

REPORT_ROOT = Path("reports/sequence18/calibrated_edge")


def write_calibrated_edge_report(
    frame: pd.DataFrame | None = None,
    *,
    calibration_summary: dict[str, Any] | None = None,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    calibration = calibration_summary or run_venue_calibration(output_root=output_root)
    raw_frame = frame.copy() if frame is not None else build_crypto_research_dataset().frame
    features = build_crypto_features(raw_frame)
    params = calibration.get("suggested_replay_parameters") or {}
    cost_bps = float(params.get("fee_bps", 5.0)) + float(params.get("slippage_bps", 3.0))
    split_results = [
        _evaluate_split(split, cost_bps)
        for split in rolling_walk_forward_splits(
            features,
            train_bars=60,
            validation_bars=30,
            test_bars=30,
            step_bars=30,
        )
    ]
    aggregate = _aggregate(split_results)
    baselines = _baselines(features, cost_bps)
    blockers = _blockers(
        calibration=calibration,
        aggregate=aggregate,
        baselines=baselines,
        split_results=split_results,
    )
    warnings = sorted(set(str(item) for item in calibration.get("warnings", [])))
    status = "BLOCKED" if blockers else "WARN" if warnings else "PASS"
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "sequence": "18",
        "status": status,
        "credibility_status": "CREDIBLE_AFTER_CALIBRATION"
        if not blockers
        else "NOT_CREDIBLE_AFTER_CALIBRATION",
        "calibration_status": calibration.get("status"),
        "calibrated_cost_bps": cost_bps,
        "split_count": len(split_results),
        "splits": split_results,
        "aggregate": aggregate,
        "baselines": baselines,
        "regime_summary": regime_summary(split_results),
        "blockers": blockers,
        "warnings": warnings,
        "live_trading_enabled": False,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _evaluate_split(split: Any, cost_bps: float) -> dict[str, Any]:
    selected = 4.0
    return {
        "split_id": split.split_id,
        "selected_min_edge_bps": selected,
        "train_metrics": _evaluate_window(split.train, selected, cost_bps),
        "validation_metrics": _evaluate_window(split.validation, selected, cost_bps),
        "test_metrics": _evaluate_window(split.test, selected, cost_bps),
        "dominant_test_regime": _dominant_regime(split.test),
    }


def _evaluate_window(
    frame: pd.DataFrame,
    min_edge_bps: float,
    cost_bps: float,
    *,
    horizon_bars: int = 5,
) -> dict[str, Any]:
    signals = [
        signal
        for signal in generate_crypto_candidate_signals(frame, min_edge_bps=min_edge_bps)
        if signal.strategy_id != "random_placebo"
    ]
    realized = [
        _realized_signal_return_bps(frame, signal, horizon_bars=horizon_bars)
        for signal in signals
    ]
    realized = [item for item in realized if item is not None]
    gross = float(pd.Series(realized).mean()) if realized else 0.0
    return {
        "signal_count": len(signals),
        "gross_expectancy_bps": gross,
        "expectancy_after_costs_bps": float(gross - cost_bps) if realized else 0.0,
        "calibrated_cost_bps": float(cost_bps),
    }


def _realized_signal_return_bps(
    frame: pd.DataFrame,
    signal: Any,
    *,
    horizon_bars: int,
) -> float | None:
    symbol_frame = frame[frame["symbol"] == signal.symbol].sort_values("timestamp").reset_index(drop=True)
    matches = symbol_frame.index[symbol_frame["timestamp"] == pd.Timestamp(signal.timestamp)]
    if len(matches) == 0:
        return None
    index = int(matches[0])
    exit_index = min(len(symbol_frame) - 1, index + horizon_bars)
    if exit_index == index:
        return None
    entry = float(symbol_frame.loc[index, "close"])
    exit_price = float(symbol_frame.loc[exit_index, "close"])
    direction = 1.0 if signal.side.upper() == "BUY" else -1.0
    return direction * ((exit_price - entry) / entry) * 10_000.0


def _aggregate(split_results: list[dict[str, Any]]) -> dict[str, float]:
    if not split_results:
        return {
            "mean_train_expectancy_after_costs_bps": 0.0,
            "mean_validation_expectancy_after_costs_bps": 0.0,
            "mean_test_expectancy_after_costs_bps": 0.0,
        }
    return {
        "mean_train_expectancy_after_costs_bps": _mean(split_results, "train_metrics"),
        "mean_validation_expectancy_after_costs_bps": _mean(split_results, "validation_metrics"),
        "mean_test_expectancy_after_costs_bps": _mean(split_results, "test_metrics"),
    }


def _mean(split_results: list[dict[str, Any]], key: str) -> float:
    return float(
        pd.Series(
            [float(item[key]["expectancy_after_costs_bps"]) for item in split_results],
            dtype="float64",
        ).mean()
    )


def _baselines(features: pd.DataFrame, cost_bps: float) -> dict[str, dict[str, float]]:
    placebo = [
        _realized_signal_return_bps(features, signal, horizon_bars=5)
        for signal in generate_crypto_candidate_signals(features, min_edge_bps=999.0)
        if signal.strategy_id == "random_placebo"
    ]
    placebo = [item for item in placebo if item is not None]
    placebo_expectancy = float(pd.Series(placebo).mean() - cost_bps) if placebo else 0.0
    return {
        "no_trade": {"expectancy_after_costs_bps": 0.0, "signal_count": 0.0},
        "random_placebo": {
            "expectancy_after_costs_bps": placebo_expectancy,
            "signal_count": float(len(placebo)),
        },
    }


def _blockers(
    *,
    calibration: dict[str, Any],
    aggregate: dict[str, float],
    baselines: dict[str, dict[str, float]],
    split_results: list[dict[str, Any]],
) -> list[str]:
    blockers: list[str] = []
    if calibration.get("status") == "BLOCKED":
        blockers.append("VENUE_CALIBRATION_BLOCKED")
    blockers.extend(str(item) for item in calibration.get("blockers", []))
    if not split_results:
        blockers.append("NO_CALIBRATED_WALK_FORWARD_EVIDENCE")
    oos = float(aggregate["mean_test_expectancy_after_costs_bps"])
    if oos < 0.0:
        blockers.append("CALIBRATED_OOS_EXPECTANCY_BELOW_THRESHOLD")
    best_baseline = max(float(item["expectancy_after_costs_bps"]) for item in baselines.values())
    if oos <= best_baseline:
        blockers.append("PLACEBO_NOT_BEATEN_AFTER_CALIBRATION")
    return sorted(set(blockers))


def _dominant_regime(frame: pd.DataFrame) -> str:
    if "volatility_regime" not in frame or frame.empty:
        return "unknown"
    return str(frame["volatility_regime"].mode().iloc[0])


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_calibrated_edge.json"
    md_path = root / "latest_calibrated_edge.md"
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    lines = [
        "# Sequence 18 Calibrated Edge Evidence",
        "",
        "Research evidence only. No live trading.",
        "",
        f"Status: {payload['status']}",
        f"Credibility: {payload['credibility_status']}",
        f"Calibrated cost bps: {payload['calibrated_cost_bps']:.4f}",
        f"Live promotion: {payload['live_promotion_status']}",
        "",
        "## Aggregate",
    ]
    for key, value in payload["aggregate"].items():
        lines.append(f"- {key}: {value:.4f}")
    lines.extend(["", "## Blockers"])
    lines.extend(f"- {item}" for item in (payload["blockers"] or ["None"]))
    lines.extend(["", "## Warnings"])
    lines.extend(f"- {item}" for item in (payload["warnings"] or ["None"]))
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
