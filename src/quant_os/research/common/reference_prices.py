from __future__ import annotations

import pandas as pd

from quant_os.data.normalization import normalize_dataset_frame
from quant_os.data.schemas import DatasetKind


def build_reference_prices(frame: pd.DataFrame, *, price_column: str = "close") -> pd.DataFrame:
    data = normalize_dataset_frame(frame, DatasetKind.CANDLE)
    reference = data[["timestamp", "symbol", price_column]].copy()
    reference = reference.rename(columns={price_column: "reference_price"})
    reference["method"] = "last_close"
    reference["dataset_kind"] = DatasetKind.REFERENCE_PRICE.value
    reference["dataset_version"] = "1.0"
    return reference.sort_values(["symbol", "timestamp"]).reset_index(drop=True)
