from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd
from pydantic import BaseModel

DEFAULT_MAX_AGE = pd.Timedelta(minutes=5)


class FreshnessMetadata(BaseModel):
    status: str
    rows: int
    latest_timestamp: datetime | None
    age_seconds: float | None
    max_age_seconds: float
    reasons: list[str]


def evaluate_freshness(
    frame: pd.DataFrame,
    *,
    timestamp_column: str = "timestamp",
    max_age: pd.Timedelta = DEFAULT_MAX_AGE,
    now: pd.Timestamp | None = None,
) -> FreshnessMetadata:
    reference_now = pd.Timestamp(now or datetime.now(UTC))
    if reference_now.tzinfo is None:
        reference_now = reference_now.tz_localize("UTC")
    else:
        reference_now = reference_now.tz_convert("UTC")
    reasons: list[str] = []
    if frame.empty:
        return FreshnessMetadata(
            status="MISSING",
            rows=0,
            latest_timestamp=None,
            age_seconds=None,
            max_age_seconds=float(max_age.total_seconds()),
            reasons=["MISSING_DATA"],
        )
    if timestamp_column not in frame.columns:
        return FreshnessMetadata(
            status="FAIL",
            rows=int(len(frame)),
            latest_timestamp=None,
            age_seconds=None,
            max_age_seconds=float(max_age.total_seconds()),
            reasons=["MISSING_TIMESTAMP"],
        )
    timestamps = pd.to_datetime(frame[timestamp_column], utc=True)
    latest = pd.Timestamp(timestamps.max())
    age = reference_now - latest
    if age < pd.Timedelta(0):
        reasons.append("FUTURE_TIMESTAMP")
    if age > max_age:
        reasons.append("STALE_DATA")
    status = "PASS" if not reasons else "STALE" if "STALE_DATA" in reasons else "FAIL"
    return FreshnessMetadata(
        status=status,
        rows=int(len(frame)),
        latest_timestamp=latest.to_pydatetime(),
        age_seconds=float(age.total_seconds()),
        max_age_seconds=float(max_age.total_seconds()),
        reasons=reasons,
    )


def freshness_to_dict(metadata: FreshnessMetadata) -> dict[str, Any]:
    return metadata.model_dump(mode="json")
