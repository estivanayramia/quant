from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class WalkForwardSplit:
    split_id: int
    train: pd.DataFrame
    validation: pd.DataFrame
    test: pd.DataFrame


def rolling_walk_forward_splits(
    frame: pd.DataFrame,
    *,
    train_bars: int = 96,
    validation_bars: int = 48,
    test_bars: int = 48,
    step_bars: int = 48,
    max_splits: int = 8,
) -> list[WalkForwardSplit]:
    data = frame.sort_values("timestamp").reset_index(drop=True)
    timestamps = pd.Series(data["timestamp"].drop_duplicates().sort_values().to_list())
    splits: list[WalkForwardSplit] = []
    start = 0
    width = train_bars + validation_bars + test_bars
    while start + width <= len(timestamps) and len(splits) < max_splits:
        train_ts = set(timestamps.iloc[start : start + train_bars])
        validation_ts = set(timestamps.iloc[start + train_bars : start + train_bars + validation_bars])
        test_ts = set(timestamps.iloc[start + train_bars + validation_bars : start + width])
        train = data[data["timestamp"].isin(train_ts)].copy()
        validation = data[data["timestamp"].isin(validation_ts)].copy()
        test = data[data["timestamp"].isin(test_ts)].copy()
        splits.append(
            WalkForwardSplit(
                split_id=len(splits) + 1,
                train=train,
                validation=validation,
                test=test,
            )
        )
        start += step_bars
    return splits
