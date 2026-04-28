from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from quant_os.adapters.market_data_parquet import LocalParquetMarketData
from quant_os.data.demo_data import seed_demo_data
from quant_os.features.sessions import add_session_features
from quant_os.features.smc_scoring import add_smc_scores
from quant_os.features.technical import moving_average, returns
from quant_os.features.volatility import add_volatility_features
from quant_os.projections.feature_projection import rebuild_feature_projection


def build_feature_frame(frame: pd.DataFrame | None = None) -> pd.DataFrame:
    if frame is None and not list(Path("data/demo").glob("*.parquet")):
        seed_demo_data()
    data = frame.copy() if frame is not None else LocalParquetMarketData().load()
    data = data.sort_values(["symbol", "timestamp"]).copy()
    data = add_volatility_features(data)
    pieces = []
    for _, group in data.groupby("symbol", sort=False):
        group = group.copy()
        group["ma_fast"] = moving_average(group["close"], 5)
        group["ma_slow"] = moving_average(group["close"], 20)
        group["ma_distance"] = (group["ma_fast"] - group["ma_slow"]) / group["close"]
        group["volume_ma"] = group["volume"].rolling(20, min_periods=1).mean()
        volume_std = group["volume"].rolling(20, min_periods=2).std().replace(0, pd.NA)
        group["volume_zscore"] = ((group["volume"] - group["volume_ma"]) / volume_std).fillna(0.0)
        group["returns"] = returns(group["close"])
        pieces.append(group)
    data = pd.concat(pieces).sort_index()
    data = add_session_features(data)
    data = add_smc_scores(data)
    return data.sort_values(["symbol", "timestamp"]).reset_index(drop=True)


def write_feature_store(
    frame: pd.DataFrame | None = None,
    output_path: str | Path = "reports/features/latest_features.parquet",
) -> dict[str, Any]:
    features = build_feature_frame(frame)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    features.to_parquet(path, index=False)
    summary = {
        "generated_at": datetime.now(UTC).isoformat(),
        "rows": len(features),
        "symbols": sorted(features["symbol"].unique().tolist()),
        "columns": sorted(features.columns.tolist()),
        "features_path": str(path),
        "live_trading_enabled": False,
    }
    summary_path = path.parent / "latest_features_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True, default=str), encoding="utf-8"
    )
    rebuild_feature_projection(features)
    return summary
