from __future__ import annotations

from typing import Any

import pandas as pd


def detect_fvg(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Placeholder interface for fair value gap research, not a proven edge."""
    _ = frame
    return []


def detect_bos_choch(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Placeholder interface for BOS/CHOCH research, not a proven edge."""
    _ = frame
    return []


def detect_liquidity_sweep(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Placeholder interface for liquidity sweep research, not a proven edge."""
    _ = frame
    return []


def detect_order_block(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Placeholder interface for order-block research, not a proven edge."""
    _ = frame
    return []
