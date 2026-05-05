from __future__ import annotations

import pandas as pd


def build_forward_return_labels(
    frame: pd.DataFrame,
    *,
    horizon_rows: int = 1,
    price_column: str = "close",
) -> pd.DataFrame:
    data = frame.sort_values(["symbol", "timestamp"]).copy()
    pieces = []
    for _, group in data.groupby("symbol", sort=False):
        group = group.copy()
        future = group[price_column].shift(-horizon_rows)
        group[f"forward_return_{horizon_rows}"] = future / group[price_column] - 1.0
        group[f"outcome_label_{horizon_rows}"] = (group[f"forward_return_{horizon_rows}"] > 0).astype(
            "float64"
        )
        pieces.append(group)
    return pd.concat(pieces).sort_index().reset_index(drop=True)
