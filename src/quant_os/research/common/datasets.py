from __future__ import annotations

from pathlib import Path

import pandas as pd

from quant_os.data.normalization import normalize_dataset_frame
from quant_os.data.schemas import DatasetKind, DatasetLayer
from quant_os.data.stores import DatasetRecord, LocalDatasetStore


def write_normalized_dataset(
    frame: pd.DataFrame,
    *,
    output_root: str | Path,
    dataset_id: str,
    kind: DatasetKind,
    source: str,
) -> DatasetRecord:
    normalized = normalize_dataset_frame(frame, kind)
    store = LocalDatasetStore(Path(output_root) / "data" / "sequence1")
    return store.write_dataset(
        normalized,
        dataset_id=dataset_id,
        kind=kind,
        layer=DatasetLayer.NORMALIZED,
        source=source,
    )
