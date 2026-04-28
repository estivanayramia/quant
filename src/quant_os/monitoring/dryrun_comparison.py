from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quant_os.data.loaders import load_yaml
from quant_os.integrations.freqtrade.safety import FreqtradeSafetyError, validate_freqtrade_config
from quant_os.monitoring.dryrun_history import (
    DRYRUN_ROOT,
    GENERATED_CONFIG,
    GENERATED_STRATEGY,
    LATEST_LOGS,
    LATEST_OPERATIONAL_STATUS,
    LATEST_RECONCILIATION,
    ensure_dryrun_monitoring_dirs,
    load_history_records,
)
from quant_os.monitoring.freshness import dryrun_freshness_summary

LATEST_TRADE_RECONCILIATION = Path("reports/freqtrade/trades/latest_trade_reconciliation.json")


def build_dryrun_comparison(write: bool = True) -> dict[str, Any]:
    ensure_dryrun_monitoring_dirs()
    checks: list[dict[str, Any]] = []

    def add(name: str, status: str, details: dict[str, Any] | None = None) -> None:
        checks.append({"name": name, "status": status, "details": details or {}})

    expected = _load_yaml_or_empty("configs/freqtrade.yaml")
    risk = _load_yaml_or_empty("configs/risk_limits.yaml")
    generated = _read_json(GENERATED_CONFIG)
    logs = _read_json(LATEST_LOGS) or {}
    operational = _read_json(LATEST_OPERATIONAL_STATUS) or {}
    reconciliation = _read_json(LATEST_RECONCILIATION) or {}

    if generated is None:
        add("config_present", "FAIL", {"path": str(GENERATED_CONFIG)})
    else:
        add("config_present", "PASS", {"path": str(GENERATED_CONFIG)})
        _compare_config(expected, generated, risk, add)
        _compare_hash_stability(add)

    _compare_strategy(add)
    _compare_logs(logs, add)
    _compare_operational(operational, add)
    _compare_reconciliation(reconciliation, add)
    _compare_trade_level(add)

    status = _aggregate_status(checks)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": status,
        "checks": checks,
        "freshness": dryrun_freshness_summary(),
        "dry_run_only": True,
        "live_trading_enabled": False,
        "unsafe_failures": [check for check in checks if check["status"] == "FAIL"],
        "warnings": [check for check in checks if check["status"] in {"WARN", "UNAVAILABLE"}],
    }
    if write:
        (DRYRUN_ROOT / "latest_comparison.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
        )
    return payload


def _compare_config(
    expected: dict[str, Any], generated: dict[str, Any], risk: dict[str, Any], add
) -> None:
    try:
        validate_freqtrade_config(GENERATED_CONFIG)
        add("freqtrade_safety_guard", "PASS")
    except FreqtradeSafetyError as exc:
        add("freqtrade_safety_guard", "FAIL", {"reasons": str(exc).split(";")})
    add("dry_run_true", "PASS" if generated.get("dry_run") is True else "FAIL")
    add(
        "live_trading_disabled",
        "PASS" if generated.get("live_trading_allowed") is False else "FAIL",
    )
    add("trading_mode_spot", "PASS" if generated.get("trading_mode") == "spot" else "FAIL")
    add("no_margin", "PASS" if generated.get("margin_mode") in {"", None} else "FAIL")
    add("no_futures", "PASS" if generated.get("futures") is not True else "FAIL")
    add("no_shorting", "PASS" if generated.get("shorting") is not True else "FAIL")
    add("no_leverage", "PASS" if float(generated.get("leverage", 1) or 1) <= 1 else "FAIL")
    exchange = generated.get("exchange", {})
    expected_pairs = sorted(expected.get("pairs") or ["BTC/USDT", "ETH/USDT"])
    actual_pairs = sorted(exchange.get("pair_whitelist", []) if isinstance(exchange, dict) else [])
    add(
        "pair_universe_alignment",
        "PASS" if expected_pairs == actual_pairs else "WARN",
        {"expected": expected_pairs, "actual": actual_pairs},
    )
    for key in ["timeframe", "max_open_trades", "stake_amount"]:
        expected_value = expected.get(key)
        actual_value = generated.get(key)
        add(
            f"{key}_alignment",
            "PASS" if str(expected_value) == str(actual_value) else "WARN",
            {"expected": expected_value, "actual": actual_value},
        )
    add(
        "strategy_name_alignment",
        "PASS" if generated.get("strategy") == expected.get("strategy_name") else "WARN",
        {"expected": expected.get("strategy_name"), "actual": generated.get("strategy")},
    )
    add(
        "max_open_trades_vs_risk",
        "PASS"
        if int(generated.get("max_open_trades", 999)) <= int(risk.get("max_open_positions", 1))
        else "FAIL",
    )
    add(
        "stake_amount_vs_risk",
        "PASS"
        if float(generated.get("stake_amount", 999999)) <= float(risk.get("max_order_notional", 25))
        else "FAIL",
    )


def _compare_strategy(add) -> None:
    if not GENERATED_STRATEGY.exists():
        add("strategy_present", "FAIL", {"path": str(GENERATED_STRATEGY)})
        return
    text = GENERATED_STRATEGY.read_text(encoding="utf-8", errors="replace")
    add("strategy_present", "PASS", {"path": str(GENERATED_STRATEGY)})
    add(
        "strategy_dry_run_warning_label",
        "PASS" if "Dry-run research only" in text else "FAIL",
    )
    forbidden = ["openai", "requests.", "ccxt", "alpaca", "create_order", "dry_run = false"]
    matches = [term for term in forbidden if term.lower() in text.lower()]
    add(
        "strategy_no_external_execution_calls",
        "PASS" if not matches else "FAIL",
        {"matches": matches},
    )
    manifest = _read_json(Path("reports/freqtrade/latest_manifest.json")) or {}
    expected_hash = manifest.get("strategy_sha256")
    actual_hash = _sha256(GENERATED_STRATEGY)
    if expected_hash and actual_hash:
        add(
            "strategy_hash_matches_manifest",
            "PASS" if expected_hash == actual_hash else "FAIL",
            {"expected": expected_hash, "actual": actual_hash},
        )
    else:
        add("strategy_hash_manifest_available", "WARN", {"actual": actual_hash})


def _compare_hash_stability(add) -> None:
    current_hash = _sha256(GENERATED_CONFIG)
    previous_hashes = [
        record.get("config_hash") for record in load_history_records() if record.get("config_hash")
    ]
    if previous_hashes and current_hash != previous_hashes[-1]:
        add(
            "config_hash_stability",
            "WARN",
            {"previous": previous_hashes[-1], "current": current_hash},
        )
    else:
        add("config_hash_stability", "PASS", {"current": current_hash})


def _compare_logs(logs: dict[str, Any], add) -> None:
    if not logs:
        add("logs_available", "WARN", {"reason": "No Freqtrade dry-run logs have been ingested."})
        return
    danger_matches = _danger_matches(json.dumps(logs).lower())
    add(
        "logs_no_live_mode_danger",
        "PASS" if not danger_matches else "FAIL",
        {"matches": danger_matches},
    )
    add("logs_warning_count", "PASS" if int(logs.get("warnings", 0) or 0) == 0 else "WARN")
    add("logs_error_count", "PASS" if int(logs.get("errors", 0) or 0) == 0 else "WARN")
    if not logs.get("pairs"):
        add("logs_pairs_detectable", "WARN")
    else:
        add("logs_pairs_detectable", "PASS", {"pairs": logs.get("pairs")})


def _compare_operational(operational: dict[str, Any], add) -> None:
    if not operational:
        add("operational_status_available", "WARN")
        return
    add("operational_status_available", "PASS")
    if operational.get("container_status") in {"UNAVAILABLE", "UNKNOWN"}:
        add("container_status", "WARN", {"container_status": operational.get("container_status")})
    else:
        add("container_status", "PASS", {"container_status": operational.get("container_status")})


def _compare_reconciliation(reconciliation: dict[str, Any], add) -> None:
    if not reconciliation:
        add("freqtrade_reconciliation_available", "WARN")
        return
    status = reconciliation.get("status")
    add(
        "freqtrade_reconciliation_status",
        "FAIL" if status == "FAIL" else "WARN" if status in {"WARN", "UNAVAILABLE"} else "PASS",
        {"status": status},
    )


def _compare_trade_level(add) -> None:
    trade_reconciliation = _read_json(LATEST_TRADE_RECONCILIATION)
    if not trade_reconciliation:
        add(
            "trade_level_comparison",
            "UNAVAILABLE",
            {"reason": "No Phase 6 trade-level reconciliation report exists yet."},
        )
        return
    status = trade_reconciliation.get("status")
    add(
        "trade_level_comparison",
        "FAIL" if status == "FAIL" else "WARN" if status in {"WARN", "UNAVAILABLE"} else "PASS",
        {
            "status": status,
            "available": trade_reconciliation.get("trade_level_comparison_available", False),
            "report": str(LATEST_TRADE_RECONCILIATION),
        },
    )


def _aggregate_status(checks: list[dict[str, Any]]) -> str:
    statuses = {check["status"] for check in checks}
    if "FAIL" in statuses:
        return "FAIL"
    if statuses & {"WARN", "UNAVAILABLE"}:
        return "WARN"
    return "PASS"


def _danger_matches(text: str) -> list[str]:
    patterns = [
        "dry_run false",
        "dry-run false",
        '"dry_run": false',
        "live mode",
        "live trading enabled",
        "real order",
        "placing live",
    ]
    return [pattern for pattern in patterns if pattern in text]


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _load_yaml_or_empty(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        return {}
    return load_yaml(config_path)


def _sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()
