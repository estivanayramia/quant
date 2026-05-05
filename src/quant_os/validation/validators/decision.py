from __future__ import annotations


def should_trade(edge_bps: float, threshold_bps: float = 10.0) -> bool:
    return edge_bps >= threshold_bps
