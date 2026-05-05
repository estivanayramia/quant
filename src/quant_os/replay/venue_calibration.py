from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from quant_os.data.loaders import load_yaml
from quant_os.data.normalization import normalize_symbol

REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = Path("configs/venue_calibration.yaml")
DEFAULT_VENUE_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "venue" / "binance_public_snapshot.json"
REPORT_ROOT = Path("reports/sequence18/venue_calibration")


def run_venue_calibration(
    *,
    fixture_path: str | Path | None = None,
    output_root: str | Path = ".",
    config_path: str | Path = CONFIG_PATH,
    allow_network_fetch: bool | None = None,
    explicit_network_fetch: bool = False,
) -> dict[str, Any]:
    config = _load_config(config_path)
    requested_network = (
        bool(config.get("allow_network_fetch", False))
        if allow_network_fetch is None
        else bool(allow_network_fetch)
    )
    network_explicitly_requested = bool(requested_network and explicit_network_fetch)
    network_allowed = False
    path = Path(fixture_path or config.get("fixture_path") or DEFAULT_VENUE_FIXTURE)
    if not path.is_absolute():
        path = Path(output_root) / path
        if not path.exists():
            path = REPO_ROOT / str(fixture_path or config.get("fixture_path") or DEFAULT_VENUE_FIXTURE)

    blockers: list[str] = []
    if requested_network and not explicit_network_fetch:
        blockers.append("NETWORK_FETCH_REQUIRES_EXPLICIT_FLAG")
    if network_explicitly_requested:
        blockers.append("NETWORK_FETCH_PROHIBITED_OFFLINE_FIRST")

    is_fixture = "tests/fixtures" in str(path).replace("\\", "/")
    source_mode = "fixture" if is_fixture else "cached_real"

    raw = _load_fixture(path)
    observed = _observed_metrics(raw)
    policy = _policy(config)
    warnings = _warnings(observed, policy)
    suggestions = _suggested_replay_parameters(observed, policy)
    status = "BLOCKED" if blockers else "WARN" if warnings else "PASS"
    payload = {
        "status": status,
        "generated_at": datetime.now(UTC).isoformat(),
        "sequence": "18",
        "source_mode": source_mode,
        "source": str(raw.get("source", "unknown")),
        "source_path": str(path),
        "source_sha256": _sha256(path),
        "venue": str(raw.get("venue") or config.get("venue") or "unknown"),
        "timeframe": str(raw.get("timeframe") or config.get("timeframe") or "unknown"),
        "symbols": observed["symbols"],
        "network_fetch_requested": requested_network,
        "network_fetch_allowed": network_allowed,
        "optional_dependencies": {"ccxt": optional_ccxt_status()},
        "observed": observed,
        "policy": policy,
        "suggested_replay_parameters": suggestions,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "live_trading_enabled": False,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def optional_ccxt_status() -> dict[str, Any]:
    return {
        "name": "ccxt",
        "installed": importlib.util.find_spec("ccxt") is not None,
        "required": False,
    }


def _load_config(config_path: str | Path) -> dict[str, Any]:
    path = Path(config_path)
    if not path.exists():
        return {}
    return load_yaml(path)


def _load_fixture(path: Path) -> dict[str, Any]:
    if not path.exists():
        msg = f"venue calibration fixture not found: {path}"
        raise FileNotFoundError(msg)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = "venue calibration fixture must contain a JSON object"
        raise ValueError(msg)
    return payload


def _observed_metrics(payload: dict[str, Any]) -> dict[str, Any]:
    captured_at = pd.Timestamp(payload.get("captured_at") or datetime.now(UTC))
    if captured_at.tzinfo is None:
        captured_at = captured_at.tz_localize("UTC")
    symbol_payloads = payload.get("symbols") or {}
    spreads: list[float] = []
    top_of_book: list[float] = []
    quote_ages: list[float] = []
    missing_intervals = 0
    candle_count = 0
    symbols: list[str] = []
    for raw_symbol, item in sorted(symbol_payloads.items()):
        symbol = normalize_symbol(raw_symbol)
        symbols.append(symbol)
        book = item.get("book_ticker") or {}
        bid = _float(book, "bidPrice")
        ask = _float(book, "askPrice")
        bid_qty = _float(book, "bidQty")
        ask_qty = _float(book, "askQty")
        if bid > 0 and ask > 0 and ask > bid:
            mid = (bid + ask) / 2.0
            spreads.append(((ask - bid) / mid) * 10_000.0)
            top_of_book.append(min(bid * bid_qty, ask * ask_qty))
        received_at = book.get("received_at")
        if received_at:
            quote_ages.append(abs((pd.Timestamp(received_at) - captured_at).total_seconds() * 1000.0))
        klines = item.get("klines") or []
        candle_count += len(klines)
        missing_intervals += _missing_interval_count(klines)
    spread_series = pd.Series(spreads, dtype="float64")
    top_series = pd.Series(top_of_book, dtype="float64")
    quote_series = pd.Series(quote_ages, dtype="float64")
    return {
        "symbols": symbols,
        "symbol_count": len(symbols),
        "candle_count": candle_count,
        "average_spread_bps": _series_mean(spread_series),
        "max_spread_bps": _series_max(spread_series),
        "min_top_of_book_notional": _series_min(top_series),
        "median_top_of_book_notional": _series_median(top_series),
        "max_quote_age_ms": _series_max(quote_series),
        "missing_interval_count": int(missing_intervals),
    }


def _missing_interval_count(klines: list[Any]) -> int:
    if len(klines) < 2:
        return 0
    timestamps = sorted(int(item[0]) for item in klines)
    expected_ms = 60_000
    missing = 0
    for earlier, later in zip(timestamps, timestamps[1:], strict=False):
        gap = later - earlier
        if gap > expected_ms:
            missing += int(gap / expected_ms) - 1
    return missing


def _policy(config: dict[str, Any]) -> dict[str, float]:
    raw = config.get("policy") or {}
    return {
        "fee_bps_floor": float(raw.get("fee_bps_floor", 5.0)),
        "slippage_bps_floor": float(raw.get("slippage_bps_floor", 3.0)),
        "spread_buffer_multiplier": float(raw.get("spread_buffer_multiplier", 1.5)),
        "min_liquidity_score": float(raw.get("min_liquidity_score", 0.35)),
        "min_top_of_book_notional": float(raw.get("min_top_of_book_notional", 25_000.0)),
        "max_quote_age_ms": float(raw.get("max_quote_age_ms", 1_000.0)),
        "max_spread_bps": float(raw.get("max_spread_bps", 12.0)),
    }


def _warnings(observed: dict[str, Any], policy: dict[str, float]) -> list[str]:
    warnings: list[str] = []
    if float(observed["max_quote_age_ms"]) > policy["max_quote_age_ms"]:
        warnings.append("STALE_BOOK_OBSERVED")
    if float(observed["max_spread_bps"]) > policy["max_spread_bps"]:
        warnings.append("WIDE_SPREAD_OBSERVED")
    if float(observed["min_top_of_book_notional"]) < policy["min_top_of_book_notional"]:
        warnings.append("THIN_TOP_OF_BOOK_OBSERVED")
    if int(observed["missing_interval_count"]) > 0:
        warnings.append("MISSING_INTERVALS_OBSERVED")
    return warnings


def _suggested_replay_parameters(
    observed: dict[str, Any],
    policy: dict[str, float],
) -> dict[str, float]:
    max_spread = float(observed["max_spread_bps"])
    observed_top = float(observed["min_top_of_book_notional"])
    return {
        "fee_bps": policy["fee_bps_floor"],
        "slippage_bps": max(
            policy["slippage_bps_floor"],
            max_spread * policy["spread_buffer_multiplier"],
        ),
        "max_spread_bps": max(policy["max_spread_bps"], max_spread * policy["spread_buffer_multiplier"]),
        "min_liquidity_score": policy["min_liquidity_score"],
        "min_top_of_book_notional": max(policy["min_top_of_book_notional"], observed_top),
        "max_quote_age_ms": policy["max_quote_age_ms"],
    }


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_venue_calibration.json"
    md_path = root / "latest_venue_calibration.md"
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    lines = [
        "# Sequence 3A Venue Calibration",
        "",
        "Research evidence only. No live trading.",
        "",
        f"Status: {payload['status']}",
        f"Venue: {payload['venue']}",
        f"Symbols: {', '.join(payload['symbols'])}",
        f"Network fetch allowed: {payload['network_fetch_allowed']}",
        f"Live promotion: {payload['live_promotion_status']}",
        "",
        "## Suggested Replay Parameters",
    ]
    for key, value in payload["suggested_replay_parameters"].items():
        lines.append(f"- {key}: {value:.4f}")
    lines.extend(["", "## Blockers"])
    lines.extend(f"- {item}" for item in (payload["blockers"] or ["None"]))
    lines.extend(["", "## Warnings"])
    lines.extend(f"- {item}" for item in (payload["warnings"] or ["None"]))
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def _float(row: dict[str, Any], key: str) -> float:
    value = row.get(key, 0.0)
    if value is None:
        return 0.0
    return float(value)


def _series_mean(series: pd.Series) -> float:
    return 0.0 if series.empty else float(series.mean())


def _series_max(series: pd.Series) -> float:
    return 0.0 if series.empty else float(series.max())


def _series_min(series: pd.Series) -> float:
    return 0.0 if series.empty else float(series.min())


def _series_median(series: pd.Series) -> float:
    return 0.0 if series.empty else float(series.median())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
