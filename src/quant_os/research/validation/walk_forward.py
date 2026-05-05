from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from quant_os.research.crypto.candidate_strategies import generate_crypto_candidate_signals
from quant_os.research.crypto.features import build_crypto_features
from quant_os.research.crypto.ingest import build_crypto_research_dataset
from quant_os.research.validation.oos_reports import write_walk_forward_report
from quant_os.research.validation.robustness import (
    edge_degradation_warnings,
    parameter_stability_warnings,
    regime_summary,
)
from quant_os.research.validation.splits import rolling_walk_forward_splits


@dataclass(frozen=True)
class WalkForwardConfig:
    train_bars: int = 96
    validation_bars: int = 48
    test_bars: int = 48
    step_bars: int = 48
    candidate_min_edges_bps: tuple[float, ...] = (3.0, 5.0, 8.0)
    cost_bps: float = 8.0
    horizon_bars: int = 5


def run_crypto_walk_forward(
    frame: pd.DataFrame | None = None,
    *,
    train_bars: int = 96,
    validation_bars: int = 48,
    test_bars: int = 48,
    step_bars: int = 48,
    output_root: str | Path = ".",
    config: WalkForwardConfig | None = None,
) -> dict[str, Any]:
    cfg = config or WalkForwardConfig(
        train_bars=train_bars,
        validation_bars=validation_bars,
        test_bars=test_bars,
        step_bars=step_bars,
    )
    raw_frame = frame.copy() if frame is not None else build_crypto_research_dataset().frame
    features = build_crypto_features(raw_frame)
    split_results = []
    for split in rolling_walk_forward_splits(
        features,
        train_bars=cfg.train_bars,
        validation_bars=cfg.validation_bars,
        test_bars=cfg.test_bars,
        step_bars=cfg.step_bars,
    ):
        selected = _select_parameter(split.train, cfg)
        split_results.append(
            {
                "split_id": split.split_id,
                "selected_min_edge_bps": selected,
                "train_metrics": _evaluate_window(split.train, selected, cfg),
                "validation_metrics": _evaluate_window(split.validation, selected, cfg),
                "test_metrics": _evaluate_window(split.test, selected, cfg),
                "dominant_test_regime": _dominant_regime(split.test),
            }
        )

    warnings = []
    warnings.extend(parameter_stability_warnings(split_results))
    warnings.extend(edge_degradation_warnings(split_results))
    aggregate = _aggregate(split_results)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "WARN" if warnings else "PASS",
        "split_count": len(split_results),
        "splits": split_results,
        "aggregate": aggregate,
        "warnings": sorted(set(warnings)),
        "baselines": _baselines(features),
        "regime_summary": regime_summary(split_results),
        "live_trading_enabled": False,
        "live_promotion_status": "LIVE_BLOCKED",
    }
    payload["report_paths"] = write_walk_forward_report(payload, output_root=output_root)
    return payload


def _select_parameter(frame: pd.DataFrame, config: WalkForwardConfig) -> float:
    scored = [
        (_evaluate_window(frame, candidate, config)["expectancy_after_costs_bps"], candidate)
        for candidate in config.candidate_min_edges_bps
    ]
    return float(max(scored, key=lambda item: (item[0], -item[1]))[1])


def _evaluate_window(
    frame: pd.DataFrame,
    min_edge_bps: float,
    config: WalkForwardConfig,
) -> dict[str, Any]:
    signals = generate_crypto_candidate_signals(frame, min_edge_bps=min_edge_bps)
    strategy_signals = [
        signal for signal in signals if signal.strategy_id != "random_placebo"
    ]
    realized = [
        _realized_signal_return_bps(frame, signal, horizon_bars=config.horizon_bars)
        for signal in strategy_signals
    ]
    realized = [item for item in realized if item is not None]
    gross = float(pd.Series(realized).mean()) if realized else 0.0
    expectancy = gross - config.cost_bps if realized else 0.0
    return {
        "signal_count": len(strategy_signals),
        "gross_expectancy_bps": gross,
        "expectancy_after_costs_bps": float(expectancy),
        "cost_bps": config.cost_bps,
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
        "mean_train_expectancy_after_costs_bps": _mean_metric(split_results, "train_metrics"),
        "mean_validation_expectancy_after_costs_bps": _mean_metric(
            split_results, "validation_metrics"
        ),
        "mean_test_expectancy_after_costs_bps": _mean_metric(split_results, "test_metrics"),
    }


def _mean_metric(split_results: list[dict[str, Any]], key: str) -> float:
    return float(
        pd.Series(
            [float(item[key]["expectancy_after_costs_bps"]) for item in split_results],
            dtype="float64",
        ).mean()
    )


def _baselines(features: pd.DataFrame) -> dict[str, dict[str, float]]:
    placebo = [
        _realized_signal_return_bps(features, signal, horizon_bars=5)
        for signal in generate_crypto_candidate_signals(features, min_edge_bps=999.0)
        if signal.strategy_id == "random_placebo"
    ]
    placebo = [item for item in placebo if item is not None]
    return {
        "no_trade": {"expectancy_after_costs_bps": 0.0, "signal_count": 0.0},
        "random_placebo": {
            "expectancy_after_costs_bps": float(pd.Series(placebo).mean()) if placebo else 0.0,
            "signal_count": float(len(placebo)),
        },
    }


def _dominant_regime(frame: pd.DataFrame) -> str:
    if "volatility_regime" not in frame or frame.empty:
        return "unknown"
    return str(frame["volatility_regime"].mode().iloc[0])
