from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel

REQUIRED_OHLCV_COLUMNS = ["timestamp", "symbol", "open", "high", "low", "close", "volume"]


OHLCV_DTYPES = {
    "symbol": "string",
    "open": "float64",
    "high": "float64",
    "low": "float64",
    "close": "float64",
    "volume": "float64",
}


class DatasetLayer(StrEnum):
    RAW = "raw"
    NORMALIZED = "normalized"
    DERIVED = "derived"


class DatasetKind(StrEnum):
    TRADE = "trades"
    ORDERBOOK_SNAPSHOT = "orderbook_snapshots"
    ORDERBOOK_DELTA = "orderbook_deltas"
    CANDLE = "candles"
    VENUE_METADATA = "venue_metadata"
    FILL = "fills"
    REFERENCE_PRICE = "reference_prices"
    OUTCOME_LABEL = "outcome_labels"


class DatasetSchema(BaseModel):
    kind: DatasetKind
    version: str
    required_columns: list[str]
    optional_columns: list[str] = []
    primary_key: list[str]
    timestamp_column: str = "timestamp"


CANONICAL_SCHEMAS: dict[DatasetKind, DatasetSchema] = {
    DatasetKind.TRADE: DatasetSchema(
        kind=DatasetKind.TRADE,
        version="1.0",
        required_columns=["timestamp", "symbol", "venue", "trade_id", "price", "quantity", "side"],
        optional_columns=["dataset_kind", "dataset_version", "received_at"],
        primary_key=["venue", "symbol", "trade_id"],
    ),
    DatasetKind.ORDERBOOK_SNAPSHOT: DatasetSchema(
        kind=DatasetKind.ORDERBOOK_SNAPSHOT,
        version="1.0",
        required_columns=["timestamp", "symbol", "venue", "bid_price", "bid_size", "ask_price", "ask_size"],
        optional_columns=["level", "dataset_kind", "dataset_version", "received_at"],
        primary_key=["venue", "symbol", "timestamp", "level"],
    ),
    DatasetKind.ORDERBOOK_DELTA: DatasetSchema(
        kind=DatasetKind.ORDERBOOK_DELTA,
        version="1.0",
        required_columns=["timestamp", "symbol", "venue", "side", "price", "quantity_delta"],
        optional_columns=["sequence", "dataset_kind", "dataset_version", "received_at"],
        primary_key=["venue", "symbol", "timestamp", "side", "price"],
    ),
    DatasetKind.CANDLE: DatasetSchema(
        kind=DatasetKind.CANDLE,
        version="1.0",
        required_columns=[
            "timestamp",
            "symbol",
            "venue",
            "timeframe",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ],
        optional_columns=["dataset_kind", "dataset_version", "received_at", "source"],
        primary_key=["venue", "symbol", "timeframe", "timestamp"],
    ),
    DatasetKind.VENUE_METADATA: DatasetSchema(
        kind=DatasetKind.VENUE_METADATA,
        version="1.0",
        required_columns=["timestamp", "venue", "symbol", "status"],
        optional_columns=["base_asset", "quote_asset", "min_notional", "tick_size", "lot_size"],
        primary_key=["venue", "symbol", "timestamp"],
    ),
    DatasetKind.FILL: DatasetSchema(
        kind=DatasetKind.FILL,
        version="1.0",
        required_columns=[
            "timestamp",
            "symbol",
            "venue",
            "fill_id",
            "order_id",
            "side",
            "price",
            "quantity",
            "fee",
        ],
        optional_columns=["liquidity", "strategy_id", "dataset_kind", "dataset_version"],
        primary_key=["venue", "fill_id"],
    ),
    DatasetKind.REFERENCE_PRICE: DatasetSchema(
        kind=DatasetKind.REFERENCE_PRICE,
        version="1.0",
        required_columns=["timestamp", "symbol", "reference_price"],
        optional_columns=["venue", "method", "dataset_kind", "dataset_version"],
        primary_key=["symbol", "timestamp"],
    ),
    DatasetKind.OUTCOME_LABEL: DatasetSchema(
        kind=DatasetKind.OUTCOME_LABEL,
        version="1.0",
        required_columns=["timestamp", "symbol", "label_name", "label_value"],
        optional_columns=["horizon", "dataset_kind", "dataset_version"],
        primary_key=["symbol", "timestamp", "label_name"],
    ),
}
