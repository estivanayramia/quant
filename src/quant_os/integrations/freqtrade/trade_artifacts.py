from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

TRADE_REPORT_DIR = Path("reports/freqtrade/trades")


class FreqtradeArtifact(BaseModel):
    path: str
    artifact_type: str
    size_bytes: int
    modified_at: str
    sha256: str
    possible_trade_db: bool = False
    skipped: bool = False
    skip_reason: str | None = None


class ParsedTradeArtifact(BaseModel):
    source_file: str
    artifact_type: str
    records: list[dict[str, Any]] = Field(default_factory=list)
    raw_events: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    unsafe_evidence: list[str] = Field(default_factory=list)


class DryRunTradeRecord(BaseModel):
    record_id: str
    source: str
    source_file: str
    source_record_id: str | None = None
    strategy_name: str | None = None
    pair: str | None = None
    symbol: str | None = None
    side: str | None = None
    status: str | None = None
    open_date: str | None = None
    close_date: str | None = None
    open_rate: float | None = None
    close_rate: float | None = None
    amount: float | None = None
    stake_amount: float | None = None
    fee_open: float | None = None
    fee_close: float | None = None
    profit_abs: float | None = None
    profit_ratio: float | None = None
    exit_reason: str | None = None
    stop_loss_abs: float | None = None
    stop_loss_pct: float | None = None
    timeframe: str | None = None
    dry_run: bool | None = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    parsed_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


def ensure_trade_report_dir() -> Path:
    TRADE_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    return TRADE_REPORT_DIR


def write_json_report(path: str | Path, payload: dict[str, Any] | list[Any]) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return output


def status_from_findings(
    *,
    failures: list[Any] | None = None,
    warnings: list[Any] | None = None,
    unavailable: bool = False,
) -> str:
    if failures:
        return "FAIL"
    if unavailable:
        return "UNAVAILABLE"
    if warnings:
        return "WARN"
    return "PASS"
