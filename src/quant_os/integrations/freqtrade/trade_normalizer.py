from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from quant_os.core.ids import deterministic_id
from quant_os.integrations.freqtrade.artifact_scanner import scan_freqtrade_artifacts
from quant_os.integrations.freqtrade.trade_artifacts import (
    DryRunTradeRecord,
    ParsedTradeArtifact,
    ensure_trade_report_dir,
    write_json_report,
)
from quant_os.integrations.freqtrade.trade_parser import parse_artifact


def ingest_trade_artifacts(write: bool = True) -> dict[str, Any]:
    scan = scan_freqtrade_artifacts(write=True)
    parsed: list[dict[str, Any]] = []
    warnings: list[str] = list(scan.get("warnings", []))
    errors: list[str] = []
    unsafe_evidence: list[str] = []
    for artifact in scan.get("artifacts", []):
        result = parse_artifact(artifact["path"], artifact.get("artifact_type"))
        parsed.append(result.model_dump(mode="json"))
        warnings.extend(result.warnings)
        errors.extend(result.errors)
        unsafe_evidence.extend(result.unsafe_evidence)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "FAIL" if unsafe_evidence else "WARN" if warnings else "PASS",
        "artifact_scan": scan,
        "parsed_artifacts": parsed,
        "parsed_records_count": sum(len(item["records"]) for item in parsed),
        "warnings": sorted(set(warnings)),
        "errors": sorted(set(errors)),
        "unsafe_evidence": sorted(set(unsafe_evidence)),
        "dry_run_only": True,
        "live_trading_enabled": False,
    }
    if not scan.get("artifacts"):
        payload["status"] = "UNAVAILABLE"
    if write:
        root = ensure_trade_report_dir()
        write_json_report(root / "latest_trades_ingested.json", payload)
    return payload


def normalize_trade_artifacts(
    parsed_artifacts: list[ParsedTradeArtifact | dict[str, Any]] | None = None,
    *,
    write: bool = True,
) -> dict[str, Any]:
    if parsed_artifacts is None:
        ingestion = ingest_trade_artifacts(write=True)
        parsed_artifacts = ingestion.get("parsed_artifacts", [])
    normalized: list[DryRunTradeRecord] = []
    warnings: list[str] = []
    unsafe_evidence: list[str] = []
    for item in parsed_artifacts:
        artifact = (
            item
            if isinstance(item, ParsedTradeArtifact)
            else ParsedTradeArtifact.model_validate(item)
        )
        warnings.extend(artifact.warnings)
        unsafe_evidence.extend(artifact.unsafe_evidence)
        for index, record in enumerate(artifact.records):
            normalized.append(
                _normalize_record(record, artifact.source_file, artifact.artifact_type, index)
            )
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "FAIL" if unsafe_evidence else "WARN" if warnings else "PASS",
        "normalized_records_count": len(normalized),
        "records": [record.model_dump(mode="json") for record in normalized],
        "warnings": sorted(set(warnings)),
        "unsafe_evidence": sorted(set(unsafe_evidence)),
        "dry_run_only": True,
        "live_trading_enabled": False,
    }
    if not normalized and not unsafe_evidence:
        payload["status"] = "UNAVAILABLE"
        payload["warnings"] = sorted(set([*payload["warnings"], "NO_NORMALIZED_TRADE_RECORDS"]))
    if write:
        root = ensure_trade_report_dir()
        write_json_report(root / "latest_trades_normalized.json", payload)
        try:
            from quant_os.projections.freqtrade_trades_projection import (
                rebuild_freqtrade_trades_projection,
            )

            rebuild_freqtrade_trades_projection(normalized)
            payload["duckdb_projection_path"] = "data/read_models/quant_os.duckdb"
            write_json_report(root / "latest_trades_normalized.json", payload)
        except Exception as exc:
            payload["warnings"] = sorted(
                set([*payload["warnings"], f"DUCKDB_PROJECTION_FAILED:{exc}"])
            )
            write_json_report(root / "latest_trades_normalized.json", payload)
    return payload


def _normalize_record(
    payload: dict[str, Any],
    source_file: str,
    artifact_type: str,
    index: int,
) -> DryRunTradeRecord:
    raw = json.loads(json.dumps(payload, default=str))
    pair = _first(payload, "pair", "symbol")
    symbol = str(pair).replace("/", "-") if pair else _first(payload, "symbol")
    side = _first(payload, "side", "trade_direction", "direction")
    inferred_side = False
    if side is None:
        side = "long"
        inferred_side = True
    if str(side).lower() in {"short", "sell_short"}:
        raw["normalization_warning"] = "SHORT_SIDE_NOT_INFERRED_OR_ALLOWED"
    elif inferred_side:
        raw["inferred_side"] = True
    source_record_id = str(_first(payload, "source_record_id", "trade_id", "id") or index)
    record_id = deterministic_id(
        "fttrade",
        source_file,
        source_record_id,
        json.dumps(raw, sort_keys=True, default=str),
        length=24,
    )
    return DryRunTradeRecord(
        record_id=record_id,
        source=artifact_type,
        source_file=source_file,
        source_record_id=source_record_id,
        strategy_name=_as_str(_first(payload, "strategy", "strategy_name")),
        pair=_as_str(pair),
        symbol=_as_str(symbol),
        side=_as_str(side),
        status=_normalize_status(payload),
        open_date=_as_datetime_string(_first(payload, "open_date", "open_timestamp", "open_time")),
        close_date=_as_datetime_string(
            _first(payload, "close_date", "close_timestamp", "close_time")
        ),
        open_rate=_as_float(_first(payload, "open_rate", "entry_price", "open_price")),
        close_rate=_as_float(_first(payload, "close_rate", "exit_price", "close_price")),
        amount=_as_float(_first(payload, "amount", "quantity")),
        stake_amount=_as_float(_first(payload, "stake_amount", "stake", "notional")),
        fee_open=_as_float(_first(payload, "fee_open", "open_fee")),
        fee_close=_as_float(_first(payload, "fee_close", "close_fee")),
        profit_abs=_as_float(_first(payload, "profit_abs", "realized_profit", "pnl")),
        profit_ratio=_as_float(_first(payload, "profit_ratio", "profit_pct", "profit_percent")),
        exit_reason=_as_str(_first(payload, "exit_reason", "sell_reason")),
        stop_loss_abs=_as_float(_first(payload, "stop_loss_abs", "stop_loss")),
        stop_loss_pct=_as_float(_first(payload, "stop_loss_pct", "stoploss_pct")),
        timeframe=_as_str(_first(payload, "timeframe")),
        dry_run=_as_bool(_first(payload, "dry_run")),
        raw_payload=raw,
        parsed_at=datetime.now(UTC).isoformat(),
    )


def _first(payload: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in payload and payload[key] not in {"", None}:
            return payload[key]
    return None


def _normalize_status(payload: dict[str, Any]) -> str | None:
    status = _first(payload, "status")
    if status:
        return str(status)
    is_open = payload.get("is_open")
    if is_open is True:
        return "open"
    if is_open is False:
        return "closed"
    return None


def _as_str(value: Any) -> str | None:
    return None if value is None else str(value)


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    if str(value).lower() in {"true", "1", "yes"}:
        return True
    if str(value).lower() in {"false", "0", "no"}:
        return False
    return None


def _as_datetime_string(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, int | float):
        timestamp = float(value)
        if timestamp > 10_000_000_000:
            timestamp = timestamp / 1000
        return datetime.fromtimestamp(timestamp, tz=UTC).isoformat()
    return str(value)
