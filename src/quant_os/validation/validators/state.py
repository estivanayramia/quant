from __future__ import annotations


def reconciliation_passes(local_quantity: float, external_quantity: float) -> bool:
    return abs(local_quantity - external_quantity) <= 1e-9
