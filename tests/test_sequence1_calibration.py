from __future__ import annotations

import pytest

from quant_os.research.calibration.diagnostics import calibration_diagnostics
from quant_os.research.calibration.penalties import apply_edge_penalties
from quant_os.research.calibration.probabilities import estimate_signal_probability
from quant_os.research.calibration.sizing import size_from_edge
from quant_os.research.calibration.uncertainty import estimate_uncertainty


def test_probability_and_uncertainty_outputs_are_bounded() -> None:
    probability = estimate_signal_probability(
        raw_score=0.75,
        volatility_regime="normal",
        liquidity_score=0.8,
        overextension_z=0.4,
    )
    uncertainty = estimate_uncertainty(sample_size=80, regime_observations=20, feature_stability=0.7)

    assert 0.0 < probability < 1.0
    assert 0.0 <= uncertainty <= 1.0


def test_minimum_edge_threshold_blocks_weak_or_penalized_setups() -> None:
    edge = apply_edge_penalties(
        probability=0.505,
        payoff_ratio=1.0,
        cost_bps=6.0,
        correlated_signal_count=3,
        liquidity_score=0.2,
        overextension_z=2.5,
    )

    assert edge.approved is False
    assert edge.size_multiplier == 0.0
    assert "EDGE_BELOW_THRESHOLD" in edge.reason_codes
    assert "WEAK_LIQUIDITY" in edge.reason_codes


def test_uncertainty_reduces_size_without_full_kelly() -> None:
    certain = size_from_edge(edge_bps=30.0, uncertainty=0.1, max_fraction=0.05)
    uncertain = size_from_edge(edge_bps=30.0, uncertainty=0.8, max_fraction=0.05)

    assert 0.0 < uncertain < certain < 0.05


def test_correlation_penalty_reduces_edge_estimate() -> None:
    solo = apply_edge_penalties(
        probability=0.56,
        payoff_ratio=1.1,
        cost_bps=4.0,
        correlated_signal_count=0,
        liquidity_score=0.9,
        overextension_z=0.4,
    )
    crowded = apply_edge_penalties(
        probability=0.56,
        payoff_ratio=1.1,
        cost_bps=4.0,
        correlated_signal_count=4,
        liquidity_score=0.9,
        overextension_z=0.4,
    )

    assert crowded.edge_bps < solo.edge_bps
    assert "CORRELATED_SIGNALS" in crowded.reason_codes


def test_calibration_diagnostics_include_core_scores() -> None:
    diagnostics = calibration_diagnostics(
        probabilities=[0.2, 0.4, 0.7, 0.9],
        outcomes=[0, 0, 1, 1],
        expected_returns_bps=[-4.0, -1.0, 8.0, 12.0],
        equity_curve=[100.0, 99.0, 101.0, 104.0],
        regimes=["low", "low", "high", "high"],
    )

    assert diagnostics["brier_score"] == pytest.approx(0.075)
    assert diagnostics["log_loss"] > 0
    assert diagnostics["expectancy_after_costs"] == pytest.approx(3.75)
    assert diagnostics["walk_forward_stability"] > 0
    assert diagnostics["regime_sensitivity"]["high"] != diagnostics["regime_sensitivity"]["low"]
    assert len(diagnostics["calibration_curve"]) > 0
