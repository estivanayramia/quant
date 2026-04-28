from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from quant_os.integrations.freqtrade.trade_artifacts import ParsedTradeArtifact

PAIR_PATTERN = re.compile(r"\b([A-Z0-9]+/[A-Z0-9]+)\b")
LIVE_DANGER_PATTERNS = [
    "dry_run false",
    "dry-run false",
    '"dry_run": false',
    "live mode",
    "live trading enabled",
    "real order",
    "exchange key",
    "api secret",
]
SECRET_FIELD_NAMES = {"key", "secret", "password", "uid", "api_key", "api_secret"}
UNSAFE_MODE_FIELDS = {"futures", "margin", "shorting", "can_short", "options"}


def parse_artifact(path: str | Path, artifact_type: str | None = None) -> ParsedTradeArtifact:
    artifact = Path(path)
    kind = artifact_type or _classify(artifact)
    if kind == "json":
        return parse_json_artifact(artifact)
    if kind == "jsonl":
        return parse_jsonl_artifact(artifact)
    if kind == "log":
        return parse_log_artifact(artifact)
    if kind == "sqlite":
        return parse_sqlite_artifact(artifact)
    return ParsedTradeArtifact(
        source_file=str(artifact),
        artifact_type=kind,
        warnings=["UNKNOWN_ARTIFACT_TYPE"],
        raw_events=[],
    )


def parse_json_artifact(path: str | Path) -> ParsedTradeArtifact:
    artifact = Path(path)
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    records, warnings = _extract_records(payload)
    unsafe = detect_unsafe_evidence(payload)
    return ParsedTradeArtifact(
        source_file=str(artifact),
        artifact_type="json",
        records=records,
        raw_events=[] if records else [{"raw_payload": payload}],
        warnings=warnings,
        unsafe_evidence=unsafe,
    )


def parse_jsonl_artifact(path: str | Path) -> ParsedTradeArtifact:
    artifact = Path(path)
    records: list[dict[str, Any]] = []
    warnings: list[str] = []
    unsafe: list[str] = []
    raw_events: list[dict[str, Any]] = []
    for line_number, line in enumerate(artifact.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            warnings.append(f"MALFORMED_JSONL_LINE:{line_number}")
            raw_events.append({"line_number": line_number, "raw": line})
            continue
        unsafe.extend(detect_unsafe_evidence(payload))
        if _looks_like_trade(payload):
            records.append(payload)
        else:
            raw_events.append({"line_number": line_number, "raw_payload": payload})
    return ParsedTradeArtifact(
        source_file=str(artifact),
        artifact_type="jsonl",
        records=records,
        raw_events=raw_events,
        warnings=sorted(set(warnings)),
        unsafe_evidence=sorted(set(unsafe)),
    )


def parse_log_artifact(path: str | Path) -> ParsedTradeArtifact:
    artifact = Path(path)
    records: list[dict[str, Any]] = []
    warnings: list[str] = []
    errors: list[str] = []
    unsafe: list[str] = []
    raw_events: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        artifact.read_text(encoding="utf-8", errors="replace").splitlines(),
        start=1,
    ):
        lowered = line.lower()
        if any(pattern in lowered for pattern in LIVE_DANGER_PATTERNS):
            unsafe.append(f"LIVE_DANGER_LINE:{line_number}")
        if "warning" in lowered or " warn " in f" {lowered} ":
            warnings.append(f"WARNING_LINE:{line_number}")
        if "error" in lowered or "critical" in lowered:
            errors.append(f"ERROR_LINE:{line_number}")
        pair_match = PAIR_PATTERN.search(line)
        trade_like = pair_match and any(
            token in lowered for token in ["buy", "sell", "entry", "exit", "trade", "profit"]
        )
        raw_payload: dict[str, Any] = {"line_number": line_number, "raw": line}
        if pair_match:
            raw_payload["pair"] = pair_match.group(1)
        if trade_like:
            raw_payload["source_record_id"] = f"log-{line_number}"
            raw_payload["status"] = "log_observed"
            raw_payload["dry_run"] = "dry-run" in lowered or "dry_run" in lowered
            records.append(raw_payload)
        else:
            raw_events.append(raw_payload)
    return ParsedTradeArtifact(
        source_file=str(artifact),
        artifact_type="log",
        records=records,
        raw_events=raw_events,
        warnings=warnings,
        errors=errors,
        unsafe_evidence=unsafe,
    )


def parse_sqlite_artifact(path: str | Path) -> ParsedTradeArtifact:
    artifact = Path(path)
    warnings: list[str] = []
    try:
        uri = f"file:{artifact.as_posix()}?mode=ro"
        connection = sqlite3.connect(uri, uri=True)
    except sqlite3.Error as exc:
        return ParsedTradeArtifact(
            source_file=str(artifact),
            artifact_type="sqlite",
            warnings=[f"SQLITE_OPEN_FAILED:{exc}"],
        )
    try:
        tables = [
            row[0]
            for row in connection.execute(
                "select name from sqlite_master where type='table'"
            ).fetchall()
        ]
        if "trades" not in tables:
            return ParsedTradeArtifact(
                source_file=str(artifact),
                artifact_type="sqlite",
                warnings=["SQLITE_TRADES_TABLE_MISSING"],
                raw_events=[{"tables": tables}],
            )
        cursor = connection.execute("select * from trades")
        columns = [description[0] for description in cursor.description or []]
        records = [dict(zip(columns, row, strict=False)) for row in cursor.fetchall()]
        unsafe: list[str] = []
        for record in records:
            unsafe.extend(detect_unsafe_evidence(record))
        return ParsedTradeArtifact(
            source_file=str(artifact),
            artifact_type="sqlite",
            records=records,
            raw_events=[{"tables": tables, "columns": columns}],
            warnings=warnings,
            unsafe_evidence=sorted(set(unsafe)),
        )
    except sqlite3.Error as exc:
        return ParsedTradeArtifact(
            source_file=str(artifact),
            artifact_type="sqlite",
            warnings=[f"SQLITE_READ_FAILED:{exc}"],
        )
    finally:
        connection.close()


def detect_unsafe_evidence(payload: Any) -> list[str]:
    evidence: list[str] = []
    text = json.dumps(payload, sort_keys=True, default=str).lower()
    for pattern in LIVE_DANGER_PATTERNS:
        if pattern in text:
            evidence.append(f"LIVE_DANGER:{pattern}")
    _walk_for_unsafe(payload, "", evidence)
    return sorted(set(evidence))


def _extract_records(payload: Any) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)], warnings
    if isinstance(payload, dict):
        for key in ["trades", "data"]:
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)], warnings
        if _looks_like_trade(payload):
            return [payload], warnings
        warnings.append("UNKNOWN_JSON_SHAPE")
        return [], warnings
    warnings.append("UNKNOWN_JSON_SHAPE")
    return [], warnings


def _looks_like_trade(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    keys = set(payload.keys())
    if "exchange" in keys and "pair_whitelist" not in keys:
        return False
    identity_keys = {"pair", "symbol", "trade_id", "id"}
    trade_detail_keys = {
        "open_date",
        "open_timestamp",
        "close_date",
        "close_timestamp",
        "open_rate",
        "close_rate",
        "profit_abs",
        "profit_ratio",
        "exit_reason",
        "is_open",
    }
    return bool(identity_keys & keys) and bool(trade_detail_keys & keys)


def _walk_for_unsafe(payload: Any, prefix: str, evidence: list[str]) -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            lowered = str(key).lower()
            path = f"{prefix}.{lowered}" if prefix else lowered
            if lowered in SECRET_FIELD_NAMES and str(value or "").strip():
                evidence.append(f"CREDENTIAL_FIELD:{path}")
            if lowered == "dry_run" and value is False:
                evidence.append("DRY_RUN_FALSE")
            if lowered in {"live_trading_allowed", "live_trading_enabled"} and value is True:
                evidence.append(f"LIVE_FLAG_TRUE:{path}")
            if lowered in UNSAFE_MODE_FIELDS and value is True:
                evidence.append(f"UNSAFE_MODE_TRUE:{path}")
            if lowered in {"leverage"} and _safe_float(value) and float(value) > 1:
                evidence.append(f"LEVERAGE_ABOVE_ONE:{path}")
            _walk_for_unsafe(value, path, evidence)
    elif isinstance(payload, list):
        for index, item in enumerate(payload):
            _walk_for_unsafe(item, f"{prefix}[{index}]", evidence)


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _classify(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return "json"
    if suffix == ".jsonl":
        return "jsonl"
    if suffix in {".log", ".txt"}:
        return "log"
    if suffix in {".sqlite", ".db"}:
        return "sqlite"
    return "unknown"
