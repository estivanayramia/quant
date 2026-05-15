from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

CANDIDATE_ID = "pm_lp_refresh_lag_arbitrage"
ALIASES = [
    "pm_stale_lp_quote_arbitrage",
    "pm_refresh_lag_window",
]

REQUIRED_PM_LP_REFRESH_LAG_FIELDS = [
    "candidate_id",
    "event_id",
    "event_type",
    "market_id",
    "condition_id",
    "token_id",
    "outcome",
    "window_start_ts",
    "window_end_ts",
    "fill_ts",
    "quote_seen_ts",
    "quote_refresh_ts",
    "quote_refresh_lag_ms",
    "stale_quote_side",
    "stale_quote_price",
    "stale_quote_size",
    "opposite_quote_price_after_fill",
    "pre_fill_best_bid",
    "pre_fill_best_ask",
    "post_fill_best_bid",
    "post_fill_best_ask",
    "spread_bps_before",
    "spread_bps_after",
    "two_sided_quote_present",
    "maker_attribution_public",
    "maker_label_source",
    "liquidity_reward_market",
    "inter_trade_interval_ms",
    "taker_burst_trade_count",
    "spot_symbol",
    "spot_trigger_source",
    "spot_return_1s",
    "spot_return_5s",
    "directional_trigger",
    "resolution_label",
    "fill_realism",
    "source_ids",
    "provenance_hash",
    "data_quality_flags",
]


class PmLpRefreshLagReplayEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str = CANDIDATE_ID
    event_id: str
    event_type: str = "refresh_lag_window"
    market_id: str
    condition_id: str
    token_id: str
    outcome: str
    window_start_ts: str
    window_end_ts: str
    fill_ts: str
    quote_seen_ts: str
    quote_refresh_ts: str
    quote_refresh_lag_ms: int
    stale_quote_side: str
    stale_quote_price: float
    stale_quote_size: float
    opposite_quote_price_after_fill: float
    pre_fill_best_bid: float
    pre_fill_best_ask: float
    post_fill_best_bid: float
    post_fill_best_ask: float
    spread_bps_before: float
    spread_bps_after: float
    two_sided_quote_present: bool
    maker_attribution_public: bool
    maker_label_source: str
    liquidity_reward_market: bool
    inter_trade_interval_ms: int
    taker_burst_trade_count: int
    spot_symbol: str
    spot_trigger_source: str
    spot_return_1s: float | None = None
    spot_return_5s: float | None = None
    directional_trigger: str
    resolution_label: str
    fill_realism: dict[str, Any] = Field(default_factory=dict)
    source_ids: list[str] = Field(default_factory=list)
    provenance_hash: str
    data_quality_flags: list[str] = Field(default_factory=list)

    @field_validator("candidate_id")
    @classmethod
    def _candidate_must_match(cls, value: str) -> str:
        if value != CANDIDATE_ID:
            raise ValueError(f"candidate_id must be {CANDIDATE_ID}")
        return value

    @field_validator("event_type")
    @classmethod
    def _event_type_must_match(cls, value: str) -> str:
        if value != "refresh_lag_window":
            raise ValueError("event_type must be refresh_lag_window")
        return value

    @field_validator(
        "window_start_ts",
        "window_end_ts",
        "fill_ts",
        "quote_seen_ts",
        "quote_refresh_ts",
    )
    @classmethod
    def _timestamps_are_utc_strings(cls, value: str) -> str:
        if not value.endswith("Z"):
            raise ValueError("timestamp must be a normalized UTC string ending with Z")
        return value

    @field_validator("stale_quote_side")
    @classmethod
    def _stale_quote_side_is_known(cls, value: str) -> str:
        if value not in {"BID", "ASK"}:
            raise ValueError("stale_quote_side must be BID or ASK")
        return value

    @field_validator("directional_trigger")
    @classmethod
    def _directional_trigger_is_known(cls, value: str) -> str:
        if value not in {"UP", "DOWN", "FLAT"}:
            raise ValueError("directional_trigger must be UP, DOWN, or FLAT")
        return value

    def to_report_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


def build_pm_lp_refresh_lag_replay_schema() -> dict[str, Any]:
    return {
        "schema_version": "pm_lp_refresh_lag_replay_schema_v1",
        "sequence": "47",
        "candidate_id": CANDIDATE_ID,
        "aliases": ALIASES,
        "event_type": "refresh_lag_window",
        "event_definition": {
            "refresh_lag_window": (
                "A fixture-safe event describing a public orderbook/trade interval where "
                "a stale opposite-side quote remains visible after a fill while a public "
                "directional trigger moves fair value."
            ),
            "required_window_fields": REQUIRED_PM_LP_REFRESH_LAG_FIELDS,
            "stale_quote_event_definition": [
                "maker-style two-sided quote observed from public orderbook snapshots",
                "public fill or trade event hits one side",
                "opposite-side quote remains visible for quote_refresh_lag_ms",
                "directional trigger and taker-burst context are timestamp-aligned",
            ],
            "fill_realism_required_fields": [
                "queue_position_observed",
                "expected_fill_fraction",
                "requires_future_model",
            ],
        },
        "label_policy": {
            "resolution_label_required": True,
            "fill_or_no_fill_label_required_before_replay": True,
            "claimed_profit_and_loss_ignored": True,
        },
        "safety": {
            "public_read_only_only": True,
            "wallet_labels_are_not_truth": True,
            "execution_authority": "NONE",
            "live_trading_enabled": False,
        },
    }


def load_pm_lp_refresh_lag_fixture_events(
    fixture_path: str | Path,
) -> list[PmLpRefreshLagReplayEvent]:
    payload = json.loads(Path(fixture_path).read_text(encoding="utf-8"))
    raw_events = payload["events"] if isinstance(payload, dict) else payload
    return [PmLpRefreshLagReplayEvent.model_validate(item) for item in raw_events]
