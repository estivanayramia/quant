from __future__ import annotations

from pydantic import BaseModel

from quant_os.research.calibration.sizing import size_from_edge


class EdgeEstimate(BaseModel):
    approved: bool
    probability: float
    gross_edge_bps: float
    edge_bps: float
    size_multiplier: float
    reason_codes: list[str]


def apply_edge_penalties(
    *,
    probability: float,
    payoff_ratio: float,
    cost_bps: float,
    correlated_signal_count: int,
    liquidity_score: float,
    overextension_z: float,
    minimum_edge_bps: float = 10.0,
    uncertainty: float = 0.35,
) -> EdgeEstimate:
    bounded_probability = max(0.01, min(0.99, probability))
    gross_edge_bps = ((bounded_probability * payoff_ratio) - (1.0 - bounded_probability)) * 1_000.0
    edge_bps = gross_edge_bps - cost_bps
    reasons: list[str] = []
    if correlated_signal_count > 0:
        edge_bps *= max(0.25, 1.0 - correlated_signal_count * 0.12)
        reasons.append("CORRELATED_SIGNALS")
    if liquidity_score < 0.35:
        edge_bps *= max(0.1, liquidity_score)
        reasons.append("WEAK_LIQUIDITY")
    if abs(overextension_z) > 2.0:
        edge_bps *= 0.55
        reasons.append("OVEREXTENSION_RISK")
    if edge_bps < minimum_edge_bps:
        reasons.append("EDGE_BELOW_THRESHOLD")
    approved = "EDGE_BELOW_THRESHOLD" not in reasons
    size_multiplier = size_from_edge(edge_bps, uncertainty, max_fraction=0.05) if approved else 0.0
    return EdgeEstimate(
        approved=approved,
        probability=float(bounded_probability),
        gross_edge_bps=float(gross_edge_bps),
        edge_bps=float(edge_bps),
        size_multiplier=float(size_multiplier),
        reason_codes=reasons,
    )
