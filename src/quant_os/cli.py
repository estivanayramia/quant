from __future__ import annotations

from pathlib import Path

import typer
from rich import print

from quant_os.adapters.event_store_jsonl import JsonlEventStore
from quant_os.adapters.market_data_parquet import LocalParquetMarketData
from quant_os.autonomy.daemon import daemon_status, run_daemon, stop_daemon
from quant_os.autonomy.proving_cycle import run_proving_once
from quant_os.autonomy.supervisor import Supervisor
from quant_os.autonomy.tasks import run_drift_checks
from quant_os.canary.arm_token import generate_arm_token
from quant_os.canary.capital_ladder import build_capital_ladder
from quant_os.canary.checklist import build_canary_checklist
from quant_os.canary.final_gate import evaluate_final_gate, write_rehearsal_report
from quant_os.canary.incident_drill import build_incident_drill
from quant_os.canary.permissions_import import import_permission_manifest
from quant_os.canary.policy import build_canary_policy
from quant_os.canary.preflight import evaluate_canary_preflight
from quant_os.canary.preflight_rehearsal import run_preflight_rehearsal
from quant_os.canary.readiness import evaluate_canary_readiness
from quant_os.canary.rehearsal import run_canary_rehearsal
from quant_os.canary.report import write_canary_report_bundle
from quant_os.canary.stoploss_proof import build_stoploss_proof
from quant_os.core.commands import CandidateOrder
from quant_os.core.events import EventType, make_event
from quant_os.data.dataset_manifest import build_dataset_manifest
from quant_os.data.dataset_quality import run_dataset_quality
from quant_os.data.dataset_splits import build_dataset_splits
from quant_os.data.demo_data import seed_demo_data
from quant_os.data.evidence_scoring import calculate_evidence_score
from quant_os.data.expanded_demo_data import seed_expanded_demo_data
from quant_os.data.historical_import import import_historical_csv
from quant_os.data.historical_manifest import build_historical_manifest
from quant_os.data.historical_normalize import normalize_latest_historical
from quant_os.data.historical_quality import run_historical_quality
from quant_os.data.leakage_checks import run_leakage_checks
from quant_os.data.loaders import load_yaml
from quant_os.data.provider_check import check_historical_providers
from quant_os.data.quality import validate_ohlcv
from quant_os.data.warehouse import ensure_local_dirs
from quant_os.domain.strategy import StrategyRecord
from quant_os.features.feature_report import write_feature_report
from quant_os.governance.registry import StrategyRegistry
from quant_os.integrations.freqtrade.artifact_scanner import scan_freqtrade_artifacts
from quant_os.integrations.freqtrade.config_writer import write_freqtrade_dry_run_config
from quant_os.integrations.freqtrade.docker_ops import DockerOps
from quant_os.integrations.freqtrade.dry_run_adapter import FreqtradeDryRunAdapter
from quant_os.integrations.freqtrade.log_ingestion import ingest_freqtrade_logs
from quant_os.integrations.freqtrade.runner import FreqtradeRunner
from quant_os.integrations.freqtrade.strategy_exporter import export_quant_os_strategy
from quant_os.integrations.freqtrade.trade_normalizer import (
    ingest_trade_artifacts,
    normalize_trade_artifacts,
)
from quant_os.integrations.freqtrade.trade_reconciliation import reconcile_freqtrade_trades
from quant_os.integrations.freqtrade.trade_reporting import write_freqtrade_trade_report
from quant_os.integrations.telegram.alert_adapter import TelegramAlertAdapter
from quant_os.monitoring.divergence import check_dryrun_divergence
from quant_os.monitoring.dryrun_comparison import build_dryrun_comparison
from quant_os.monitoring.dryrun_history import append_history_record
from quant_os.monitoring.monitoring_report import generate_dryrun_monitoring_report
from quant_os.monitoring.promotion_readiness import check_promotion_readiness
from quant_os.ops.freqtrade_reporting import (
    write_freqtrade_dry_run_report,
    write_freqtrade_status_report,
)
from quant_os.ops.reporting import generate_daily_report
from quant_os.projections.rebuild import rebuild_read_models as rebuild_read_models_projection
from quant_os.proving.incident_log import summarize_incidents
from quant_os.proving.proving_report import write_proving_report
from quant_os.proving.readiness import evaluate_proving_readiness
from quant_os.proving.run_history import load_proving_history, write_proving_status
from quant_os.research.backtest import run_backtest
from quant_os.research.historical_evidence import (
    build_historical_splits,
    calculate_historical_evidence_score,
)
from quant_os.research.historical_research_report import write_historical_research_report
from quant_os.research.leaderboard import build_strategy_leaderboard
from quant_os.research.overfit_checks import run_overfit_checks
from quant_os.research.regime_tests import run_regime_tests
from quant_os.research.research_evidence_report import write_research_evidence_report
from quant_os.research.research_report import run_strategy_research, write_strategy_research_report
from quant_os.research.strategies import baseline_ma_candidates
from quant_os.research.strategy_ablation import run_strategy_ablation
from quant_os.research.tournament import run_tournament
from quant_os.research.walk_forward import run_walk_forward_validation
from quant_os.risk.firewall import RiskFirewall
from quant_os.risk.limits import RiskLimits
from quant_os.security.live_trading_guard import live_trading_guard
from quant_os.watchdog.health_checks import run_watchdog

app = typer.Typer(help="Local deterministic QuantOps simulation foundation.")
autonomous_app = typer.Typer(help="Autonomous safe-mode runbooks.")
features_app = typer.Typer(help="Deterministic feature-building commands.")
strategy_app = typer.Typer(help="Strategy governance commands.")
freqtrade_app = typer.Typer(help="Freqtrade dry-run-only commands.")
dryrun_app = typer.Typer(help="Dry-run comparison monitoring commands.")
dataset_app = typer.Typer(help="Offline dataset evidence commands.")
evidence_app = typer.Typer(help="Research evidence report commands.")
historical_app = typer.Typer(help="Historical data ingestion commands.")
proving_app = typer.Typer(help="Autonomous proving-mode commands.")
canary_app = typer.Typer(help="Tiny-live canary policy gates. Planning only.")
app.add_typer(autonomous_app, name="autonomous")
app.add_typer(features_app, name="features")
app.add_typer(strategy_app, name="strategy")
app.add_typer(freqtrade_app, name="freqtrade")
app.add_typer(dryrun_app, name="dryrun")
app.add_typer(dataset_app, name="dataset")
app.add_typer(evidence_app, name="evidence")
app.add_typer(historical_app, name="historical")
app.add_typer(proving_app, name="proving")
app.add_typer(canary_app, name="canary")


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


@freqtrade_app.command("docker-check")
def freqtrade_docker_check() -> None:
    docker = DockerOps()
    print(
        {
            "docker_available": docker.docker_available(),
            "compose_available": docker.compose_available(),
            "required_for_ci": False,
        }
    )


@freqtrade_app.command("dry-run-start")
def freqtrade_dry_run_start() -> None:
    result = FreqtradeRunner(_event_store()).start()
    print(result.to_dict())
    if result.status == "FAIL":
        raise typer.Exit(1)


@freqtrade_app.command("dry-run-stop")
def freqtrade_dry_run_stop() -> None:
    print(FreqtradeRunner(_event_store()).stop().to_dict())


@freqtrade_app.command("dry-run-logs")
def freqtrade_dry_run_logs() -> None:
    payload = FreqtradeRunner(_event_store()).logs()
    print({"logs": "reports/freqtrade/logs/latest_logs.json", **payload})


@freqtrade_app.command("dry-run-status")
def freqtrade_dry_run_status() -> None:
    payload = FreqtradeRunner(_event_store()).status()
    print({"status": payload, "report": "reports/freqtrade/status/latest_operational_status.json"})


@freqtrade_app.command("dry-run-report")
def freqtrade_dry_run_report() -> None:
    payload = write_freqtrade_dry_run_report()
    print(
        {
            "report": "reports/freqtrade/status/latest_operational_status.json",
            "reconciliation": payload["reconciliation"]["status"],
        }
    )


@freqtrade_app.command("ingest-logs")
def freqtrade_ingest_logs() -> None:
    payload = ingest_freqtrade_logs()
    print({"logs": "reports/freqtrade/logs/latest_logs.json", **payload})


@freqtrade_app.command("reconcile")
def freqtrade_reconcile() -> None:
    payload = FreqtradeRunner(_event_store()).reconcile()
    print(
        {
            "reconciliation": payload["status"],
            "report": "reports/freqtrade/reconciliation/latest_reconciliation.json",
        }
    )
    if payload["status"] == "FAIL":
        raise typer.Exit(1)


@freqtrade_app.command("operational-manifest")
def freqtrade_operational_manifest() -> None:
    path = DockerOps().write_operation_manifest(
        DockerOps().get_container_status(),
    )
    print({"manifest": str(path), "live_trading_enabled": False})


@freqtrade_app.command("artifacts-scan")
def freqtrade_artifacts_scan() -> None:
    payload = scan_freqtrade_artifacts()
    print(
        {
            "artifact_scan": payload["status"],
            "artifacts_found": payload["artifacts_found"],
            "report": "reports/freqtrade/trades/latest_artifact_scan.json",
        }
    )


@freqtrade_app.command("trades-ingest")
def freqtrade_trades_ingest() -> None:
    payload = ingest_trade_artifacts()
    print(
        {
            "ingestion": payload["status"],
            "parsed_records": payload["parsed_records_count"],
            "report": "reports/freqtrade/trades/latest_trades_ingested.json",
        }
    )
    if payload["status"] == "FAIL":
        raise typer.Exit(1)


@freqtrade_app.command("trades-normalize")
def freqtrade_trades_normalize() -> None:
    payload = normalize_trade_artifacts()
    print(
        {
            "normalization": payload["status"],
            "normalized_records": payload["normalized_records_count"],
            "report": "reports/freqtrade/trades/latest_trades_normalized.json",
        }
    )
    if payload["status"] == "FAIL":
        raise typer.Exit(1)


@freqtrade_app.command("trade-reconcile")
def freqtrade_trade_reconcile() -> None:
    payload = reconcile_freqtrade_trades(event_store=_event_store())
    print(
        {
            "trade_reconciliation": payload["status"],
            "trade_level_comparison_available": payload["trade_level_comparison_available"],
            "report": "reports/freqtrade/trades/latest_trade_reconciliation.json",
        }
    )
    if payload["status"] == "FAIL":
        raise typer.Exit(1)


@freqtrade_app.command("trade-report")
def freqtrade_trade_report() -> None:
    payload = write_freqtrade_trade_report()
    print(
        {
            "trade_report": payload["trade_reconciliation_status"],
            "report": "reports/freqtrade/trades/latest_trade_report.md",
            "live_trading_enabled": False,
        }
    )
    if payload["trade_reconciliation_status"] == "FAIL":
        raise typer.Exit(1)


@dryrun_app.command("history")
def dryrun_history() -> None:
    payload = append_history_record()
    print(
        {
            "history": "reports/dryrun/latest_history.json",
            "records_count": payload["records_count"],
            "live_trading_enabled": False,
        }
    )


@dryrun_app.command("compare")
def dryrun_compare() -> None:
    payload = build_dryrun_comparison()
    print(
        {
            "comparison": payload["status"],
            "report": "reports/dryrun/latest_comparison.json",
            "live_trading_enabled": False,
        }
    )
    if payload["status"] == "FAIL":
        raise typer.Exit(1)


@dryrun_app.command("divergence-check")
def dryrun_divergence_check() -> None:
    payload = check_dryrun_divergence()
    print(
        {
            "divergence": payload["status"],
            "score": payload["score"],
            "report": "reports/dryrun/latest_divergence.json",
        }
    )
    if payload["status"] == "FAIL":
        raise typer.Exit(1)


@dryrun_app.command("monitor-report")
def dryrun_monitor_report() -> None:
    payload = generate_dryrun_monitoring_report()
    print(
        {
            "monitoring": payload["status"],
            "report": payload["latest_report_path"],
            "live_promotion_status": payload["live_promotion_status"],
        }
    )
    if payload["status"] == "FAIL":
        raise typer.Exit(1)


@dryrun_app.command("promote-check")
def dryrun_promote_check() -> None:
    payload = check_promotion_readiness()
    print(
        {
            "promotion": payload["status"],
            "live_promotion_status": payload["live_promotion_status"],
            "live_eligible": payload["live_eligible"],
        }
    )


@dryrun_app.command("status")
def dryrun_status() -> None:
    payload = generate_dryrun_monitoring_report()
    print(
        {
            "status": payload["status"],
            "comparison": payload["latest_comparison_status"],
            "divergence": payload["latest_divergence_status"],
            "promotion": payload["latest_promotion_status"],
            "live_promotion_status": payload["live_promotion_status"],
        }
    )


@dryrun_app.command("trade-reconcile")
def dryrun_trade_reconcile() -> None:
    freqtrade_trade_reconcile()


@dryrun_app.command("trade-report")
def dryrun_trade_report() -> None:
    freqtrade_trade_report()


@dataset_app.command("seed-expanded")
def dataset_seed_expanded() -> None:
    payload = seed_expanded_demo_data()
    print(
        {
            "dataset": "expanded_demo",
            "rows": payload["rows"],
            "symbols": payload["symbols"],
            "timeframes": payload["timeframes"],
            "live_trading_enabled": False,
        }
    )


@dataset_app.command("manifest")
def dataset_manifest() -> None:
    payload = build_dataset_manifest()
    print(
        {
            "status": payload["status"],
            "dataset_id": payload["dataset_id"],
            "rows": payload["rows"],
            "report": "reports/datasets/latest_manifest.json",
        }
    )


@dataset_app.command("quality")
def dataset_quality() -> None:
    payload = run_dataset_quality()
    print(
        {
            "status": payload["status"],
            "failures": payload["failures"],
            "warnings_count": len(payload["warnings"]),
            "report": "reports/datasets/latest_quality.json",
        }
    )
    if payload["status"] == "FAIL":
        raise typer.Exit(1)


@dataset_app.command("splits")
def dataset_splits() -> None:
    payload = build_dataset_splits()
    print(
        {
            "status": payload["status"],
            "items": len(payload["items"]),
            "report": "reports/datasets/latest_splits.json",
        }
    )


@dataset_app.command("leakage-check")
def dataset_leakage_check() -> None:
    payload = run_leakage_checks()
    print(
        {
            "status": payload["status"],
            "target_leakage": payload["target_leakage"],
            "report": "reports/datasets/latest_leakage_check.json",
        }
    )
    if payload["status"] == "FAIL":
        raise typer.Exit(1)


@dataset_app.command("evidence-score")
def dataset_evidence_score() -> None:
    payload = calculate_evidence_score()
    print(
        {
            "status": payload["final_evidence_status"],
            "live_promotion_status": payload["live_promotion_status"],
            "report": "reports/evidence/latest_evidence_score.json",
        }
    )


@evidence_app.command("research-report")
def evidence_research_report() -> None:
    payload = write_research_evidence_report()
    print(
        {
            "status": payload["evidence_score"]["final_evidence_status"],
            "quality": payload["dataset_quality_summary"]["status"],
            "live_promotion_status": payload["live_promotion_status"],
            "report": "reports/evidence/latest_research_evidence_report.md",
        }
    )


@historical_app.command("import-csv")
def historical_import_csv(
    path: Path = Path("tests/fixtures/historical/sample_ohlcv_standard.csv"),
    symbol: str | None = None,
    timeframe: str = "1d",
    source_name: str = "fixture_local",
) -> None:
    payload = import_historical_csv(
        path,
        symbol=symbol,
        timeframe=timeframe,
        source_name=source_name,
        allow_external_path=False,
    )
    print(
        {
            "status": payload["status"],
            "rows": payload["rows"],
            "normalized_path": payload["normalized_path"],
            "live_trading_enabled": False,
        }
    )


@historical_app.command("normalize")
def historical_normalize() -> None:
    payload = normalize_latest_historical()
    print(
        {
            "status": "NORMALIZED",
            "rows": payload["rows"],
            "normalized_path": payload["normalized_path"],
            "live_trading_enabled": False,
        }
    )


@historical_app.command("manifest")
def historical_manifest() -> None:
    payload = build_historical_manifest()
    print(
        {
            "status": payload["status"],
            "dataset_id": payload["dataset_id"],
            "rows": payload["rows"],
            "report": "reports/historical/manifests/latest_manifest.json",
        }
    )


@historical_app.command("quality")
def historical_quality() -> None:
    payload = run_historical_quality()
    print(
        {
            "status": payload["status"],
            "failures": payload["failures"],
            "warnings_count": len(payload["warnings"]),
            "report": "reports/historical/quality/latest_quality.json",
        }
    )
    if payload["status"] == "FAIL":
        raise typer.Exit(1)


@historical_app.command("splits")
def historical_splits() -> None:
    payload = build_historical_splits()
    print(
        {
            "status": payload["status"],
            "items": len(payload["items"]),
            "report": "reports/historical/evidence/latest_splits.json",
        }
    )


@historical_app.command("evidence-score")
def historical_evidence_score() -> None:
    payload = calculate_historical_evidence_score()
    print(
        {
            "status": payload["final_evidence_status"],
            "live_promotion_status": payload["live_promotion_status"],
            "report": "reports/historical/evidence/latest_historical_evidence_score.json",
        }
    )


@historical_app.command("research-report")
def historical_research_report() -> None:
    payload = write_historical_research_report()
    print(
        {
            "status": payload["evidence_score"]["final_evidence_status"],
            "quality": payload["quality_summary"]["status"],
            "live_promotion_status": payload["live_promotion_status"],
            "report": "reports/historical/evidence/latest_historical_research_report.md",
        }
    )


@historical_app.command("provider-check")
def historical_provider_check() -> None:
    payload = check_historical_providers()
    print(
        {
            "status": payload["status"],
            "providers": payload["providers"],
            "internet_required": payload["internet_required"],
            "live_trading_enabled": False,
        }
    )


@historical_app.command("status")
def historical_status() -> None:
    providers = check_historical_providers()
    manifest = build_historical_manifest()
    quality = run_historical_quality()
    evidence = calculate_historical_evidence_score()
    payload = {
        "status": "PASS" if quality["status"] in {"PASS", "WARN"} else "FAIL",
        "provider_status": providers["providers"],
        "imported_datasets_count": 1 if manifest["rows"] else 0,
        "latest_manifest_status": manifest["status"],
        "latest_quality_status": quality["status"],
        "latest_historical_evidence_status": evidence["final_evidence_status"],
        "source_types": [manifest["source_type"]],
        "blockers": evidence["blockers"],
        "warnings": evidence["warnings"],
        "latest_report_path": "reports/historical/evidence/latest_historical_evidence_score.md",
        "live_promotion_status": "LIVE_BLOCKED",
    }
    from quant_os.data.historical_cache import write_status

    write_status(payload)
    print(payload)


@proving_app.command("run-once")
def proving_run_once() -> None:
    payload = run_proving_once(_event_store())
    print(
        {
            "run_id": payload["record"]["run_id"],
            "readiness": payload["readiness"]["readiness_status"],
            "live_promotion_status": payload["readiness"]["live_promotion_status"],
            "report": "reports/proving/latest_proving_report.md",
        }
    )


@proving_app.command("status")
def proving_status() -> None:
    payload = write_proving_status()
    print(
        {
            "status": payload["status"],
            "history_records_count": payload["history_records_count"],
            "current_success_streak": payload["streaks"]["current_success_streak"],
            "live_promotion_status": payload["live_promotion_status"],
            "report": "reports/proving/latest_status.json",
        }
    )


@proving_app.command("history")
def proving_history() -> None:
    records = load_proving_history()
    status = write_proving_status(records)
    print(
        {
            "history_records_count": len(records),
            "successful_runs": status["streaks"]["successful_runs"],
            "failed_runs": status["streaks"]["failed_runs"],
            "live_promotion_status": "LIVE_BLOCKED",
        }
    )


@proving_app.command("incidents")
def proving_incidents() -> None:
    payload = summarize_incidents()
    print(
        {
            "incidents_count": payload["incidents_count"],
            "unresolved_count": payload["unresolved_count"],
            "by_severity": payload["by_severity"],
            "live_promotion_status": payload["live_promotion_status"],
        }
    )


@proving_app.command("readiness")
def proving_readiness() -> None:
    payload = evaluate_proving_readiness()
    print(
        {
            "readiness": payload["readiness_status"],
            "dry_run_proven": payload["dry_run_proven"],
            "live_promotion_status": payload["live_promotion_status"],
            "blockers": payload["blockers"],
            "report": "reports/proving/latest_readiness.json",
        }
    )


@proving_app.command("report")
def proving_report() -> None:
    payload = write_proving_report()
    print(
        {
            "readiness": payload["readiness_status"],
            "history_records_count": payload["history_records_count"],
            "live_promotion_status": payload["live_promotion_status"],
            "report": "reports/proving/latest_proving_report.md",
        }
    )


@canary_app.command("policy")
def canary_policy() -> None:
    payload = build_canary_policy()
    print(
        {
            "status": payload["status"],
            "live_promotion_status": payload["live_promotion_status"],
            "report": "reports/canary/latest_policy.md",
        }
    )


@canary_app.command("checklist")
def canary_checklist() -> None:
    payload = build_canary_checklist()
    print(
        {
            "status": payload["status"],
            "blockers": payload["blockers"],
            "live_promotion_status": payload["live_promotion_status"],
            "report": "reports/canary/latest_checklist.md",
        }
    )


@canary_app.command("preflight")
def canary_preflight() -> None:
    payload = evaluate_canary_preflight()
    print(
        {
            "status": payload["status"],
            "preflight_status": payload["preflight_status"],
            "blockers": payload["blockers"],
            "live_promotion_status": payload["live_promotion_status"],
            "report": "reports/canary/latest_preflight.md",
        }
    )


@canary_app.command("incident-drill")
def canary_incident_drill() -> None:
    payload = build_incident_drill()
    print(
        {
            "status": payload["status"],
            "scenarios": len(payload["scenarios"]),
            "live_promotion_status": payload["live_promotion_status"],
            "report": "reports/canary/latest_incident_drill.md",
        }
    )


@canary_app.command("capital-ladder")
def canary_capital_ladder() -> None:
    payload = build_capital_ladder()
    print(
        {
            "status": payload["status"],
            "current_stage": payload["current_stage"],
            "live_promotion_status": payload["live_promotion_status"],
            "report": "reports/canary/latest_capital_ladder.md",
        }
    )


@canary_app.command("readiness")
def canary_readiness() -> None:
    payload = evaluate_canary_readiness()
    print(
        {
            "readiness": payload["readiness_status"],
            "planning_status": payload["planning_status"],
            "blockers": payload["blockers"],
            "live_promotion_status": payload["live_promotion_status"],
            "report": "reports/canary/latest_readiness.md",
        }
    )


@canary_app.command("report")
def canary_report() -> None:
    payload = write_canary_report_bundle()
    print(
        {
            "status": payload["status"],
            "preflight_status": payload["preflight_status"],
            "readiness_status": payload["readiness_status"],
            "live_promotion_status": payload["live_promotion_status"],
            "report": payload["latest_report_path"],
        }
    )


@canary_app.command("permission-import")
def canary_permission_import(
    path: Path = Path("tests/fixtures/canary/permission_manifest_safe.yaml"),
) -> None:
    payload = import_permission_manifest(path)
    print(
        {
            "status": payload["status"],
            "scopes": payload["normalized_scope_list"],
            "blockers": payload["blockers"],
            "live_promotion_status": payload["live_promotion_status"],
            "report": "reports/canary/latest_permission_manifest.md",
        }
    )


@canary_app.command("arm-token")
def canary_arm_token() -> None:
    payload = generate_arm_token()
    print(
        {
            "status": payload["status"],
            "token_id": payload["token_id"],
            "rehearsal_only": payload["rehearsal_only"],
            "live_promotion_status": payload["live_promotion_status"],
            "report": "reports/canary/latest_arm_token.md",
        }
    )


@canary_app.command("preflight-rehearsal")
def canary_preflight_rehearsal() -> None:
    payload = run_preflight_rehearsal()
    print(
        {
            "status": payload["status"],
            "preflight_rehearsal_status": payload["preflight_rehearsal_status"],
            "blockers": payload["blockers"],
            "live_promotion_status": payload["live_promotion_status"],
            "report": "reports/canary/latest_preflight_rehearsal.md",
        }
    )


@canary_app.command("stoploss-proof")
def canary_stoploss_proof() -> None:
    payload = build_stoploss_proof()
    print(
        {
            "status": payload["status"],
            "design_status": payload["design_status"],
            "blockers": payload["blockers"],
            "live_promotion_status": payload["live_promotion_status"],
            "report": "reports/canary/latest_stoploss_proof.md",
        }
    )


@canary_app.command("rehearsal")
def canary_rehearsal() -> None:
    payload = run_canary_rehearsal()
    print(
        {
            "status": payload["status"],
            "rehearsal_status": payload["rehearsal_status"],
            "placed_orders": payload["placed_orders"],
            "exchange_connections": payload["exchange_connections"],
            "live_promotion_status": payload["live_promotion_status"],
            "report": "reports/canary/latest_rehearsal.md",
        }
    )


@canary_app.command("final-gate")
def canary_final_gate() -> None:
    payload = evaluate_final_gate()
    print(
        {
            "status": payload["status"],
            "final_gate_status": payload["final_gate_status"],
            "rehearsal_ready": payload["rehearsal_ready"],
            "live_promotion_status": payload["live_promotion_status"],
            "report": "reports/canary/latest_final_gate.md",
        }
    )


@canary_app.command("rehearsal-report")
def canary_rehearsal_report() -> None:
    payload = write_rehearsal_report()
    print(
        {
            "status": payload["status"],
            "final_gate_status": payload["final_gate_status"],
            "live_promotion_status": payload["live_promotion_status"],
            "report": "reports/canary/latest_rehearsal_report.md",
        }
    )


@features_app.command("build")
def features_build() -> None:
    payload = write_feature_report()
    print(
        {
            "features_built": True,
            "rows": payload["rows"],
            "report": payload["report_path"],
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


@strategy_app.command("research")
def strategy_research(symbol: str = "SPY") -> None:
    payload = run_strategy_research(symbol)
    print(
        {
            "status": payload["status"],
            "strategies_tested": len(payload["results"]),
            "report": "reports/strategy/research/latest_research.json",
            "live_promotion_status": payload["live_promotion_status"],
        }
    )


@strategy_app.command("ablation")
def strategy_ablation(symbol: str = "SPY") -> None:
    payload = run_strategy_ablation(symbol)
    print({"status": payload["status"], "report": "reports/strategy/ablation/latest_ablation.json"})


@strategy_app.command("walk-forward")
def strategy_walk_forward(symbol: str = "SPY") -> None:
    payload = run_walk_forward_validation(symbol)
    print(
        {
            "status": payload["status"],
            "report": "reports/strategy/walk_forward/latest_walk_forward.json",
        }
    )


@strategy_app.command("regime-tests")
def strategy_regime_tests(symbol: str = "SPY") -> None:
    payload = run_regime_tests(symbol)
    print(
        {"status": payload["status"], "report": "reports/strategy/regime/latest_regime_tests.json"}
    )


@strategy_app.command("overfit-check")
def strategy_overfit_check(symbol: str = "SPY") -> None:
    payload = run_overfit_checks(symbol)
    print(
        {
            "status": payload["status"],
            "warnings": payload["warnings"],
            "report": "reports/strategy/overfit/latest_overfit_check.json",
        }
    )


@strategy_app.command("leaderboard")
def strategy_leaderboard(symbol: str = "SPY") -> None:
    payload = build_strategy_leaderboard(symbol)
    print(
        {
            "status": payload["status"],
            "top_strategy": payload["top_strategy"],
            "report": "reports/strategy/leaderboard/latest_leaderboard.json",
            "live_promotion_status": payload["live_promotion_status"],
        }
    )


@strategy_app.command("research-report")
def strategy_research_report() -> None:
    payload = write_strategy_research_report()
    print(
        {
            "report": "reports/strategy/latest_research_report.md",
            "strategies_tested": len(payload["strategy_list"]),
            "live_promotion_status": payload["live_promotion_status"],
        }
    )


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
