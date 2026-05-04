from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from quant_os.core.errors import DataQualityError
from quant_os.data.freshness import evaluate_freshness
from quant_os.data.normalization import normalize_dataset_frame, normalize_symbol
from quant_os.data.quality import validate_canonical_frame
from quant_os.data.schemas import CANONICAL_SCHEMAS, DatasetKind, DatasetLayer
from quant_os.data.stores import LocalDatasetStore
from quant_os.research.common.joins import join_asof_reference_prices, join_forward_labels
from quant_os.research.common.reference_prices import build_reference_prices


def _raw_btc_eth() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": [
                "2026-01-01 00:00:00",
                "2026-01-01 00:01:00",
                "2026-01-01 00:00:00",
                "2026-01-01 00:01:00",
            ],
            "symbol": ["btc-usdt", "BTCUSDT", "eth-usdt", "ETHUSDT"],
            "open": [100.0, 101.0, 50.0, 51.0],
            "high": [102.0, 103.0, 52.0, 53.0],
            "low": [99.0, 100.0, 49.0, 50.0],
            "close": [101.0, 102.0, 51.0, 52.0],
            "volume": [10.0, 11.0, 20.0, 21.0],
            "venue": ["binance", "binance", "binance", "binance"],
            "timeframe": ["1m", "1m", "1m", "1m"],
        }
    )


def test_canonical_schemas_cover_sequence1_dataset_types() -> None:
    assert DatasetKind.CANDLE in CANONICAL_SCHEMAS
    assert DatasetKind.TRADE in CANONICAL_SCHEMAS
    assert DatasetKind.ORDERBOOK_SNAPSHOT in CANONICAL_SCHEMAS
    assert DatasetKind.FILL in CANONICAL_SCHEMAS
    assert DatasetKind.REFERENCE_PRICE in CANONICAL_SCHEMAS
    assert DatasetKind.OUTCOME_LABEL in CANONICAL_SCHEMAS
    assert CANONICAL_SCHEMAS[DatasetKind.CANDLE].version == "1.0"


def test_normalization_standardizes_time_and_crypto_symbols() -> None:
    normalized = normalize_dataset_frame(_raw_btc_eth(), DatasetKind.CANDLE)

    assert normalize_symbol("BTCUSDT") == "BTC/USDT"
    assert normalized["timestamp"].dt.tz is not None
    assert normalized["symbol"].tolist() == ["BTC/USDT", "BTC/USDT", "ETH/USDT", "ETH/USDT"]
    assert normalized["dataset_kind"].unique().tolist() == ["candles"]
    assert normalized["dataset_version"].unique().tolist() == ["1.0"]


def test_local_dataset_store_writes_layers_manifest_and_quality(tmp_path: Path) -> None:
    store = LocalDatasetStore(tmp_path)
    normalized = normalize_dataset_frame(_raw_btc_eth(), DatasetKind.CANDLE)

    record = store.write_dataset(
        normalized,
        dataset_id="crypto_btc_eth_1m",
        kind=DatasetKind.CANDLE,
        layer=DatasetLayer.NORMALIZED,
        source="fixture_binance",
    )

    loaded = store.read_dataset("crypto_btc_eth_1m", DatasetLayer.NORMALIZED)
    assert record.manifest_path.exists()
    assert record.rows == 4
    assert record.quality["status"] == "PASS"
    assert record.freshness.rows == 4
    assert loaded["symbol"].tolist() == normalized["symbol"].tolist()


def test_freshness_and_quality_block_stale_or_corrupt_data() -> None:
    stale = normalize_dataset_frame(_raw_btc_eth(), DatasetKind.CANDLE)
    freshness = evaluate_freshness(
        stale,
        max_age=pd.Timedelta(minutes=5),
        now=pd.Timestamp("2026-01-01T00:30:00Z"),
    )
    assert freshness.status == "STALE"
    assert "STALE_DATA" in freshness.reasons

    corrupt = stale.copy()
    corrupt.loc[0, "close"] = -1.0
    with pytest.raises(DataQualityError, match="NON_POSITIVE_PRICE"):
        validate_canonical_frame(corrupt, DatasetKind.CANDLE)


def test_research_joins_attach_reference_prices_and_labels() -> None:
    candles = normalize_dataset_frame(_raw_btc_eth(), DatasetKind.CANDLE)
    reference = build_reference_prices(candles)
    with_reference = join_asof_reference_prices(candles, reference)
    with_labels = join_forward_labels(with_reference, horizon_rows=1)

    assert "reference_price" in with_reference.columns
    assert "forward_return_1" in with_labels.columns
    btc = with_labels[with_labels["symbol"] == "BTC/USDT"].reset_index(drop=True)
    assert btc.loc[0, "forward_return_1"] == pytest.approx((102.0 / 101.0) - 1.0)
