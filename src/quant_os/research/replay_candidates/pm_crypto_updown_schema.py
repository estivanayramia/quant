from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

CANDIDATE_ID = "pm_crypto_updown_repricing_lag"

REQUIRED_PM_CRYPTO_UPDOWN_FIELDS = [
    "candidate_id",
    "market_id",
    "condition_id",
    "slug",
    "token_id",
    "outcome",
    "window_start_ts",
    "window_end_ts",
    "event_ts",
    "seconds_to_window_end",
    "spot_symbol",
    "spot_price",
    "spot_return_1s",
    "spot_return_5s",
    "spot_return_15s",
    "market_bid",
    "market_ask",
    "market_mid",
    "market_spread",
    "market_last_trade_price",
    "market_volume",
    "market_liquidity",
    "clob_snapshot_id",
    "source_ids",
    "provenance_hash",
    "data_quality_flags",
    "label_status",
    "resolved_outcome",
]


class PmCryptoUpDownReplayRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str = CANDIDATE_ID
    market_id: str
    condition_id: str
    slug: str
    token_id: str
    outcome: str
    window_start_ts: str
    window_end_ts: str
    event_ts: str
    seconds_to_window_end: float
    spot_symbol: str
    spot_price: float | None
    spot_return_1s: float | None = None
    spot_return_5s: float | None = None
    spot_return_15s: float | None = None
    market_bid: float | None
    market_ask: float | None
    market_mid: float | None
    market_spread: float | None
    market_last_trade_price: float | None
    market_volume: float | None
    market_liquidity: float | None
    clob_snapshot_id: str
    source_ids: list[str] = Field(default_factory=list)
    provenance_hash: str
    data_quality_flags: list[str] = Field(default_factory=list)
    label_status: str
    resolved_outcome: str | None = None

    @field_validator("candidate_id")
    @classmethod
    def _candidate_must_match(cls, value: str) -> str:
        if value != CANDIDATE_ID:
            raise ValueError(f"candidate_id must be {CANDIDATE_ID}")
        return value

    @field_validator("window_start_ts", "window_end_ts", "event_ts")
    @classmethod
    def _timestamps_are_utc_strings(cls, value: str) -> str:
        if not value.endswith("Z"):
            raise ValueError("timestamp must be a normalized UTC string ending with Z")
        return value

    def to_report_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
