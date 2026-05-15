from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CANDIDATE_ID = "pm_weather_forecast_market_mismatch"
REQUIRED_WEATHER_REPLAY_FIELDS = [
    "candidate_id",
    "market_id",
    "event_id",
    "location",
    "variable",
    "bucket_range",
    "forecast_value",
    "forecast_probability",
    "forecast_source",
    "forecast_ts",
    "market_price",
    "market_mid",
    "spread",
    "liquidity",
    "orderbook_ts",
    "resolution_value",
    "resolution_label",
    "resolution_ts",
    "known_at_ts",
    "source_quality",
    "provenance_hash",
]


class WeatherMarketReplayRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str = CANDIDATE_ID
    market_id: str
    event_id: str
    location: str
    variable: str
    bucket_range: str
    forecast_value: float
    forecast_probability: float
    forecast_source: str
    forecast_ts: str
    market_price: float
    market_mid: float
    spread: float
    liquidity: float
    orderbook_ts: str
    resolution_value: float | None = None
    resolution_label: str
    resolution_ts: str
    known_at_ts: str
    source_quality: str
    provenance_hash: str
    fixture_only: bool = False
    synthetic: bool = False
    proof_eligible: bool = True
    source_ids: list[str] = Field(default_factory=list)
    data_quality_flags: list[str] = Field(default_factory=list)

    @field_validator("candidate_id")
    @classmethod
    def _candidate_must_match(cls, value: str) -> str:
        if value != CANDIDATE_ID:
            raise ValueError(f"candidate_id must be {CANDIDATE_ID}")
        return value

    @field_validator("forecast_ts", "orderbook_ts", "resolution_ts", "known_at_ts")
    @classmethod
    def _timestamps_are_utc(cls, value: str) -> str:
        _parse_utc_timestamp(value)
        return value

    @field_validator("forecast_probability", "market_price", "market_mid")
    @classmethod
    def _probability_bounds(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("probability/price fields must be between 0 and 1")
        return value

    @field_validator("spread", "liquidity")
    @classmethod
    def _non_negative_market_quality(cls, value: float) -> float:
        if value < 0.0:
            raise ValueError("spread and liquidity must be non-negative")
        return value

    @model_validator(mode="after")
    def _no_lookahead_and_labels(self) -> WeatherMarketReplayRow:
        forecast_ts = _parse_utc_timestamp(self.forecast_ts)
        known_at_ts = _parse_utc_timestamp(self.known_at_ts)
        orderbook_ts = _parse_utc_timestamp(self.orderbook_ts)
        resolution_ts = _parse_utc_timestamp(self.resolution_ts)
        if forecast_ts > known_at_ts:
            raise ValueError("forecast_ts must be <= known_at_ts")
        if known_at_ts > orderbook_ts:
            raise ValueError("known_at_ts must be <= orderbook_ts")
        if self.proof_eligible and resolution_ts <= orderbook_ts:
            raise ValueError("resolution_ts must be after orderbook_ts for proof rows")
        if self.proof_eligible and not self.resolution_label:
            raise ValueError("resolution_label is required for proof rows")
        if self.proof_eligible and self.fixture_only:
            raise ValueError("fixture_only rows cannot be proof_eligible")
        return self

    def to_report_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


def build_weather_market_replay_schema() -> dict[str, Any]:
    return {
        "schema_version": "weather_market_replay_schema_v1",
        "sequence": "50",
        "candidate_id": CANDIDATE_ID,
        "required_fields": REQUIRED_WEATHER_REPLAY_FIELDS,
        "timestamp_policy": {
            "utc_required": True,
            "forecast_known_before_decision": "forecast_ts <= known_at_ts <= orderbook_ts",
            "resolution_after_decision_for_proof": "resolution_ts > orderbook_ts",
            "no_lookahead_required": True,
        },
        "label_policy": {
            "resolution_label_required_for_proof_rows": True,
            "fixture_rows_are_not_proof": True,
            "source_quality_separation_required": True,
        },
        "safety": {
            "public_read_only_only": True,
            "execution_authority": "NONE",
            "live_trading_enabled": False,
        },
    }


def build_fixture_weather_market_replay_row() -> dict[str, Any]:
    return {
        "candidate_id": CANDIDATE_ID,
        "market_id": "fixture_weather_market_001",
        "event_id": "fixture_weather_event_001",
        "location": "New York, NY",
        "variable": "temperature_max_f",
        "bucket_range": "70_to_74_f_inclusive",
        "forecast_value": 72.0,
        "forecast_probability": 0.68,
        "forecast_source": "fixture_public_weather_shape",
        "forecast_ts": "2026-05-15T11:00:00Z",
        "market_price": 0.44,
        "market_mid": 0.42,
        "spread": 0.04,
        "liquidity": 300.0,
        "orderbook_ts": "2026-05-15T12:05:00Z",
        "resolution_value": 73.0,
        "resolution_label": "IN_BUCKET",
        "resolution_ts": "2026-05-16T00:05:00Z",
        "known_at_ts": "2026-05-15T12:00:00Z",
        "source_quality": "SYNTHETIC_ONLY",
        "provenance_hash": "sha256:fixture_weather_market_mismatch_001",
        "fixture_only": True,
        "synthetic": True,
        "proof_eligible": False,
        "source_ids": ["fixture_weather", "fixture_market"],
        "data_quality_flags": ["fixture_only", "not_proof"],
    }


def load_weather_market_replay_rows(
    fixture_path: str | Path,
) -> list[WeatherMarketReplayRow]:
    path = _resolve_fixture_path(Path(fixture_path))
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_rows = payload["events"] if isinstance(payload, dict) else payload
    return [WeatherMarketReplayRow.model_validate(item) for item in raw_rows]


def _parse_utc_timestamp(value: str) -> datetime:
    if not value.endswith("Z"):
        raise ValueError("timestamp must be a normalized UTC string ending with Z")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo != UTC:
        raise ValueError("timestamp must be UTC")
    return parsed


def _resolve_fixture_path(path: Path) -> Path:
    if path.exists() or path.is_absolute():
        return path
    return Path(__file__).resolve().parents[4] / path
