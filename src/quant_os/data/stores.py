from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import BaseModel, ConfigDict

from quant_os.data.freshness import FreshnessMetadata, evaluate_freshness
from quant_os.data.quality import validate_canonical_frame
from quant_os.data.schemas import CANONICAL_SCHEMAS, DatasetKind, DatasetLayer


class DatasetRecord(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    dataset_id: str
    kind: DatasetKind
    layer: DatasetLayer
    version: str
    source: str
    path: Path
    manifest_path: Path
    rows: int
    sha256: str
    freshness: FreshnessMetadata
    quality: dict[str, Any]
    written_at: datetime
    live_trading_enabled: bool = False


class LocalDatasetStore:
    def __init__(self, root: str | Path = "data/sequence1") -> None:
        self.root = Path(root)

    def write_dataset(
        self,
        frame: pd.DataFrame,
        *,
        dataset_id: str,
        kind: DatasetKind | str,
        layer: DatasetLayer | str,
        source: str,
    ) -> DatasetRecord:
        dataset_kind = DatasetKind(kind)
        dataset_layer = DatasetLayer(layer)
        schema = CANONICAL_SCHEMAS[dataset_kind]
        quality = validate_canonical_frame(frame, dataset_kind)
        freshness = evaluate_freshness(
            frame,
            max_age=pd.Timedelta(days=3650),
            now=pd.Timestamp(frame["timestamp"].max()) if "timestamp" in frame else None,
        )
        output_dir = self.root / dataset_layer.value / dataset_id / f"v{schema.version}"
        output_dir.mkdir(parents=True, exist_ok=True)
        data_path = output_dir / "data.parquet"
        frame.to_parquet(data_path, index=False)
        record = DatasetRecord(
            dataset_id=dataset_id,
            kind=dataset_kind,
            layer=dataset_layer,
            version=schema.version,
            source=source,
            path=data_path,
            manifest_path=output_dir / "manifest.json",
            rows=int(len(frame)),
            sha256=_sha256(data_path),
            freshness=freshness,
            quality=quality,
            written_at=datetime.now(UTC),
        )
        record.manifest_path.write_text(
            json.dumps(record.model_dump(mode="json"), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return record

    def read_dataset(self, dataset_id: str, layer: DatasetLayer | str) -> pd.DataFrame:
        dataset_layer = DatasetLayer(layer)
        candidates = sorted((self.root / dataset_layer.value / dataset_id).glob("v*/data.parquet"))
        if not candidates:
            msg = f"dataset not found: {dataset_id} layer={dataset_layer.value}"
            raise FileNotFoundError(msg)
        return pd.read_parquet(candidates[-1])


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
