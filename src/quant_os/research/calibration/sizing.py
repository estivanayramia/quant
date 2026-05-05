from __future__ import annotations


def size_from_edge(edge_bps: float, uncertainty: float, max_fraction: float = 0.02) -> float:
    if edge_bps <= 0:
        return 0.0
    bounded_uncertainty = max(0.0, min(1.0, uncertainty))
    conservative_edge_scale = min(1.0, edge_bps / 100.0)
    return float(max_fraction * conservative_edge_scale * (1.0 - bounded_uncertainty))
