from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quant_os.adapters.event_store_jsonl import JsonlEventStore
from quant_os.adapters.market_data_parquet import LocalParquetMarketData
from quant_os.autonomy.freqtrade_tasks import freqtrade_safe_lane_status
from quant_os.core.commands import CandidateOrder
from quant_os.core.events import EventType, make_event
from quant_os.data.demo_data import seed_demo_data
from quant_os.data.quality import validate_ohlcv
from quant_os.drift.data_drift import detect_data_drift, signal_to_dict
from quant_os.drift.feature_drift import detect_feature_drift
from quant_os.drift.performance_drift import detect_performance_drift
from quant_os.drift.slippage_drift import detect_slippage_drift
from quant_os.execution.engine import ExecutionEngine
from quant_os.features.technical import atr_like_range, moving_average, returns, volatility
from quant_os.integrations.telegram.alert_adapter import TelegramAlertAdapter
from quant_os.ops.reporting import generate_daily_report
from quant_os.projections.rebuild import rebuild_read_models
from quant_os.research.backtest import run_backtest
from quant_os.research.strategies import baseline_ma_candidates
from quant_os.research.tournament import run_tournament
from quant_os.risk.firewall import RiskFirewall
from quant_os.risk.limits import RiskLimits
from quant_os.security.config_guard import config_guard
from quant_os.security.live_trading_guard import live_trading_guard
from quant_os.security.secrets_guard import secrets_guard
from quant_os.watchdog.health_checks import run_watchdog


def run_config_guard() -> dict[str, object]:
    result = config_guard()
    if not result.passed:
        raise RuntimeError(";".join(result.reasons))
    return {"passed": result.passed, "reasons": result.reasons, "details": result.details}


def run_secrets_guard() -> dict[str, object]:
    result = secrets_guard()
    if not result.passed:
        raise RuntimeError(";".join(result.reasons))
    return {"passed": result.passed, "reasons": result.reasons, "details": result.details}


def run_live_trading_guard() -> dict[str, object]:
    result = live_trading_guard()
    if not result.passed:
        raise RuntimeError(";".join(result.reasons))
    return {"passed": result.passed, "reasons": result.reasons, "details": result.details}


def seed_or_load_demo_data(event_store: JsonlEventStore) -> dict[str, object]:
    return seed_demo_data(event_store=event_store)


def validate_local_data() -> dict[str, object]:
    return validate_ohlcv(LocalParquetMarketData().load())


def build_features() -> dict[str, object]:
    frame = LocalParquetMarketData().load("SPY").sort_values("timestamp").copy()
    frame["returns"] = returns(frame["close"])
    frame["ma_fast"] = moving_average(frame["close"], 5)
    frame["volatility"] = volatility(frame["close"])
    frame["atr_like"] = atr_like_range(frame)
    return {
        "rows": len(frame),
        "columns": ["returns", "ma_fast", "volatility", "atr_like"],
        "latest": frame.iloc[-1][["returns", "ma_fast", "volatility", "atr_like"]].to_dict(),
    }


def run_baseline_backtest(event_store: JsonlEventStore) -> dict[str, object]:
    result = run_backtest(LocalParquetMarketData().load("SPY"), "baseline_ma", event_store)
    return result.model_dump(mode="json", exclude={"fills", "equity_curve"})


def run_placebo_backtest(event_store: JsonlEventStore) -> dict[str, object]:
    result = run_backtest(LocalParquetMarketData().load("SPY"), "placebo_random", event_store)
    return result.model_dump(mode="json", exclude={"fills", "equity_curve"})


def run_strategy_tournament(event_store: JsonlEventStore) -> dict[str, object]:
    return run_tournament(LocalParquetMarketData().load("SPY"), event_store)


def run_shadow_cycle(event_store: JsonlEventStore) -> dict[str, object]:
    frame = LocalParquetMarketData().load("SPY")
    candidates = baseline_ma_candidates(frame, strategy_id="shadow_baseline")[:5]
    engine = ExecutionEngine(event_store, RiskFirewall(RiskLimits.from_yaml(), event_store))
    decisions = []
    for candidate in candidates:
        candidate = CandidateOrder.model_validate(candidate.model_dump())
        result = engine.process_candidate(candidate, execute=False)
        decisions.append(
            {
                "client_order_id": result.order.client_order_id,
                "approved": result.decision.approved,
                "reasons": result.decision.reasons,
                "filled": result.fill is not None,
            }
        )
    return {"decisions": decisions, "simulation_fills_enabled": False}


def rebuild_models(event_store: JsonlEventStore) -> dict[str, object]:
    return {"read_model_path": str(rebuild_read_models(event_store))}


def run_drift_checks(event_store: JsonlEventStore | None = None) -> dict[str, object]:
    event_store = event_store or JsonlEventStore()
    frame = LocalParquetMarketData().load()
    signals = [
        detect_data_drift(frame),
        detect_feature_drift(frame),
        detect_performance_drift(),
        detect_slippage_drift(),
    ]
    summary = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "drift_detected" if any(signal.detected for signal in signals) else "passed",
        "signals": [signal_to_dict(signal) for signal in signals],
    }
    root = Path("reports/drift")
    root.mkdir(parents=True, exist_ok=True)
    (root / "latest_drift.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    lines = ["# Drift Report", "", f"Status: {summary['status']}", ""]
    for signal in summary["signals"]:
        lines.append(
            f"- {signal['name']}: detected={signal['detected']} details={signal['details']}"
        )
    (root / "latest_drift.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    event_type = (
        EventType.DRIFT_DETECTED
        if summary["status"] == "drift_detected"
        else EventType.DRIFT_CHECK_PASSED
    )
    event_store.append(make_event(event_type, "drift", summary))
    return summary


def run_watchdog_checks(event_store: JsonlEventStore) -> dict[str, object]:
    report = run_watchdog(event_store)
    event_store.append(
        make_event(
            EventType.WATCHDOG_PASSED if report.passed else EventType.WATCHDOG_FAILED,
            "watchdog",
            report.to_dict(),
        )
    )
    if not report.passed:
        raise RuntimeError("critical watchdog checks failed")
    return report.to_dict()


def generate_reports(event_store: JsonlEventStore) -> dict[str, object]:
    return generate_daily_report(event_store)


def send_mock_alert(message: str) -> dict[str, object]:
    adapter = TelegramAlertAdapter(enabled=False)
    adapter.send_summary(message)
    return {"provider": "mock_telegram", "messages": adapter.sent_messages}


def task_callable(name: str, event_store: JsonlEventStore) -> Callable[[], dict[str, Any]]:
    mapping: dict[str, Callable[[], dict[str, Any]]] = {
        "config_guard": run_config_guard,
        "secrets_guard": run_secrets_guard,
        "live_trading_guard": run_live_trading_guard,
        "seed_or_load_demo_data": lambda: seed_or_load_demo_data(event_store),
        "validate_data": validate_local_data,
        "build_features": build_features,
        "run_baseline_backtest": lambda: run_baseline_backtest(event_store),
        "run_placebo_backtest": lambda: run_placebo_backtest(event_store),
        "run_tournament": lambda: run_strategy_tournament(event_store),
        "run_slippage_fee_stress": lambda: {"covered_by": "run_tournament"},
        "run_shadow_mode": lambda: run_shadow_cycle(event_store),
        "rebuild_read_models": lambda: rebuild_models(event_store),
        "run_drift_checks": lambda: run_drift_checks(event_store),
        "freqtrade_safe_lane_status": freqtrade_safe_lane_status,
        "run_watchdog_health_checks": lambda: run_watchdog_checks(event_store),
        "generate_report": lambda: generate_reports(event_store),
        "send_mock_alert": lambda: send_mock_alert("Autonomous safe run completed."),
    }
    return mapping[name]
