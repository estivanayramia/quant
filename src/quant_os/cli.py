from __future__ import annotations

from pathlib import Path

import typer
from rich import print

from quant_os.adapters.event_store_jsonl import JsonlEventStore
from quant_os.adapters.market_data_parquet import LocalParquetMarketData
from quant_os.autonomy.daemon import daemon_status, run_daemon, stop_daemon
from quant_os.autonomy.supervisor import Supervisor
from quant_os.autonomy.tasks import run_drift_checks
from quant_os.core.commands import CandidateOrder
from quant_os.core.events import EventType, make_event
from quant_os.data.demo_data import seed_demo_data
from quant_os.data.loaders import load_yaml
from quant_os.data.quality import validate_ohlcv
from quant_os.data.warehouse import ensure_local_dirs
from quant_os.domain.strategy import StrategyRecord
from quant_os.governance.registry import StrategyRegistry
from quant_os.integrations.freqtrade.config_writer import write_freqtrade_dry_run_config
from quant_os.integrations.freqtrade.dry_run_adapter import FreqtradeDryRunAdapter
from quant_os.integrations.freqtrade.strategy_exporter import export_quant_os_strategy
from quant_os.integrations.telegram.alert_adapter import TelegramAlertAdapter
from quant_os.ops.freqtrade_reporting import write_freqtrade_status_report
from quant_os.ops.reporting import generate_daily_report
from quant_os.projections.rebuild import rebuild_read_models as rebuild_read_models_projection
from quant_os.research.backtest import run_backtest
from quant_os.research.strategies import baseline_ma_candidates
from quant_os.research.tournament import run_tournament
from quant_os.risk.firewall import RiskFirewall
from quant_os.risk.limits import RiskLimits
from quant_os.security.live_trading_guard import live_trading_guard
from quant_os.watchdog.health_checks import run_watchdog

app = typer.Typer(help="Local deterministic QuantOps simulation foundation.")
autonomous_app = typer.Typer(help="Autonomous safe-mode runbooks.")
strategy_app = typer.Typer(help="Strategy governance commands.")
freqtrade_app = typer.Typer(help="Freqtrade dry-run-only commands.")
app.add_typer(autonomous_app, name="autonomous")
app.add_typer(strategy_app, name="strategy")
app.add_typer(freqtrade_app, name="freqtrade")


def _event_store() -> JsonlEventStore:
    return JsonlEventStore("data/events/events.jsonl")


def _load_symbol(symbol: str = "SPY"):
    path = Path("data/demo") / f"{symbol}.parquet"
    if not path.exists():
        seed_demo_data(event_store=_event_store())
    return LocalParquetMarketData().load(symbol)


@app.command()
def seed_demo() -> None:
    ensure_local_dirs()
    summary = seed_demo_data(event_store=_event_store())
    print({"seeded": summary})


@app.command()
def validate_data() -> None:
    frame = LocalParquetMarketData().load()
    summary = validate_ohlcv(frame)
    print({"validated": summary})


@app.command()
def backtest(symbol: str = "SPY", strategy: str = "baseline_ma") -> None:
    frame = _load_symbol(symbol)
    result = run_backtest(frame, strategy=strategy, event_store=_event_store())
    print({"strategy": result.strategy_id, "metrics": result.metrics})


@app.command()
def tournament(symbol: str = "SPY") -> None:
    frame = _load_symbol(symbol)
    summary = run_tournament(frame, _event_store())
    print(summary)


@app.command()
def shadow(symbol: str = "SPY", execute_simulation: bool = False) -> None:
    frame = _load_symbol(symbol)
    candidates = baseline_ma_candidates(frame, strategy_id="shadow_baseline")[:5]
    event_store = _event_store()
    risk = RiskFirewall(RiskLimits.from_yaml(), event_store)
    from quant_os.execution.engine import ExecutionEngine

    engine = ExecutionEngine(event_store, risk)
    decisions = []
    for candidate in candidates:
        candidate = CandidateOrder.model_validate(candidate.model_dump())
        result = engine.process_candidate(candidate, execute=execute_simulation)
        decisions.append(
            {
                "client_order_id": result.order.client_order_id,
                "approved": result.decision.approved,
                "reasons": result.decision.reasons,
                "filled": result.fill is not None,
            }
        )
    print({"shadow_decisions": decisions, "simulation_fills_enabled": execute_simulation})


@app.command()
def rebuild_read_models() -> None:
    path = rebuild_read_models_fn()
    print({"read_models": str(path)})


def rebuild_read_models_fn() -> Path:
    return rebuild_read_models_projection(_event_store())


@app.command()
def report() -> None:
    payload = generate_daily_report(_event_store())
    print({"report": "reports/daily_report.md", "summary_keys": sorted(payload.keys())})


@app.command("guard-live")
def guard_live() -> None:
    result = live_trading_guard()
    if not result.passed:
        print({"passed": False, "reasons": result.reasons})
        raise typer.Exit(1)
    print({"passed": True, "guard": "live_trading_guard"})


@app.command("watchdog")
def watchdog_command() -> None:
    store = _event_store()
    report_payload = run_watchdog(store)
    store.append(
        make_event(
            EventType.WATCHDOG_PASSED if report_payload.passed else EventType.WATCHDOG_FAILED,
            "watchdog",
            report_payload.to_dict(),
        )
    )
    print({"watchdog": report_payload.status, "report": "reports/watchdog/latest_health.json"})
    if not report_payload.passed:
        raise typer.Exit(1)


@app.command("drift")
def drift_command() -> None:
    summary = run_drift_checks(_event_store())
    print({"drift": summary["status"], "report": "reports/drift/latest_drift.json"})


@app.command("alerts-test")
def alerts_test() -> None:
    adapter = TelegramAlertAdapter(enabled=False)
    adapter.send_summary("Quant OS mock alert test. Alerts only; no trading authority.")
    print({"provider": "mock_telegram", "messages": adapter.sent_messages})


@app.command("freqtrade-config")
def freqtrade_config() -> None:
    path = write_freqtrade_dry_run_config()
    print({"freqtrade_config": str(path), "dry_run": True, "live_trading_allowed": False})


@freqtrade_app.command("generate-config")
def freqtrade_generate_config() -> None:
    path = FreqtradeDryRunAdapter().generate_config()
    print({"freqtrade_config": str(path), "dry_run": True, "live_trading_allowed": False})


@freqtrade_app.command("validate")
def freqtrade_validate() -> None:
    result = FreqtradeDryRunAdapter().validate_config()
    print({"passed": result.passed, "config_path": result.config_path, "reasons": result.reasons})


@freqtrade_app.command("export-strategy")
def freqtrade_export_strategy() -> None:
    path = export_quant_os_strategy()
    print({"strategy_path": str(path), "dry_run_research_only": True})


@freqtrade_app.command("status")
def freqtrade_status() -> None:
    status = write_freqtrade_status_report()
    print({"status": status, "report": "reports/freqtrade/latest_status.json"})


@freqtrade_app.command("command-preview")
def freqtrade_command_preview() -> None:
    print({"docker_command_preview": FreqtradeDryRunAdapter().build_docker_command()})


@freqtrade_app.command("manifest")
def freqtrade_manifest() -> None:
    adapter = FreqtradeDryRunAdapter()
    path = adapter.write_run_manifest()
    print({"manifest": str(path), "live_trading_enabled": False})


@freqtrade_app.command("dry-run-check")
def freqtrade_dry_run_check() -> None:
    adapter = FreqtradeDryRunAdapter()
    if not Path(adapter.config_path).exists():
        adapter.generate_config()
    if not Path(adapter.strategy_path).exists():
        adapter.export_strategy()
    result = adapter.validate_config()
    manifest = adapter.write_run_manifest()
    write_freqtrade_status_report()
    print(
        {
            "dry_run_ready": result.passed,
            "manifest": str(manifest),
            "live_trading_enabled": False,
        }
    )


@autonomous_app.command("run-once")
def autonomous_run_once(runbook: str = "full_safe_autonomous_cycle") -> None:
    state = Supervisor().run_once(runbook)
    print(
        {
            "run_id": state.run_id,
            "status": state.status.value,
            "report": "reports/autonomy/latest_run.json",
        }
    )
    if state.status.value != "completed":
        raise typer.Exit(1)


@autonomous_app.command("daemon")
def autonomous_daemon(
    interval_minutes: int = typer.Option(60, min=1),
    max_cycles: int | None = typer.Option(None),
) -> None:
    result = run_daemon(interval_minutes=interval_minutes, max_cycles=max_cycles)
    print(result.__dict__)


@autonomous_app.command("status")
def autonomous_status() -> None:
    print(daemon_status())


@autonomous_app.command("stop")
def autonomous_stop() -> None:
    print(stop_daemon())


@strategy_app.command("list")
def strategy_list() -> None:
    registry = _strategy_registry()
    print({"strategies": [record.model_dump(mode="json") for record in registry.records.values()]})


@strategy_app.command("quarantine")
def strategy_quarantine(strategy_id: str, reason: str = typer.Option(..., "--reason")) -> None:
    registry = _strategy_registry()
    registry.quarantine(strategy_id, reason)
    print({"strategy_id": strategy_id, "status": "quarantined", "reason": reason})


@strategy_app.command("release")
def strategy_release(strategy_id: str, reason: str = typer.Option(..., "--reason")) -> None:
    registry = _strategy_registry()
    registry.release(strategy_id)
    print({"strategy_id": strategy_id, "status": "research", "reason": reason})


@strategy_app.command("status")
def strategy_status(strategy_id: str) -> None:
    registry = _strategy_registry()
    record = registry.records.get(strategy_id)
    if record is None:
        raise typer.BadParameter(f"unknown strategy {strategy_id}")
    print(record.model_dump(mode="json"))


@app.command()
def smoke() -> None:
    ensure_local_dirs()
    seed_demo()
    validate_data()
    backtest()
    tournament()
    shadow()
    rebuild_read_models()
    report()
    print("[green]smoke completed[/green]")


def _strategy_registry() -> StrategyRegistry:
    registry = StrategyRegistry(_event_store())
    config = load_yaml("configs/strategies.yaml")
    for strategy_id, raw in (config.get("strategies") or {}).items():
        registry.register(
            StrategyRecord(
                strategy_id=strategy_id,
                name=strategy_id,
                enabled=bool(raw.get("enabled", True)),
                quarantined=bool(raw.get("quarantined", False)),
                notes=str(raw.get("description", "")),
            )
        )
    for event in _event_store().read_all():
        if event.event_type == EventType.STRATEGY_QUARANTINED:
            strategy_id = str(event.payload.get("strategy_id", event.aggregate_id))
            if strategy_id in registry.records:
                registry.records[strategy_id].quarantined = True
                registry.records[strategy_id].status = "quarantined"
        if event.event_type == EventType.STRATEGY_RELEASED:
            strategy_id = str(event.payload.get("strategy_id", event.aggregate_id))
            if strategy_id in registry.records:
                registry.records[strategy_id].quarantined = False
                registry.records[strategy_id].status = "research"
    return registry


if __name__ == "__main__":
    app()
