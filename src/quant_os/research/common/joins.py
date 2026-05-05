from __future__ import annotations

import pandas as pd

from quant_os.data.labels import build_forward_return_labels


def join_asof_reference_prices(frame: pd.DataFrame, reference_prices: pd.DataFrame) -> pd.DataFrame:
    pieces = []
    left = frame.sort_values(["symbol", "timestamp"]).copy()
    right = reference_prices.sort_values(["symbol", "timestamp"]).copy()
    for symbol, group in left.groupby("symbol", sort=False):
        reference = right[right["symbol"] == symbol]
        joined = pd.merge_asof(
            group.sort_values("timestamp"),
            reference[["timestamp", "reference_price"]].sort_values("timestamp"),
            on="timestamp",
            direction="backward",
        )
        joined["symbol"] = symbol
        pieces.append(joined)
    return pd.concat(pieces).sort_values(["symbol", "timestamp"]).reset_index(drop=True)


def join_forward_labels(frame: pd.DataFrame, *, horizon_rows: int = 1) -> pd.DataFrame:
    return build_forward_return_labels(frame, horizon_rows=horizon_rows)
