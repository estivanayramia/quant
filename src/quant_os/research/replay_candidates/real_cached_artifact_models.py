from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from quant_os.data.crypto_spot_snapshots import parse_utc

ARTIFACT_TYPES = {
    "spot_snapshot",
    "spot_candle",
    "pm_market_window",
    "pm_clob_snapshot",
    "pm_trade_snapshot",
    "pm_window_label",
    "pm_resolution_label",
}
CAPTURE_MODES = {
    "real_cached_manual",
    "official_api_read_only",
    "public_static_read_only",
    "local_import",
    "fixture_real_shaped",
    "synthetic_stress",
}
PRIMARY_REAL_CACHED_CAPTURE_MODES = {
    "real_cached_manual",
    "official_api_read_only",
    "public_static_read_only",
    "local_import",
}
NON_PRIMARY_CAPTURE_MODES = {"fixture_real_shaped", "synthetic_stress"}


class RealCachedArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_type: str
    source_id: str
    capture_mode: str
    captured_at: str
    event_ts: str
    raw_hash: str
    normalized_hash: str
    source_url: str | None = None
    source_note: str | None = None
    provenance: dict[str, Any]
    quality_flags: list[str] = Field(default_factory=list)
    market_id: str | None = None
    condition_id: str | None = None
    slug: str | None = None
    token_id: str | None = None
    outcome: str | None = None
    spot_symbol: str | None = None
    window_start_ts: str | None = None
    window_end_ts: str | None = None
    tokens: list[dict[str, str]] | None = None
    clob_snapshot_id: str | None = None
    trade_id: str | None = None
    bid: float | None = None
    ask: float | None = None
    last_trade_price: float | None = None
    volume: float | None = None
    liquidity: float | None = None
    price: float | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    size: float | None = None
    side: str | None = None
    label_status: str | None = None
    resolved_outcome: str | None = None
    resolution_source_id: str | None = None

    @field_validator("artifact_type")
    @classmethod
    def _artifact_type_supported(cls, value: str) -> str:
        if value not in ARTIFACT_TYPES:
            raise ValueError("UNSUPPORTED_ARTIFACT_TYPE")
        return value

    @field_validator("capture_mode")
    @classmethod
    def _capture_mode_supported(cls, value: str) -> str:
        if value not in CAPTURE_MODES:
            raise ValueError("UNSUPPORTED_CAPTURE_MODE")
        return value

    @field_validator("captured_at", "event_ts", "window_start_ts", "window_end_ts")
    @classmethod
    def _timestamp_is_utc_z(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not value.endswith("Z"):
            raise ValueError("TIMESTAMP_NOT_UTC_Z")
        parse_utc(value)
        return value

    @model_validator(mode="after")
    def _required_type_fields_present(self) -> RealCachedArtifact:
        if not self.source_url and not self.source_note:
            raise ValueError("SOURCE_URL_OR_NOTE_REQUIRED")
        missing = [
            field
            for field in _required_fields_for_type(self.artifact_type)
            if getattr(self, field) in (None, "", [])
        ]
        if missing:
            raise ValueError(f"MISSING_REQUIRED_FIELDS:{','.join(sorted(missing))}")
        if self.artifact_type == "pm_market_window":
            for token in self.tokens or []:
                if not token.get("token_id") or not token.get("outcome"):
                    raise ValueError("MALFORMED_MARKET_TOKEN")
        if (
            self.artifact_type == "pm_clob_snapshot"
            and self.bid is not None
            and self.ask is not None
            and self.ask < self.bid
        ):
            raise ValueError("ASK_BELOW_BID")
        return self

    @property
    def source_quality(self) -> str:
        return source_quality_for_capture_mode(self.capture_mode)

    @property
    def artifact_key(self) -> tuple[str, str, str, str]:
        return (
            self.artifact_type,
            self.market_id or self.spot_symbol or "",
            self.token_id or "",
            self.window_start_ts or self.event_ts,
        )


def real_cached_primary_capture_mode(capture_mode: str) -> bool:
    return capture_mode in PRIMARY_REAL_CACHED_CAPTURE_MODES


def source_quality_for_capture_mode(capture_mode: str) -> str:
    if capture_mode in PRIMARY_REAL_CACHED_CAPTURE_MODES:
        return "real_cached"
    if capture_mode in NON_PRIMARY_CAPTURE_MODES:
        return capture_mode
    raise ValueError("UNSUPPORTED_CAPTURE_MODE")


def _required_fields_for_type(artifact_type: str) -> tuple[str, ...]:
    required = {
        "spot_snapshot": ("spot_symbol", "price"),
        "spot_candle": ("spot_symbol", "open", "high", "low", "close"),
        "pm_market_window": (
            "market_id",
            "condition_id",
            "slug",
            "spot_symbol",
            "window_start_ts",
            "window_end_ts",
            "tokens",
        ),
        "pm_clob_snapshot": (
            "market_id",
            "token_id",
            "clob_snapshot_id",
            "bid",
            "ask",
            "last_trade_price",
            "volume",
            "liquidity",
        ),
        "pm_trade_snapshot": ("market_id", "token_id", "trade_id", "price", "size", "side"),
        "pm_window_label": ("market_id", "label_status", "resolution_source_id"),
        "pm_resolution_label": ("market_id", "label_status", "resolution_source_id"),
    }
    return required[artifact_type]
