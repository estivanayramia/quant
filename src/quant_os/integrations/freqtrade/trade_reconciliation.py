from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quant_os.adapters.event_store_jsonl import JsonlEventStore
from quant_os.data.loaders import load_yaml
from quant_os.integrations.freqtrade.safety import FreqtradeSafetyError, validate_freqtrade_config
from quant_os.integrations.freqtrade.trade_artifacts import (
    DryRunTradeRecord,
    ensure_trade_report_dir,
    write_json_report,
)
from quant_os.integrations.freqtrade.trade_normalizer import normalize_trade_artifacts


def reconcile_freqtrade_trades(
    records: list[DryRunTradeRecord | dict[str, Any]] | None = None,
    *,
    expected_records: list[dict[str, Any]] | None = None,
    event_store: JsonlEventStore | None = None,
    write: bool = True,
) -> dict[str, Any]:
    config = _artifact_config()
    normalized_payload: dict[str, Any] | None = None
    if records is None:
        normalized_payload = normalize_trade_artifacts(write=True)
        records = normalized_payload.get("records", [])
    trade_records = [
        item if isinstance(item, DryRunTradeRecord) else DryRunTradeRecord.model_validate(item)
        for item in records
    ]
    expected = (
        expected_records if expected_records is not None else _load_expected_records(event_store)
    )
    failures: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    matches: list[dict[str, Any]] = []
    unmatched_freqtrade: list[dict[str, Any]] = []
    unmatched_quantos = list(expected)

    _run_core_safety_checks(failures)
    if normalized_payload:
        for evidence in normalized_payload.get("unsafe_evidence", []):
            failures.append({"reason": "UNSAFE_ARTIFACT_EVIDENCE", "details": evidence})

    if not trade_records:
        warnings.append({"reason": "NO_FREQTRADE_TRADE_LEVEL_DATA"})
    if not expected:
        warnings.append({"reason": "NO_QUANTOS_EXPECTED_TRADE_LEVEL_DATA"})

    for record in trade_records:
        match = _find_match(record, unmatched_quantos, config)
        if match is None:
            unmatched_freqtrade.append(record.model_dump(mode="json"))
        else:
            unmatched_quantos.remove(match)
            mismatches = _compare_record(record, match, config)
            if mismatches:
                warnings.append(
                    {
                        "reason": "TRADE_FIELD_MISMATCH",
                        "record_id": record.record_id,
                        "mismatches": mismatches,
                    }
                )
            matches.append({"freqtrade_record_id": record.record_id, "quantos_record": match})

    if unmatched_freqtrade:
        warnings.append(
            {"reason": "UNMATCHED_FREQTRADE_RECORDS", "count": len(unmatched_freqtrade)}
        )
    if unmatched_quantos:
        warnings.append(
            {"reason": "UNMATCHED_QUANTOS_EXPECTED_RECORDS", "count": len(unmatched_quantos)}
        )

    unavailable = not trade_records and not expected and not failures
    status = (
        "FAIL" if failures else "UNAVAILABLE" if unavailable else "WARN" if warnings else "PASS"
    )
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": status,
        "dry_run_only": True,
        "live_trading_enabled": False,
        "trade_level_comparison_available": bool(trade_records and expected),
        "freqtrade_records_count": len(trade_records),
        "quantos_expected_records_count": len(expected),
        "matched_records_count": len(matches),
        "unmatched_freqtrade_records": unmatched_freqtrade,
        "unmatched_quantos_expected_records": unmatched_quantos,
        "matches": matches,
        "failures": failures,
        "warnings": warnings,
        "normalized_records_path": "reports/freqtrade/trades/latest_trades_normalized.json",
    }
    if write:
        _write_reconciliation_reports(payload)
    return payload


def _run_core_safety_checks(failures: list[dict[str, Any]]) -> None:
    config_path = Path("freqtrade/user_data/config/config.dry-run.generated.json")
    if not config_path.exists():
        return
    try:
        validate_freqtrade_config(config_path)
    except FreqtradeSafetyError as exc:
        failures.append({"reason": "FREQTRADE_SAFETY_GUARD_FAILED", "details": str(exc)})


def _load_expected_records(event_store: JsonlEventStore | None) -> list[dict[str, Any]]:
    event_store = event_store or JsonlEventStore("data/events/events.jsonl")
    if not Path(event_store.path).exists():
        return []
    expected: list[dict[str, Any]] = []
    for event in event_store.read_all():
        if str(event.event_type) == "ORDER_FILLED":
            fill = event.payload.get("fill", {})
            if isinstance(fill, dict):
                expected.append(
                    {
                        "source": "quantos_event_ledger",
                        "symbol": fill.get("symbol"),
                        "side": fill.get("side"),
                        "quantity": fill.get("quantity"),
                        "price": fill.get("price"),
                        "timestamp": fill.get("filled_at") or str(event.timestamp),
                        "strategy_name": fill.get("strategy_id"),
                    }
                )
    return expected


def _find_match(
    record: DryRunTradeRecord,
    expected: list[dict[str, Any]],
    config: dict[str, Any],
) -> dict[str, Any] | None:
    for item in expected:
        if _symbols_align(record.symbol, item.get("symbol")) and _side_align(
            record.side, item.get("side")
        ):
            return item
    return None


def _compare_record(
    record: DryRunTradeRecord,
    expected: dict[str, Any],
    config: dict[str, Any],
) -> list[str]:
    mismatches: list[str] = []
    if not _symbols_align(record.symbol, expected.get("symbol")):
        mismatches.append("SYMBOL_MISMATCH")
    if not _side_align(record.side, expected.get("side")):
        mismatches.append("SIDE_MISMATCH")
    expected_notional = _as_float(expected.get("notional"))
    if expected_notional is None:
        price = _as_float(expected.get("price"))
        quantity = _as_float(expected.get("quantity"))
        expected_notional = price * quantity if price is not None and quantity is not None else None
    tolerance_pct = float(config["reconciliation"].get("notional_tolerance_pct", 20))
    if record.stake_amount is not None and expected_notional:
        diff_pct = (
            abs(record.stake_amount - expected_notional) / max(abs(expected_notional), 1) * 100
        )
        if diff_pct > tolerance_pct:
            mismatches.append("NOTIONAL_MISMATCH")
    if record.profit_abs is None:
        mismatches.append("PNL_UNAVAILABLE")
    if not record.exit_reason and not record.close_date:
        mismatches.append("EXIT_EVIDENCE_UNAVAILABLE")
    return mismatches


def _symbols_align(left: Any, right: Any) -> bool:
    if left is None or right is None:
        return False
    return str(left).replace("/", "-").upper() == str(right).replace("/", "-").upper()


def _side_align(left: Any, right: Any) -> bool:
    if left is None or right is None:
        return True
    left_value = str(left).lower()
    right_value = str(right).lower()
    if left_value == "long" and right_value == "buy":
        return True
    return left_value == right_value


def _artifact_config() -> dict[str, Any]:
    defaults = {
        "reconciliation": {
            "timestamp_tolerance_seconds": 300,
            "notional_tolerance_pct": 20,
            "pnl_tolerance_abs": 5,
        }
    }
    path = Path("configs/freqtrade_artifacts.yaml")
    if path.exists():
        loaded = load_yaml(path)
        defaults.update(loaded)
        defaults["reconciliation"] = {
            "timestamp_tolerance_seconds": 300,
            "notional_tolerance_pct": 20,
            "pnl_tolerance_abs": 5,
            **loaded.get("reconciliation", {}),
        }
    return defaults


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _write_reconciliation_reports(payload: dict[str, Any]) -> None:
    root = ensure_trade_report_dir()
    write_json_report(root / "latest_trade_reconciliation.json", payload)
    lines = [
        "# Freqtrade Trade-Level Reconciliation",
        "",
        "Dry-run only. No live trading. No real-money trading.",
        "",
        f"Status: {payload['status']}",
        f"Freqtrade records: {payload['freqtrade_records_count']}",
        f"QuantOS expected records: {payload['quantos_expected_records_count']}",
        f"Matched records: {payload['matched_records_count']}",
        "",
        "## Failures",
    ]
    failures = payload.get("failures") or ["None"]
    lines.extend(f"- {failure}" for failure in failures)
    lines.extend(["", "## Warnings"])
    warnings = payload.get("warnings") or ["None"]
    lines.extend(f"- {warning}" for warning in warnings)
    lines.extend(
        [
            "",
            "Live promotion remains blocked. Missing or partial trade-level evidence is not treated as proof of readiness.",
        ]
    )
    (root / "latest_trade_reconciliation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
