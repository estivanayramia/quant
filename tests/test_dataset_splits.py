from __future__ import annotations

import pandas as pd

from quant_os.data.dataset_splits import split_frame_ranges, walk_forward_ranges
from quant_os.data.leakage_checks import ordered_before, ranges_overlap


def _frame(rows: int = 100) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=rows, freq="1h", tz="UTC"),
            "symbol": ["SPY"] * rows,
            "timeframe": ["1h"] * rows,
        }
    )


def test_dataset_splits_do_not_overlap() -> None:
    splits = split_frame_ranges(_frame(), purge_gap_bars=1)
    assert not ranges_overlap(splits["train"], splits["validation"])
    assert not ranges_overlap(splits["validation"], splits["test"])


def test_walk_forward_splits_are_ordered() -> None:
    windows = walk_forward_ranges(_frame(), min_splits=3, purge_gap_bars=1)
    assert len(windows) == 3
    assert all(ordered_before(window["train"], window["test"]) for window in windows)
