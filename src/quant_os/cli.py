from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich import print

from quant_os.adapters.event_store_jsonl import JsonlEventStore
from quant_os.adapters.market_data_parquet import LocalParquetMarketData
from quant_os.autonomy.daemon import daemon_status, run_daemon, stop_daemon
from quant_os.autonomy.dry_run_proving import DryRunProvingConfig, run_dry_run_proving_cycle
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
from quant_os.data.prediction_markets.activity_capture import capture_polymarket_activity
from quant_os.data.provider_check import check_historical_providers
from quant_os.data.providers.polymarket_capture import (
    DEFAULT_POLYMARKET_FIXTURE,
    capture_polymarket_markets,
)
from quant_os.data.quality import validate_ohlcv
from quant_os.data.venue_capture import capture_public_venue_snapshot
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
from quant_os.live_canary.capabilities import inspect_exchange_capabilities
from quant_os.live_canary.live_fire import fire_live_canary
from quant_os.live_canary.live_preflight import prepare_live_canary, run_live_preflight
from quant_os.live_canary.live_reconcile import reconcile_live_canary
from quant_os.live_canary.live_report import write_live_canary_report_bundle
from quant_os.live_canary.live_status import live_canary_status, stop_live_canary
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
from quant_os.readiness.sequence2 import write_sequence2_readiness_report
from quant_os.replay.engine import ReplayEngine, ReplayOrderIntent
from quant_os.replay.realism_report import write_replay_realism_report
from quant_os.replay.venue_calibration import DEFAULT_VENUE_FIXTURE, run_venue_calibration
from quant_os.research.backtest import run_backtest
from quant_os.research.calibration.diagnostics import calibration_diagnostics
from quant_os.research.calibration.penalties import apply_edge_penalties
from quant_os.research.calibration.probabilities import estimate_signal_probability
from quant_os.research.calibration.uncertainty import estimate_uncertainty
from quant_os.research.crypto.calibrated_edge_report import write_calibrated_edge_report
from quant_os.research.crypto.features import build_crypto_features
from quant_os.research.crypto.ingest import build_crypto_research_dataset
from quant_os.research.crypto.reports import write_crypto_research_report
from quant_os.research.historical_evidence import (
    build_historical_splits,
    calculate_historical_evidence_score,
)
from quant_os.research.historical_research_report import write_historical_research_report
from quant_os.research.leaderboard import build_strategy_leaderboard
from quant_os.research.overfit_checks import run_overfit_checks
from quant_os.research.prediction_markets.ablation import write_ablation_report
from quant_os.research.prediction_markets.activity_dataset_growth import (
    write_activity_dataset_growth_report,
)
from quant_os.research.prediction_markets.candidate_predictions import (
    write_prediction_candidate_evaluation_report,
    write_prediction_candidate_report,
    write_prediction_feature_report,
)
from quant_os.research.prediction_markets.dataset_growth import write_dataset_growth_report
from quant_os.research.prediction_markets.evaluation import (
    write_lane_activity_evaluation_report,
    write_lane_evaluation_report,
    write_real_activity_signal_evaluation_report,
)
from quant_os.research.prediction_markets.historical_dataset import (
    write_expanded_historical_dataset_report,
    write_signal_discovery_dataset_report,
)
from quant_os.research.prediction_markets.historical_dataset import (
    write_historical_dataset_report as write_prediction_historical_dataset_report,
)
from quant_os.research.prediction_markets.label_quality import write_label_quality_report
from quant_os.research.prediction_markets.lane_activity_dataset import (
    write_lane_activity_dataset_report,
    write_sequence25_activity_dataset_report,
    write_sequence26_lane_dataset_summary_report,
)
from quant_os.research.prediction_markets.lane_activity_quality import (
    write_lane_activity_quality_report,
)
from quant_os.research.prediction_markets.lane_decision import write_lane_decision_report
from quant_os.research.prediction_markets.lane_dynamics import write_dynamic_signal_report
from quant_os.research.prediction_markets.lane_selection import write_lane_selection_report
from quant_os.research.prediction_markets.lane_timeline import (
    write_lane_timeline_summary_report,
)
from quant_os.research.prediction_markets.manipulation_flags import (
    write_manipulation_flags_report,
)
from quant_os.research.prediction_markets.market_quality_filters import (
    write_market_quality_filter_report,
)
from quant_os.research.prediction_markets.market_strata import write_market_strata_report
from quant_os.research.prediction_markets.oos_validation import write_lane_oos_validation_report
from quant_os.research.prediction_markets.quality_report import (
    write_market_inventory_report,
    write_market_quality_report,
    write_research_priority_report,
)
from quant_os.research.prediction_markets.reference_alignment import (
    write_reference_context_report,
)
from quant_os.research.prediction_markets.reference_quality import (
    write_reference_quality_report,
)
from quant_os.research.prediction_markets.replay_feasibility_report import (
    write_lane_replay_readiness_report,
    write_oos_replay_readiness_report,
    write_real_activity_replay_readiness_report,
    write_replay_feasibility_report,
    write_replay_precondition_report,
    write_venue_replay_readiness_report,
)
from quant_os.research.prediction_markets.resolved_history_growth import (
    write_resolved_history_growth_report,
)
from quant_os.research.prediction_markets.robustness import write_lane_robustness_report
from quant_os.research.prediction_markets.signal_families import write_signal_family_report
from quant_os.research.prediction_markets.venue_signals import write_venue_signal_report
from quant_os.research.prediction_markets.wallet_flow_features import write_wallet_flow_report
from quant_os.research.prediction_markets.wallet_reports import write_wallet_research_report
from quant_os.research.regime_tests import run_regime_tests
from quant_os.research.research_evidence_report import write_research_evidence_report
from quant_os.research.research_report import run_strategy_research, write_strategy_research_report
from quant_os.research.strategies import baseline_ma_candidates
from quant_os.research.strategy_ablation import run_strategy_ablation
from quant_os.research.tournament import run_tournament
from quant_os.research.validation.walk_forward import run_crypto_walk_forward
from quant_os.research.walk_forward import run_walk_forward_validation
from quant_os.risk.firewall import RiskFirewall
from quant_os.risk.limits import RiskLimits
from quant_os.security.live_trading_guard import live_trading_guard
from quant_os.validation.runner import list_scenarios, run_all_scenarios, run_scenario
from quant_os.watchdog.health_checks import run_watchdog

app = typer.Typer(help="Local deterministic QuantOps simulation foundation.")
autonomous_app = typer.Typer(help="Autonomous safe-mode runbooks.")
data_app = typer.Typer(help="Market-agnostic data spine commands.")
features_app = typer.Typer(help="Deterministic feature-building commands.")
research_app = typer.Typer(help="Research lane commands.")
replay_app = typer.Typer(help="Execution-aware offline replay commands.")
calibration_app = typer.Typer(help="Signal calibration and edge scoring commands.")
validation_app = typer.Typer(help="Autonomy behavioral validation commands.")
strategy_app = typer.Typer(help="Strategy governance commands.")
freqtrade_app = typer.Typer(help="Freqtrade dry-run-only commands.")
dryrun_app = typer.Typer(help="Dry-run comparison monitoring commands.")
dataset_app = typer.Typer(help="Offline dataset evidence commands.")
evidence_app = typer.Typer(help="Research evidence report commands.")
historical_app = typer.Typer(help="Historical data ingestion commands.")
proving_app = typer.Typer(help="Autonomous proving-mode commands.")
canary_app = typer.Typer(help="Tiny-live canary policy gates and default-off execution lane.")
readiness_app = typer.Typer(help="Evidence-based readiness reports.")
app.add_typer(autonomous_app, name="autonomous")
app.add_typer(data_app, name="data")
app.add_typer(features_app, name="features")
app.add_typer(research_app, name="research")
app.add_typer(replay_app, name="replay")
app.add_typer(calibration_app, name="calibration")
app.add_typer(validation_app, name="validation")
app.add_typer(strategy_app, name="strategy")
app.add_typer(freqtrade_app, name="freqtrade")
app.add_typer(dryrun_app, name="dryrun")
app.add_typer(dataset_app, name="dataset")
app.add_typer(evidence_app, name="evidence")
app.add_typer(historical_app, name="historical")
app.add_typer(proving_app, name="proving")
app.add_typer(canary_app, name="canary")
app.add_typer(readiness_app, name="readiness")

DEFAULT_POLYMARKET_WALLET_FIXTURE = (
    Path("tests") / "fixtures" / "prediction_markets" / "polymarket_wallet_activity_sample.json"
)
DEFAULT_POLYMARKET_HISTORY_FIXTURE = (
    Path("tests")
    / "fixtures"
    / "prediction_markets"
    / "history"
    / "polymarket_resolution_history_sample.json"
)
DEFAULT_POLYMARKET_EXPANDED_HISTORY_FIXTURE = (
    Path("tests")
    / "fixtures"
    / "prediction_markets"
    / "history"
    / "polymarket_resolution_history_expanded_sample.json"
)
DEFAULT_POLYMARKET_SIGNAL_DISCOVERY_FIXTURE = (
    Path("tests")
    / "fixtures"
    / "prediction_markets"
    / "history"
    / "polymarket_signal_discovery_sample.json"
)
DEFAULT_POLYMARKET_LANE_ACTIVITY_FIXTURE = (
    Path("tests")
    / "fixtures"
    / "prediction_markets"
    / "activity"
    / "polymarket_short_dated_lane_activity_sample.json"
)
DEFAULT_POLYMARKET_REAL_CACHED_ACTIVITY_FIXTURE = (
    Path("tests")
    / "fixtures"
    / "prediction_markets"
    / "activity"
    / "polymarket_real_cached_activity_sample.json"
)
DEFAULT_POLYMARKET_OOS_ACTIVITY_FIXTURE = (
    Path("tests")
    / "fixtures"
    / "prediction_markets"
    / "activity"
    / "polymarket_real_cached_activity_oos_sample.json"
)
DEFAULT_BENCHMARK_FIXTURE_ROOT = Path("tests") / "fixtures" / "benchmark_sources"
DEFAULT_POLYMARKET_PUBLIC_SNAPSHOT_FIXTURE = (
    DEFAULT_BENCHMARK_FIXTURE_ROOT / "polymarket_public_snapshot.json"
)
DEFAULT_PMXT_MANIFEST_FIXTURE = DEFAULT_BENCHMARK_FIXTURE_ROOT / "pmxt_manifest.json"
DEFAULT_REFERENCE_DATASETS_MANIFEST_FIXTURE = (
    DEFAULT_BENCHMARK_FIXTURE_ROOT / "reference_datasets_manifest.json"
)
DEFAULT_SOCIAL_CAPTURE_FIXTURE = (
    Path("tests") / "fixtures" / "social_capture" / "x_capture_sample"
)
DEFAULT_RESEARCH_INTAKE_SOURCE_CONFIG = Path("configs") / "research_intake_sources.yaml"
DEFAULT_PM_CRYPTO_UPDOWN_FIXTURE_ROOT = (
    Path("tests") / "fixtures" / "replay_candidates" / "pm_crypto_updown"
)
DEFAULT_PM_LP_REFRESH_LAG_FIXTURE = (
    Path("tests")
    / "fixtures"
    / "replay_candidates"
    / "pm_lp_refresh_lag"
    / "refresh_lag_windows.json"
)
DEFAULT_PM_LP_REFRESH_LAG_PUBLIC_SOURCE_FIXTURE = (
    Path("tests")
    / "fixtures"
    / "replay_candidates"
    / "pm_lp_refresh_lag"
    / "public_source_sample"
    / "blocked_missing_public_fill_attribution.json"
)


def _repo_default_path(path: Path) -> Path:
    if path.exists():
        return path
    return Path(__file__).resolve().parents[2] / path


def _optional_path_list(paths: list[Path] | None) -> list[Path] | None:
    return list(paths) if paths else None


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


@data_app.command("validate")
def data_spine_validate(periods: int = typer.Option(120, min=20)) -> None:
    dataset = build_crypto_research_dataset(periods=periods)
    print(
        {
            "status": dataset.record.quality["status"],
            "dataset_id": dataset.dataset_id,
            "rows": dataset.record.rows,
            "symbols": sorted(dataset.frame["symbol"].unique().tolist()),
            "layer": dataset.record.layer.value,
            "live_trading_enabled": False,
        }
    )


@data_app.command("venue-capture")
def data_venue_capture(
    venue: str = typer.Option("binance", "--venue"),
    timeframe: str = typer.Option("1m", "--timeframe"),
) -> None:
    payload = capture_public_venue_snapshot(exchange_id=venue, timeframe=timeframe)
    print(payload)


@data_app.command("source-registry-report")
def data_source_registry_report() -> None:
    from quant_os.data.source_registry import build_source_registry_report

    payload = build_source_registry_report(output_root=Path("."))
    print(
        {
            "status": payload["status"],
            "sources_count": payload["sources_count"],
            "live_capable_sources": payload["live_capable_sources"],
            "report": "reports/external_benchmarks/source_registry/latest_source_registry.json",
            "live_trading_enabled": payload["live_trading_enabled"],
            "execution_authority_added": payload["execution_authority_added"],
        }
    )


@data_app.command("capture-prediction-markets")
def data_capture_prediction_markets(
    fixture_path: Annotated[Path | None, typer.Option("--fixture-path")] = None,
    allow_network_fetch: bool = typer.Option(False, "--allow-network-fetch"),
    explicit_network_fetch: bool = typer.Option(False, "--explicit-network-fetch"),
) -> None:
    path = (
        fixture_path
        if fixture_path is not None
        else None
        if allow_network_fetch
        else DEFAULT_POLYMARKET_FIXTURE
    )
    payload = capture_polymarket_markets(
        fixture_path=path,
        allow_network_fetch=allow_network_fetch,
        explicit_network_fetch=explicit_network_fetch,
    )
    print(payload)
    if payload["status"] == "BLOCKED":
        raise typer.Exit(1)


@data_app.command("capture-polymarket-activity")
def data_capture_polymarket_activity(
    fixture_path: Annotated[Path | None, typer.Option("--fixture-path")] = None,
    manual_network: bool = typer.Option(False, "--manual-network"),
    explicit_network_ack: bool = typer.Option(False, "--explicit-network-ack"),
) -> None:
    path = (
        None
        if manual_network and fixture_path is None
        else fixture_path or DEFAULT_POLYMARKET_REAL_CACHED_ACTIVITY_FIXTURE
    )
    payload = capture_polymarket_activity(
        fixture_path=path,
        manual_network=manual_network,
        explicit_network_ack=explicit_network_ack,
    )
    print(
        {
            "status": payload["status"],
            "source_mode": payload.get("source_mode"),
            "raw_event_count": payload.get("raw_event_count"),
            "usable_event_count": payload.get("usable_event_count"),
            "report": "reports/sequence25/activity_capture/latest_activity_capture.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )
    if payload["status"] == "BLOCKED":
        raise typer.Exit(1)


@research_app.command("crypto-build")
def research_crypto_build(periods: int = typer.Option(240, min=50)) -> None:
    dataset = build_crypto_research_dataset(periods=periods)
    payload = write_crypto_research_report(dataset.frame)
    print(
        {
            "status": payload["status"],
            "dataset_id": dataset.dataset_id,
            "rows": payload["rows"],
            "symbols": payload["symbols"],
            "signals": payload["signal_count"],
            "report": "reports/crypto/latest_research.json",
            "live_trading_enabled": False,
        }
    )


@research_app.command("social-capture-inventory")
def research_social_capture_inventory(
    capture_root: Annotated[Path | None, typer.Option("--capture-root")] = None,
) -> None:
    from quant_os.research.social_intake.capture_loader import write_capture_inventory

    payload = write_capture_inventory(
        capture_root=capture_root or _repo_default_path(DEFAULT_SOCIAL_CAPTURE_FIXTURE),
    )
    print(
        {
            "status": "CAPTURE_INVENTORIED",
            "post_count": payload["post_count"],
            "report": "reports/sequence34/social_intake/latest_capture_inventory.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("social-post-classification")
def research_social_post_classification(
    capture_root: Annotated[Path | None, typer.Option("--capture-root")] = None,
) -> None:
    from quant_os.research.social_intake.post_classification_report import (
        write_post_classification_report,
    )

    payload = write_post_classification_report(
        capture_root=capture_root or _repo_default_path(DEFAULT_SOCIAL_CAPTURE_FIXTURE),
    )
    print(
        {
            "status": payload["classification_status"],
            "post_count": payload["post_count"],
            "report": "reports/sequence34/social_intake/latest_post_classification.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("social-hypothesis-queue")
def research_social_hypothesis_queue(
    capture_root: Annotated[Path | None, typer.Option("--capture-root")] = None,
) -> None:
    from quant_os.research.social_intake.hypothesis_queue import (
        write_hypothesis_queue_report,
    )

    payload = write_hypothesis_queue_report(
        capture_root=capture_root or _repo_default_path(DEFAULT_SOCIAL_CAPTURE_FIXTURE),
    )
    print(
        {
            "status": payload["hypothesis_queue_status"],
            "hypothesis_count": payload["hypothesis_count"],
            "report": "reports/sequence34/hypothesis_queue/latest_hypothesis_queue.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("social-task-queue")
def research_social_task_queue(
    capture_root: Annotated[Path | None, typer.Option("--capture-root")] = None,
) -> None:
    from quant_os.research.social_intake.research_task_queue import (
        write_research_task_queue_report,
    )

    payload = write_research_task_queue_report(
        capture_root=capture_root or _repo_default_path(DEFAULT_SOCIAL_CAPTURE_FIXTURE),
    )
    print(
        {
            "status": payload["research_task_queue_status"],
            "top_priority_reason": payload["top_priority_reason"],
            "report": "reports/sequence34/research_tasks/latest_research_task_queue.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("evidence-acquisition-plan")
def research_evidence_acquisition_plan(
    capture_root: Annotated[Path | None, typer.Option("--capture-root")] = None,
) -> None:
    from quant_os.research.social_intake.evidence_acquisition_report import (
        write_evidence_acquisition_report,
    )

    payload = write_evidence_acquisition_report(
        capture_root=capture_root or _repo_default_path(DEFAULT_SOCIAL_CAPTURE_FIXTURE),
    )
    print(
        {
            "status": payload["evidence_plan_status"],
            "phase33_blocker_addressed": payload["phase33_blocker_addressed"],
            "report": "reports/sequence34/evidence_acquisition/latest_evidence_plan.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("intake-source-policy")
def research_intake_source_policy(
    source_config_path: Annotated[Path | None, typer.Option("--source-config-path")] = None,
) -> None:
    from quant_os.research.intake.source_config import write_source_policy_report

    payload = write_source_policy_report(
        source_config_path=source_config_path
        or _repo_default_path(DEFAULT_RESEARCH_INTAKE_SOURCE_CONFIG),
    )
    print(
        {
            "status": payload["policy_status"],
            "allowed_source_count": payload["allowed_source_count"],
            "blocked_source_count": payload["blocked_source_count"],
            "report": "reports/sequence35/intake_sources/latest_source_policy.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("intake-run")
def research_intake_run(
    source_config_path: Annotated[Path | None, typer.Option("--source-config-path")] = None,
) -> None:
    from quant_os.research.intake.intake_run_report import write_intake_run_report

    payload = write_intake_run_report(
        source_config_path=source_config_path
        or _repo_default_path(DEFAULT_RESEARCH_INTAKE_SOURCE_CONFIG),
    )
    print(
        {
            "status": payload["run_status"],
            "run_id": payload["run_id"],
            "artifact_count": payload["artifact_count"],
            "duplicate_count": payload["duplicate_count"],
            "report": "reports/sequence35/intake_run/latest_intake_run.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("knowledge-ledger-summary")
def research_knowledge_ledger_summary(
    source_config_path: Annotated[Path | None, typer.Option("--source-config-path")] = None,
) -> None:
    from quant_os.research.intake.intake_run_report import write_intake_run_report
    from quant_os.research.intake.knowledge_ledger import write_knowledge_ledger_summary

    intake_run = write_intake_run_report(
        source_config_path=source_config_path
        or _repo_default_path(DEFAULT_RESEARCH_INTAKE_SOURCE_CONFIG),
    )
    payload = write_knowledge_ledger_summary(intake_run=intake_run)
    print(
        {
            "status": payload["ledger_status"],
            "unique_artifact_count": payload["unique_artifact_count"],
            "duplicate_artifact_count": payload["duplicate_artifact_count"],
            "report": "reports/sequence35/knowledge_ledger/latest_knowledge_ledger_summary.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("evidence-to-shadow-bridge")
def research_evidence_to_shadow_bridge(
    source_config_path: Annotated[Path | None, typer.Option("--source-config-path")] = None,
) -> None:
    from quant_os.research.intake.evidence_to_shadow_report import (
        write_evidence_to_shadow_report,
    )

    payload = write_evidence_to_shadow_report(
        source_config_path=source_config_path
        or _repo_default_path(DEFAULT_RESEARCH_INTAKE_SOURCE_CONFIG),
    )
    print(
        {
            "status": payload["bridge_status"],
            "targeted_blockers": payload["targeted_blockers"],
            "report": "reports/sequence35/evidence_bridge/latest_evidence_to_shadow_bridge.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("pm-crypto-updown-dataset")
def research_pm_crypto_updown_dataset(
    fixture_root: Annotated[Path | None, typer.Option("--fixture-root")] = None,
) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_dataset_report import (
        write_pm_crypto_updown_dataset_report,
    )

    payload = write_pm_crypto_updown_dataset_report(
        fixture_root=fixture_root or _repo_default_path(DEFAULT_PM_CRYPTO_UPDOWN_FIXTURE_ROOT),
    )
    print(
        {
            "status": payload["readiness_status"],
            "row_count": payload["row_count"],
            "replay_ready_row_count": payload["replay_ready_row_count"],
            "report": "reports/sequence36/replay_dataset/latest_pm_crypto_updown_dataset.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("pm-crypto-updown-quality")
def research_pm_crypto_updown_quality(
    fixture_root: Annotated[Path | None, typer.Option("--fixture-root")] = None,
) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_dataset_report import (
        write_pm_crypto_updown_dataset_report,
    )

    payload = write_pm_crypto_updown_dataset_report(
        fixture_root=fixture_root or _repo_default_path(DEFAULT_PM_CRYPTO_UPDOWN_FIXTURE_ROOT),
    )
    print(
        {
            "status": payload["readiness_status"],
            "clob_coverage": payload["clob_coverage"],
            "spot_coverage": payload["spot_coverage"],
            "blockers": payload["blockers"],
            "report": "reports/sequence36/replay_dataset/latest_pm_crypto_updown_dataset.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("pm-crypto-updown-replay-eval")
def research_pm_crypto_updown_replay_eval(
    fixture_root: Annotated[Path | None, typer.Option("--fixture-root")] = None,
) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_replay_eval import (
        write_pm_crypto_updown_replay_eval_report,
    )

    payload = write_pm_crypto_updown_replay_eval_report(
        fixture_root=fixture_root or _repo_default_path(DEFAULT_PM_CRYPTO_UPDOWN_FIXTURE_ROOT),
    )
    print(
        {
            "status": payload["evaluation_status"],
            "row_count": payload["row_count"],
            "replay_ready_row_count": payload["replay_ready_row_count"],
            "candidate_signal_count": payload["candidate_signal_count"],
            "report": "reports/sequence37/replay_eval/latest_pm_crypto_updown_replay_eval.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("pm-crypto-updown-placebo")
def research_pm_crypto_updown_placebo(
    fixture_root: Annotated[Path | None, typer.Option("--fixture-root")] = None,
) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_replay_eval import (
        write_pm_crypto_updown_replay_eval_report,
    )

    payload = write_pm_crypto_updown_replay_eval_report(
        fixture_root=fixture_root or _repo_default_path(DEFAULT_PM_CRYPTO_UPDOWN_FIXTURE_ROOT),
    )
    placebo = payload["placebo_metrics"]
    print(
        {
            "status": placebo["placebo_comparison_status"],
            "promotion_blocked": placebo["promotion_blocked"],
            "report": "reports/sequence37/replay_eval/latest_pm_crypto_updown_replay_eval.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("pm-crypto-updown-shadow-bridge")
def research_pm_crypto_updown_shadow_bridge(
    fixture_root: Annotated[Path | None, typer.Option("--fixture-root")] = None,
) -> None:
    from quant_os.readiness.candidate_replay_readiness_report import (
        write_candidate_replay_readiness_report,
    )
    from quant_os.research.replay_candidates.pm_crypto_updown_replay_eval import (
        write_pm_crypto_updown_replay_eval_report,
    )
    from quant_os.research.replay_candidates.pm_crypto_updown_shadow_bridge import (
        write_pm_crypto_updown_shadow_bridge_report,
    )

    evaluation = write_pm_crypto_updown_replay_eval_report(
        fixture_root=fixture_root or _repo_default_path(DEFAULT_PM_CRYPTO_UPDOWN_FIXTURE_ROOT),
    )
    readiness = write_candidate_replay_readiness_report(evaluation_report=evaluation)
    payload = write_pm_crypto_updown_shadow_bridge_report(
        evaluation_report=evaluation,
        readiness_report=readiness,
    )
    print(
        {
            "status": payload["readiness_status"],
            "shadow_intent_count": payload["shadow_intent_count"],
            "blocked_intent_count": payload["blocked_intent_count"],
            "report": "reports/sequence37/shadow_bridge/latest_pm_crypto_updown_shadow_bridge.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("pm-crypto-updown-expansion-plan")
def research_pm_crypto_updown_expansion_plan(
    fixture_root: Annotated[Path | None, typer.Option("--fixture-root")] = None,
) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_expansion_plan import (
        write_pm_crypto_updown_expansion_plan,
    )

    payload = write_pm_crypto_updown_expansion_plan(
        fixture_root=fixture_root or _repo_default_path(DEFAULT_PM_CRYPTO_UPDOWN_FIXTURE_ROOT),
    )
    print(
        {
            "status": payload["plan_status"],
            "current_replay_ready_row_count": payload["current_replay_ready_row_count"],
            "rows_needed_from_current": payload["rows_needed_from_current"],
            "report": "reports/sequence38/evidence_expansion/latest_expansion_plan.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@data_app.command("pm-crypto-updown-capture-plan")
def data_pm_crypto_updown_capture_plan(
    manual_network_ok: bool = typer.Option(False, "--manual-network-ok"),
    run_id: str = typer.Option("manual_plan", "--run-id"),
) -> None:
    from quant_os.data.prediction_markets.pm_updown_real_cached_capture import (
        write_pm_crypto_updown_real_cached_capture_plan,
    )

    payload = write_pm_crypto_updown_real_cached_capture_plan(
        manual_network_ok=manual_network_ok,
        run_id=run_id,
    )
    print(
        {
            "status": payload["status"],
            "manual_only": payload["manual_only"],
            "network_enabled": payload["network_enabled"],
            "network_fetch_attempted": payload["network_fetch_attempted"],
            "report": "reports/sequence39/manual_capture/latest_real_cached_capture_plan.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@data_app.command("pm-lp-refresh-lag-capture-plan")
def data_pm_lp_refresh_lag_capture_plan() -> None:
    from quant_os.data.prediction_markets.pm_lp_refresh_lag_capture_plan import (
        write_pm_lp_refresh_lag_capture_plan,
    )

    payload = write_pm_lp_refresh_lag_capture_plan()
    print(
        {
            "status": payload["status"],
            "manual_only": payload["manual_only"],
            "network_enabled": payload["network_enabled"],
            "network_fetch_attempted": payload["network_fetch_attempted"],
            "report": ("reports/sequence48/capture_plan/latest_lp_refresh_lag_capture_plan.json"),
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@data_app.command("pm-crypto-updown-real-cached-import")
def data_pm_crypto_updown_real_cached_import(
    import_root: Annotated[
        Path | None,
        typer.Option("--import-root"),
    ] = None,
    real_cached_root: Annotated[list[Path] | None, typer.Option("--real-cached-root")] = None,
) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_real_cached_import import (
        import_pm_crypto_updown_real_cached_artifact_roots,
        import_pm_crypto_updown_real_cached_artifacts,
    )

    real_cached_roots = _optional_path_list(real_cached_root)
    if real_cached_roots:
        payload = import_pm_crypto_updown_real_cached_artifact_roots(
            import_roots=real_cached_roots,
        )
        report_path = "reports/sequence41/real_cached_import/latest_real_cached_import.json"
    else:
        payload = import_pm_crypto_updown_real_cached_artifacts(
            import_root=import_root or Path("data/external/manual_captures/pm_crypto_updown/manual_plan"),
        )
        report_path = "reports/sequence39/real_cached_import/latest_real_cached_import.json"
    print(
        {
            "status": payload["import_status"],
            "accepted_artifact_count": payload["accepted_artifact_count"],
            "real_cached_rows_imported": payload["real_cached_rows_imported"],
            "report": report_path,
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("pm-crypto-updown-window-acquisition")
def research_pm_crypto_updown_window_acquisition(
    fixture_root: Annotated[Path | None, typer.Option("--fixture-root")] = None,
    real_cached_root: Annotated[list[Path] | None, typer.Option("--real-cached-root")] = None,
) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_window_acquisition_report import (
        write_pm_crypto_updown_window_acquisition_plan,
    )

    payload = write_pm_crypto_updown_window_acquisition_plan(
        fixture_root=fixture_root or _repo_default_path(DEFAULT_PM_CRYPTO_UPDOWN_FIXTURE_ROOT),
        real_cached_artifact_roots=_optional_path_list(real_cached_root),
    )
    print(
        {
            "status": payload["capture_or_import_status"],
            "current_primary_row_count": payload["current_primary_row_count"],
            "current_real_cached_row_count": payload["current_real_cached_row_count"],
            "row_gap": payload["row_gap"],
            "required_remaining_two_token_windows": payload[
                "required_remaining_two_token_windows"
            ],
            "report": "reports/sequence41/window_acquisition/latest_window_acquisition_plan.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("pm-crypto-updown-manual-capture-plan")
def research_pm_crypto_updown_manual_capture_plan() -> None:
    from quant_os.data.prediction_markets.pm_updown_capture_plan import (
        write_pm_updown_manual_capture_plan,
    )

    payload = write_pm_updown_manual_capture_plan()
    print(
        {
            "status": "MANUAL_CAPTURE_PLAN_READY",
            "manual_only": payload["manual_only"],
            "network_enabled": payload["network_enabled"],
            "report": "reports/sequence38/manual_capture/latest_manual_capture_plan.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("pm-crypto-updown-expanded-dataset")
def research_pm_crypto_updown_expanded_dataset(
    fixture_root: Annotated[Path | None, typer.Option("--fixture-root")] = None,
) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_dataset_builder import (
        write_pm_crypto_updown_expanded_dataset_report,
    )

    payload = write_pm_crypto_updown_expanded_dataset_report(
        fixture_root=fixture_root or _repo_default_path(DEFAULT_PM_CRYPTO_UPDOWN_FIXTURE_ROOT),
    )
    print(
        {
            "status": "EXPANDED_DATASET_BUILT",
            "row_count": payload["row_count"],
            "primary_evidence_row_count": payload["primary_evidence_row_count"],
            "report": "reports/sequence38/expanded_dataset/latest_pm_crypto_updown_expanded_dataset.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("pm-crypto-updown-evidence-quality")
def research_pm_crypto_updown_evidence_quality(
    fixture_root: Annotated[Path | None, typer.Option("--fixture-root")] = None,
) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_evidence_quality import (
        write_pm_crypto_updown_evidence_quality_report,
    )

    payload = write_pm_crypto_updown_evidence_quality_report(
        fixture_root=fixture_root or _repo_default_path(DEFAULT_PM_CRYPTO_UPDOWN_FIXTURE_ROOT),
    )
    print(
        {
            "status": payload["evidence_expansion_status"],
            "primary_evidence_row_count": payload["primary_evidence_row_count"],
            "rows_needed_for_threshold": payload["rows_needed_for_threshold"],
            "report": "reports/sequence38/evidence_quality/latest_pm_crypto_updown_evidence_quality.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("pm-crypto-updown-expanded-replay-eval")
def research_pm_crypto_updown_expanded_replay_eval(
    fixture_root: Annotated[Path | None, typer.Option("--fixture-root")] = None,
) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_expanded_replay_eval import (
        write_pm_crypto_updown_expanded_replay_eval_report,
    )

    payload = write_pm_crypto_updown_expanded_replay_eval_report(
        fixture_root=fixture_root or _repo_default_path(DEFAULT_PM_CRYPTO_UPDOWN_FIXTURE_ROOT),
    )
    print(
        {
            "status": payload["evaluation_status"],
            "primary_evidence_row_count": payload["primary_evidence_row_count"],
            "synthetic_rows_counted_as_primary": payload["synthetic_rows_counted_as_primary"],
            "report": "reports/sequence38/expanded_replay_eval/latest_expanded_replay_eval.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("pm-crypto-updown-threshold-progress")
def research_pm_crypto_updown_threshold_progress(
    fixture_root: Annotated[Path | None, typer.Option("--fixture-root")] = None,
    real_cached_root: Annotated[list[Path] | None, typer.Option("--real-cached-root")] = None,
    sequence41: bool = typer.Option(False, "--sequence41"),
) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_threshold_progress import (
        write_pm_crypto_updown_sequence41_threshold_progress_report,
        write_pm_crypto_updown_threshold_progress_report,
    )

    if sequence41:
        payload = write_pm_crypto_updown_sequence41_threshold_progress_report(
            fixture_root=fixture_root or _repo_default_path(DEFAULT_PM_CRYPTO_UPDOWN_FIXTURE_ROOT),
            real_cached_artifact_roots=_optional_path_list(real_cached_root),
        )
        report_path = "reports/sequence41/threshold_progress/latest_threshold_progress.json"
    else:
        payload = write_pm_crypto_updown_threshold_progress_report(
            fixture_root=fixture_root or _repo_default_path(DEFAULT_PM_CRYPTO_UPDOWN_FIXTURE_ROOT),
            real_cached_artifact_roots=_optional_path_list(real_cached_root),
        )
        report_path = "reports/sequence39/threshold_progress/latest_threshold_progress.json"
    print(
        {
            "status": payload["threshold_status"],
            "readiness_status": payload["readiness_status"],
            "current_primary_row_count": payload["current_primary_row_count"],
            "current_real_cached_row_count": payload["current_real_cached_row_count"],
            "row_gap": payload["row_gap"],
            "report": report_path,
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("pm-crypto-updown-real-cached-replay-eval")
def research_pm_crypto_updown_real_cached_replay_eval(
    fixture_root: Annotated[Path | None, typer.Option("--fixture-root")] = None,
    real_cached_root: Annotated[list[Path] | None, typer.Option("--real-cached-root")] = None,
    sequence41: bool = typer.Option(False, "--sequence41"),
) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_real_cached_replay_eval import (
        write_pm_crypto_updown_real_cached_replay_eval_report,
        write_pm_crypto_updown_sequence41_replay_eval_report,
    )

    if sequence41:
        payload = write_pm_crypto_updown_sequence41_replay_eval_report(
            fixture_root=fixture_root or _repo_default_path(DEFAULT_PM_CRYPTO_UPDOWN_FIXTURE_ROOT),
            real_cached_artifact_roots=_optional_path_list(real_cached_root),
        )
        report_path = "reports/sequence41/replay_eval/latest_pm_crypto_updown_replay_eval.json"
    else:
        payload = write_pm_crypto_updown_real_cached_replay_eval_report(
            fixture_root=fixture_root or _repo_default_path(DEFAULT_PM_CRYPTO_UPDOWN_FIXTURE_ROOT),
            real_cached_artifact_roots=_optional_path_list(real_cached_root),
        )
        report_path = "reports/sequence39/real_cached_replay_eval/latest_real_cached_replay_eval.json"
    print(
        {
            "status": payload["evaluation_status"],
            "primary_evidence_row_count": payload["primary_evidence_row_count"],
            "real_cached_replay_ready_row_count": payload[
                "real_cached_replay_ready_row_count"
            ],
            "synthetic_rows_counted_as_primary": payload[
                "synthetic_rows_counted_as_primary"
            ],
            "report": report_path,
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("pm-crypto-updown-fill-blockers")
def research_pm_crypto_updown_fill_blockers(
    fixture_root: Annotated[Path | None, typer.Option("--fixture-root")] = None,
    real_cached_root: Annotated[list[Path] | None, typer.Option("--real-cached-root")] = None,
) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_dataset_builder import (
        build_pm_crypto_updown_expanded_dataset,
    )
    from quant_os.research.replay_candidates.pm_crypto_updown_fill_blocker_report import (
        write_pm_crypto_updown_fill_blocker_attribution_report,
    )
    from quant_os.research.replay_candidates.pm_crypto_updown_signals import (
        score_pm_crypto_updown_signals,
    )

    dataset = build_pm_crypto_updown_expanded_dataset(
        fixture_root=fixture_root or _repo_default_path(DEFAULT_PM_CRYPTO_UPDOWN_FIXTURE_ROOT),
        real_cached_artifact_roots=_optional_path_list(real_cached_root),
    )
    signals = score_pm_crypto_updown_signals(dataset["rows"])
    payload = write_pm_crypto_updown_fill_blocker_attribution_report(
        rows=dataset["rows"],
        signal_report=signals,
    )
    print(
        {
            "status": (
                "FILL_BLOCKERS_ATTRIBUTED"
                if payload["blocked_row_count"]
                else "NO_FILL_BLOCKERS_FOUND"
            ),
            "blocked_row_count": payload["blocked_row_count"],
            "potentially_tradeable_row_count": payload["potentially_tradeable_row_count"],
            "report": "reports/sequence43/fill_blockers/latest_fill_blocker_attribution.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("pm-crypto-updown-shadow-policy")
def research_pm_crypto_updown_shadow_policy(
    fixture_root: Annotated[Path | None, typer.Option("--fixture-root")] = None,
    real_cached_root: Annotated[list[Path] | None, typer.Option("--real-cached-root")] = None,
) -> None:
    from quant_os.execution.pm_crypto_updown_shadow_policy import (
        write_pm_crypto_updown_shadow_policy_report,
    )
    from quant_os.research.replay_candidates.pm_crypto_updown_dataset_builder import (
        build_pm_crypto_updown_expanded_dataset,
    )
    from quant_os.research.replay_candidates.pm_crypto_updown_signals import (
        score_pm_crypto_updown_signals,
    )

    dataset = build_pm_crypto_updown_expanded_dataset(
        fixture_root=fixture_root or _repo_default_path(DEFAULT_PM_CRYPTO_UPDOWN_FIXTURE_ROOT),
        real_cached_artifact_roots=_optional_path_list(real_cached_root),
    )
    signals = score_pm_crypto_updown_signals(dataset["rows"])
    payload = write_pm_crypto_updown_shadow_policy_report(
        rows=dataset["rows"],
        signal_report=signals,
    )
    print(
        {
            "status": "OFFLINE_SHADOW_POLICY_WRITTEN",
            "allowed_intent_count": payload["allowed_intent_count"],
            "blocked_intent_count": payload["blocked_intent_count"],
            "report": "reports/sequence43/shadow_policy/latest_pm_crypto_updown_shadow_policy.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("pm-crypto-updown-policy-replay-eval")
def research_pm_crypto_updown_policy_replay_eval(
    fixture_root: Annotated[Path | None, typer.Option("--fixture-root")] = None,
    real_cached_root: Annotated[list[Path] | None, typer.Option("--real-cached-root")] = None,
) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_policy_replay_eval import (
        write_pm_crypto_updown_policy_replay_eval_report,
    )

    payload = write_pm_crypto_updown_policy_replay_eval_report(
        fixture_root=fixture_root or _repo_default_path(DEFAULT_PM_CRYPTO_UPDOWN_FIXTURE_ROOT),
        real_cached_artifact_roots=_optional_path_list(real_cached_root),
    )
    print(
        {
            "status": payload["evaluation_status"],
            "allowed_intent_count": payload["allowed_intent_count"],
            "primary_allowed_intent_count": payload["primary_allowed_intent_count"],
            "cost_fill_realism_still_blocks": payload["policy_answers"][
                "cost_fill_realism_still_blocks"
            ],
            "report": "reports/sequence43/policy_replay_eval/latest_policy_replay_eval.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("pm-crypto-updown-allowed-intent-diagnostics")
def research_pm_crypto_updown_allowed_intent_diagnostics(
    fixture_root: Annotated[Path | None, typer.Option("--fixture-root")] = None,
    real_cached_root: Annotated[list[Path] | None, typer.Option("--real-cached-root")] = None,
) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_allowed_intent_report import (
        write_pm_crypto_updown_allowed_intent_diagnostics_report,
    )

    payload = write_pm_crypto_updown_allowed_intent_diagnostics_report(
        fixture_root=fixture_root or _repo_default_path(DEFAULT_PM_CRYPTO_UPDOWN_FIXTURE_ROOT),
        real_cached_artifact_roots=_optional_path_list(real_cached_root),
    )
    print(
        {
            "status": payload["active_blocker"],
            "allowed_primary_intent_count": payload["allowed_primary_intent_count"],
            "allowed_real_cached_intent_count": payload["allowed_real_cached_intent_count"],
            "allowed_synthetic_diagnostic_intent_count": payload[
                "allowed_synthetic_diagnostic_intent_count"
            ],
            "report": "reports/sequence44/allowed_intent_diagnostics/latest_allowed_intent_diagnostics.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("pm-crypto-updown-discriminators")
def research_pm_crypto_updown_discriminators(
    fixture_root: Annotated[Path | None, typer.Option("--fixture-root")] = None,
    real_cached_root: Annotated[list[Path] | None, typer.Option("--real-cached-root")] = None,
) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_allowed_intent_diagnostics import (
        evaluate_pm_crypto_updown_allowed_intent_diagnostics,
    )
    from quant_os.research.replay_candidates.pm_crypto_updown_discriminators import (
        evaluate_pm_crypto_updown_discriminators,
    )

    diagnostics = evaluate_pm_crypto_updown_allowed_intent_diagnostics(
        fixture_root=fixture_root or _repo_default_path(DEFAULT_PM_CRYPTO_UPDOWN_FIXTURE_ROOT),
        real_cached_artifact_roots=_optional_path_list(real_cached_root),
    )
    payload = evaluate_pm_crypto_updown_discriminators(diagnostics=diagnostics)
    print(
        {
            "status": "DISCRIMINATORS_EVALUATED",
            "input_allowed_primary_count": payload["input_allowed_primary_count"],
            "discriminator_count": len(payload["discriminators"]),
            "diagnostic_only_count": sum(
                1 for item in payload["discriminators"] if item["diagnostic_only"]
            ),
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("pm-crypto-updown-baseline-placebo-attribution")
def research_pm_crypto_updown_baseline_placebo_attribution(
    fixture_root: Annotated[Path | None, typer.Option("--fixture-root")] = None,
    real_cached_root: Annotated[list[Path] | None, typer.Option("--real-cached-root")] = None,
) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_allowed_intent_diagnostics import (
        evaluate_pm_crypto_updown_allowed_intent_diagnostics,
    )
    from quant_os.research.replay_candidates.pm_crypto_updown_baseline_placebo_attribution import (
        write_pm_crypto_updown_baseline_placebo_attribution_report,
    )

    diagnostics = evaluate_pm_crypto_updown_allowed_intent_diagnostics(
        fixture_root=fixture_root or _repo_default_path(DEFAULT_PM_CRYPTO_UPDOWN_FIXTURE_ROOT),
        real_cached_artifact_roots=_optional_path_list(real_cached_root),
    )
    payload = write_pm_crypto_updown_baseline_placebo_attribution_report(
        diagnostics=diagnostics,
    )
    print(
        {
            "status": payload["active_blocker"],
            "market_baseline_dominant": payload["market_baseline_dominant"],
            "additional_allowed_primary_intents_required": payload[
                "additional_allowed_primary_intents_required"
            ],
            "report": "reports/sequence44/baseline_placebo_attribution/latest_baseline_placebo_attribution.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("pm-crypto-updown-allowed-intent-acquisition")
def research_pm_crypto_updown_allowed_intent_acquisition(
    fixture_root: Annotated[Path | None, typer.Option("--fixture-root")] = None,
    real_cached_root: Annotated[list[Path] | None, typer.Option("--real-cached-root")] = None,
) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_allowed_intent_acquisition import (
        write_pm_crypto_updown_allowed_intent_acquisition_plan,
    )

    payload = write_pm_crypto_updown_allowed_intent_acquisition_plan(
        fixture_root=fixture_root or _repo_default_path(DEFAULT_PM_CRYPTO_UPDOWN_FIXTURE_ROOT),
        real_cached_artifact_roots=_optional_path_list(real_cached_root),
    )
    print(
        {
            "status": payload["capture_or_import_status"],
            "required_additional_allowed_primary_intents": payload[
                "required_additional_allowed_primary_intents"
            ],
            "required_additional_allowed_real_cached_intents": payload[
                "required_additional_allowed_real_cached_intents"
            ],
            "estimated_additional_two_token_windows_required": payload[
                "estimated_additional_two_token_windows_required"
            ],
            "report": "reports/sequence45/allowed_intent_acquisition/latest_allowed_intent_acquisition_plan.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("pm-crypto-updown-allowed-intent-progress")
def research_pm_crypto_updown_allowed_intent_progress(
    fixture_root: Annotated[Path | None, typer.Option("--fixture-root")] = None,
    real_cached_root: Annotated[list[Path] | None, typer.Option("--real-cached-root")] = None,
) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_allowed_intent_progress import (
        write_pm_crypto_updown_allowed_intent_progress_report,
    )

    payload = write_pm_crypto_updown_allowed_intent_progress_report(
        fixture_root=fixture_root or _repo_default_path(DEFAULT_PM_CRYPTO_UPDOWN_FIXTURE_ROOT),
        real_cached_artifact_roots=_optional_path_list(real_cached_root),
    )
    print(
        {
            "status": payload["progress_status"],
            "new_allowed_primary_intents": payload["new_allowed_primary_intents"],
            "new_allowed_real_cached_intents": payload["new_allowed_real_cached_intents"],
            "current_allowed_primary_intents": payload["current_allowed_primary_intents"],
            "current_allowed_real_cached_intents": payload[
                "current_allowed_real_cached_intents"
            ],
            "report": "reports/sequence45/allowed_intent_progress/latest_allowed_intent_progress.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("pm-crypto-updown-discriminator-update")
def research_pm_crypto_updown_discriminator_update(
    fixture_root: Annotated[Path | None, typer.Option("--fixture-root")] = None,
    real_cached_root: Annotated[list[Path] | None, typer.Option("--real-cached-root")] = None,
) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_allowed_intent_progress import (
        write_pm_crypto_updown_discriminator_update_report,
    )

    payload = write_pm_crypto_updown_discriminator_update_report(
        fixture_root=fixture_root or _repo_default_path(DEFAULT_PM_CRYPTO_UPDOWN_FIXTURE_ROOT),
        real_cached_artifact_roots=_optional_path_list(real_cached_root),
    )
    print(
        {
            "status": payload["update_status"],
            "input_allowed_primary_count": payload["input_allowed_primary_count"],
            "discriminator_count": len(payload["discriminators"]),
            "report": "reports/sequence45/discriminators/latest_discriminator_update.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("pm-crypto-updown-overfit-guard-update")
def research_pm_crypto_updown_overfit_guard_update(
    fixture_root: Annotated[Path | None, typer.Option("--fixture-root")] = None,
    real_cached_root: Annotated[list[Path] | None, typer.Option("--real-cached-root")] = None,
) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_allowed_intent_progress import (
        write_pm_crypto_updown_overfit_guard_update_report,
    )

    payload = write_pm_crypto_updown_overfit_guard_update_report(
        fixture_root=fixture_root or _repo_default_path(DEFAULT_PM_CRYPTO_UPDOWN_FIXTURE_ROOT),
        real_cached_artifact_roots=_optional_path_list(real_cached_root),
    )
    print(
        {
            "status": payload["status"],
            "passes": payload["passes"],
            "blockers": payload["blockers"],
            "report": "reports/sequence45/overfit_guard/latest_overfit_guard_update.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("pm-crypto-updown-baseline-placebo-update")
def research_pm_crypto_updown_baseline_placebo_update(
    fixture_root: Annotated[Path | None, typer.Option("--fixture-root")] = None,
    real_cached_root: Annotated[list[Path] | None, typer.Option("--real-cached-root")] = None,
) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_allowed_intent_progress import (
        write_pm_crypto_updown_baseline_placebo_update_report,
    )

    payload = write_pm_crypto_updown_baseline_placebo_update_report(
        fixture_root=fixture_root or _repo_default_path(DEFAULT_PM_CRYPTO_UPDOWN_FIXTURE_ROOT),
        real_cached_artifact_roots=_optional_path_list(real_cached_root),
    )
    print(
        {
            "status": payload["active_blocker"],
            "candidate_beats_market_baseline": payload["candidate_beats_market_baseline"],
            "candidate_beats_no_skill_baseline": payload["candidate_beats_no_skill_baseline"],
            "candidate_beats_or_separates_from_placebos": payload[
                "candidate_beats_or_separates_from_placebos"
            ],
            "report": "reports/sequence45/baseline_placebo/latest_baseline_placebo_update.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("pm-crypto-updown-phase45-reference-notes")
def research_pm_crypto_updown_phase45_reference_notes() -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_phase45_notes import (
        write_pm_crypto_updown_phase45_reference_notes,
    )

    payload = write_pm_crypto_updown_phase45_reference_notes()
    print(
        {
            "status": "REFERENCE_NOTES_WRITTEN",
            "candidate_backlog_families": payload["candidate_backlog_families"],
            "report": "reports/sequence45/reference_notes/latest_phase45_reference_notes.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("pm-crypto-updown-phase46-capture-pass")
def research_pm_crypto_updown_phase46_capture_pass(
    run_id: str = typer.Option("pm_crypto_updown_manual_046", "--run-id"),
    fixture_root: Annotated[Path | None, typer.Option("--fixture-root")] = None,
    real_cached_root: Annotated[list[Path] | None, typer.Option("--real-cached-root")] = None,
) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_allowed_intent_capture_pass import (
        DEFAULT_CAPTURE_ROOT,
        write_pm_crypto_updown_allowed_intent_capture_pass_report,
        write_pm_crypto_updown_phase46_allowed_intent_progress_report,
        write_pm_crypto_updown_phase46_baseline_placebo_update_report,
        write_pm_crypto_updown_phase46_discriminator_update_report,
        write_pm_crypto_updown_phase46_overfit_guard_update_report,
    )

    capture_root = DEFAULT_CAPTURE_ROOT / run_id
    baseline_roots = _optional_path_list(real_cached_root)
    all_roots = baseline_roots + [capture_root]
    payload = write_pm_crypto_updown_allowed_intent_capture_pass_report(
        run_id=run_id,
        capture_run_root=capture_root,
        baseline_real_cached_artifact_roots=baseline_roots,
        fixture_root=fixture_root or _repo_default_path(DEFAULT_PM_CRYPTO_UPDOWN_FIXTURE_ROOT),
    )
    write_pm_crypto_updown_phase46_allowed_intent_progress_report(
        fixture_root=fixture_root or _repo_default_path(DEFAULT_PM_CRYPTO_UPDOWN_FIXTURE_ROOT),
        real_cached_artifact_roots=all_roots,
    )
    write_pm_crypto_updown_phase46_discriminator_update_report(
        fixture_root=fixture_root or _repo_default_path(DEFAULT_PM_CRYPTO_UPDOWN_FIXTURE_ROOT),
        real_cached_artifact_roots=all_roots,
    )
    write_pm_crypto_updown_phase46_overfit_guard_update_report(
        fixture_root=fixture_root or _repo_default_path(DEFAULT_PM_CRYPTO_UPDOWN_FIXTURE_ROOT),
        real_cached_artifact_roots=all_roots,
    )
    write_pm_crypto_updown_phase46_baseline_placebo_update_report(
        fixture_root=fixture_root or _repo_default_path(DEFAULT_PM_CRYPTO_UPDOWN_FIXTURE_ROOT),
        real_cached_artifact_roots=all_roots,
    )
    print(
        {
            "status": payload["blocker_after"],
            "capture_attempted": payload["capture_attempted"],
            "artifacts_accepted": payload["artifacts_accepted"],
            "allowed_primary_intents_before": payload["allowed_primary_intents_before"],
            "allowed_primary_intents_after": payload["allowed_primary_intents_after"],
            "allowed_real_cached_intents_before": payload[
                "allowed_real_cached_intents_before"
            ],
            "allowed_real_cached_intents_after": payload[
                "allowed_real_cached_intents_after"
            ],
            "report": "reports/sequence46/allowed_intent_capture/latest_allowed_intent_capture_pass.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("pm-lp-refresh-lag-candidate-pack")
def research_pm_lp_refresh_lag_candidate_pack() -> None:
    from quant_os.research.replay_candidates.pm_lp_refresh_lag_candidate_pack import (
        write_pm_lp_refresh_lag_candidate_pack_report,
    )

    payload = write_pm_lp_refresh_lag_candidate_pack_report()
    print(
        {
            "status": payload["candidate_readiness_status"],
            "candidate_id": payload["candidate_id"],
            "report": "reports/sequence47/candidate_pack/latest_candidate_pack.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("pm-lp-refresh-lag-replay-schema")
def research_pm_lp_refresh_lag_replay_schema() -> None:
    from quant_os.research.replay_candidates.pm_lp_refresh_lag_schema import (
        build_pm_lp_refresh_lag_replay_schema,
    )

    payload = build_pm_lp_refresh_lag_replay_schema()
    print(
        {
            "status": "REPLAY_SCHEMA_DEFINED",
            "candidate_id": payload["candidate_id"],
            "event_type": payload["event_type"],
            "live_trading_enabled": False,
            "execution_authority": payload["safety"]["execution_authority"],
        }
    )


@research_app.command("pm-lp-refresh-lag-source-policy")
def research_pm_lp_refresh_lag_source_policy() -> None:
    from quant_os.research.replay_candidates.pm_lp_refresh_lag_source_policy import (
        write_pm_lp_refresh_lag_source_policy_report,
    )

    payload = write_pm_lp_refresh_lag_source_policy_report()
    print(
        {
            "status": payload["policy_status"],
            "allowed_source_count": len(payload["allowed_sources"]),
            "blocked_source_count": len(payload["blocked_sources"]),
            "report": "reports/sequence47/source_policy/latest_source_policy.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("pm-lp-refresh-lag-source-feasibility")
def research_pm_lp_refresh_lag_source_feasibility() -> None:
    from quant_os.research.replay_candidates.pm_lp_refresh_lag_source_feasibility import (
        write_pm_lp_refresh_lag_source_feasibility_report,
    )

    payload = write_pm_lp_refresh_lag_source_feasibility_report()
    print(
        {
            "status": payload["feasibility_status"],
            "active_blocker": payload["active_blocker"],
            "public_source_acquisition_ready": payload["public_source_acquisition_ready"],
            "report": ("reports/sequence48/source_feasibility/latest_source_feasibility.json"),
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("prediction-market-quality")
def research_prediction_market_quality(
    fixture_path: Annotated[Path | None, typer.Option("--fixture-path")] = None,
) -> None:
    payload = write_market_quality_report(fixture_path=fixture_path or DEFAULT_POLYMARKET_FIXTURE)
    print(
        {
            "status": "PASS",
            "market_count": payload["market_count"],
            "researchable_count": payload["summary"]["researchable_count"],
            "source_mode": payload["source_mode"],
            "report": "reports/sequence20/market_quality/latest_market_quality.json",
            "live_trading_enabled": False,
        }
    )


@research_app.command("prediction-market-wallet-report")
def research_prediction_market_wallet_report(
    activity_fixture_path: Annotated[Path | None, typer.Option("--activity-fixture-path")] = None,
    market_fixture_path: Annotated[Path | None, typer.Option("--market-fixture-path")] = None,
) -> None:
    payload = write_wallet_research_report(
        activity_fixture_path=activity_fixture_path or DEFAULT_POLYMARKET_WALLET_FIXTURE,
        market_fixture_path=market_fixture_path or DEFAULT_POLYMARKET_FIXTURE,
    )
    print(
        {
            "status": "PASS",
            "wallet_count": payload["observed_facts"]["wallet_count"],
            "activity_count": payload["observed_facts"]["activity_count"],
            "source_mode": payload["source_mode"],
            "execution_authority": payload["execution_authority"],
            "copy_trading_enabled": payload["copy_trading_enabled"],
            "report": "reports/sequence20/wallet_research/latest_wallet_research.json",
            "live_trading_enabled": False,
        }
    )


@research_app.command("prediction-market-priority")
def research_prediction_market_priority(
    fixture_path: Annotated[Path | None, typer.Option("--fixture-path")] = None,
) -> None:
    path = fixture_path or DEFAULT_POLYMARKET_FIXTURE
    inventory = write_market_inventory_report(fixture_path=path)
    priority = write_research_priority_report(fixture_path=path)
    print(
        {
            "status": priority["status"],
            "inventory_market_count": inventory["market_count"],
            "candidate_lane_count": len(priority["top_candidate_research_lanes"]),
            "source_mode": priority["source_mode"],
            "inventory_report": "reports/sequence20/market_inventory/latest_market_inventory.json",
            "priority_report": "reports/sequence20/research_priority/latest_research_priority.json",
            "live_trading_enabled": False,
        }
    )


@research_app.command("prediction-history-build")
def research_prediction_history_build(
    fixture_path: Annotated[Path | None, typer.Option("--fixture-path")] = None,
) -> None:
    payload = write_prediction_historical_dataset_report(
        fixture_path=fixture_path or DEFAULT_POLYMARKET_HISTORY_FIXTURE,
    )
    print(
        {
            "status": payload["research_readiness_status"],
            "dataset_id": payload["dataset_id"],
            "market_count": payload["market_count"],
            "resolved_count": payload["resolution_summary"]["resolved_count"],
            "ready_for_replay_design": payload["ready_for_replay_design"],
            "report": "reports/sequence21/dataset/latest_dataset_summary.json",
            "live_trading_enabled": False,
        }
    )


@research_app.command("prediction-feature-report")
def research_prediction_feature_report(
    fixture_path: Annotated[Path | None, typer.Option("--fixture-path")] = None,
) -> None:
    payload = write_prediction_feature_report(
        fixture_path=fixture_path or DEFAULT_POLYMARKET_HISTORY_FIXTURE,
    )
    print(
        {
            "status": "RESEARCH_ONLY",
            "feature_count": payload["feature_count"],
            "source_mode": payload["source_mode"],
            "report": "reports/sequence21/features/latest_prediction_features.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("prediction-candidate-report")
def research_prediction_candidate_report(
    fixture_path: Annotated[Path | None, typer.Option("--fixture-path")] = None,
) -> None:
    payload = write_prediction_candidate_report(
        fixture_path=fixture_path or DEFAULT_POLYMARKET_HISTORY_FIXTURE,
    )
    print(
        {
            "status": payload["research_readiness_status"],
            "feature_count": payload["feature_count"],
            "resolved_observation_count": payload["metrics"]["resolved_observation_count"],
            "ready_for_replay_design": payload["ready_for_replay_design"],
            "blockers": payload["blockers"],
            "report": "reports/sequence21/prediction_candidates/latest_prediction_candidates.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("prediction-history-expand")
def research_prediction_history_expand(
    fixture_path: Annotated[Path | None, typer.Option("--fixture-path")] = None,
    previous_fixture_path: Annotated[Path | None, typer.Option("--previous-fixture-path")] = None,
) -> None:
    path = fixture_path or DEFAULT_POLYMARKET_EXPANDED_HISTORY_FIXTURE
    previous_path = previous_fixture_path or DEFAULT_POLYMARKET_HISTORY_FIXTURE
    dataset = write_expanded_historical_dataset_report(fixture_path=path)
    growth = write_dataset_growth_report(
        previous_fixture_path=previous_path,
        expanded_fixture_path=path,
    )
    print(
        {
            "status": dataset["research_dataset_status"],
            "dataset_id": dataset["dataset_id"],
            "dataset_hash": dataset["dataset_hash"],
            "market_count": dataset["market_count"],
            "resolved_count": dataset["resolution_summary"]["resolved_count"],
            "market_delta": growth["market_delta"],
            "resolved_delta": growth["resolved_delta"],
            "dataset_report": "reports/sequence22/dataset/latest_dataset_summary.json",
            "growth_report": "reports/sequence22/dataset/latest_dataset_growth.json",
            "live_trading_enabled": False,
            "execution_authority": dataset["execution_authority"],
        }
    )


@research_app.command("prediction-candidate-eval")
def research_prediction_candidate_eval(
    fixture_path: Annotated[Path | None, typer.Option("--fixture-path")] = None,
) -> None:
    payload = write_prediction_candidate_evaluation_report(
        fixture_path=fixture_path or DEFAULT_POLYMARKET_EXPANDED_HISTORY_FIXTURE,
    )
    print(
        {
            "status": payload["candidate_evaluation_status"],
            "feature_count": payload["feature_count"],
            "resolved_observation_count": payload["metrics"]["resolved_observation_count"],
            "report": "reports/sequence22/prediction_candidates/latest_prediction_candidate_eval.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("prediction-lane-selection")
def research_prediction_lane_selection(
    fixture_path: Annotated[Path | None, typer.Option("--fixture-path")] = None,
) -> None:
    path = fixture_path or DEFAULT_POLYMARKET_SIGNAL_DISCOVERY_FIXTURE
    dataset = write_signal_discovery_dataset_report(fixture_path=path)
    strata = write_market_strata_report(fixture_path=path)
    lanes = write_lane_selection_report(fixture_path=path)
    print(
        {
            "status": "RESEARCH_ONLY",
            "dataset_id": dataset["dataset_id"],
            "market_count": dataset["market_count"],
            "stratified_market_count": strata["summary"]["market_count"],
            "best_lane": lanes["best_lane"]["lane_id"] if lanes["best_lane"] else None,
            "lane_count": lanes["lane_count"],
            "dataset_report": "reports/sequence23/dataset/latest_dataset_summary.json",
            "strata_report": "reports/sequence23/dataset/latest_market_strata.json",
            "lane_report": "reports/sequence23/lane_selection/latest_lane_selection.json",
            "live_trading_enabled": False,
            "execution_authority": lanes["execution_authority"],
        }
    )


@research_app.command("prediction-signal-report")
def research_prediction_signal_report() -> None:
    payload = write_signal_family_report()
    print(
        {
            "status": "RESEARCH_ONLY",
            "signal_family_count": payload["signal_family_count"],
            "report": "reports/sequence23/prediction_candidates/latest_signal_families.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("prediction-lane-eval")
def research_prediction_lane_eval(
    fixture_path: Annotated[Path | None, typer.Option("--fixture-path")] = None,
) -> None:
    payload = write_lane_evaluation_report(
        fixture_path=fixture_path or DEFAULT_POLYMARKET_SIGNAL_DISCOVERY_FIXTURE,
    )
    print(
        {
            "status": payload["lane_evaluation_status"],
            "best_lane": payload["best_lane_evaluation"]["lane_id"],
            "signal_families_tested": payload["signal_families_tested"],
            "lane_report": "reports/sequence23/lane_evaluation/latest_lane_evaluation.json",
            "candidate_report": "reports/sequence23/prediction_candidates/latest_prediction_candidates.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("replay-feasibility")
def research_replay_feasibility(
    fixture_path: Annotated[Path | None, typer.Option("--fixture-path")] = None,
    lane_aware: bool = typer.Option(False, "--lane-aware"),
) -> None:
    if lane_aware:
        payload = write_replay_precondition_report(
            fixture_path=fixture_path or DEFAULT_POLYMARKET_SIGNAL_DISCOVERY_FIXTURE,
        )
        print(
            {
                "status": payload["replay_precondition_status"],
                "ready_for_narrow_replay_design": payload["ready_for_narrow_replay_design"],
                "blockers": payload["blockers"],
                "report": "reports/sequence23/replay_preconditions/latest_replay_preconditions.json",
                "live_trading_enabled": False,
                "execution_authority": payload["execution_authority"],
            }
        )
        return
    payload = write_replay_feasibility_report(
        fixture_path=fixture_path or DEFAULT_POLYMARKET_EXPANDED_HISTORY_FIXTURE,
    )
    print(
        {
            "status": payload["replay_feasibility_status"],
            "ready_for_narrow_replay_design": payload["ready_for_narrow_replay_design"],
            "blockers": payload["blockers"],
            "report": "reports/sequence22/replay_feasibility/latest_replay_feasibility.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("lane-activity-build")
def research_lane_activity_build(
    fixture_path: Annotated[Path | None, typer.Option("--fixture-path")] = None,
) -> None:
    path = fixture_path or DEFAULT_POLYMARKET_LANE_ACTIVITY_FIXTURE
    dataset = write_lane_activity_dataset_report(fixture_path=path)
    timeline = write_lane_timeline_summary_report(fixture_path=path)
    print(
        {
            "status": dataset["research_dataset_status"],
            "lane_id": dataset["lane_id"],
            "market_count": dataset["market_count"],
            "included_market_count": dataset["included_market_count"],
            "resolved_market_count": dataset["resolved_market_count"],
            "activity_observation_count": dataset["activity_observation_count"],
            "activity_depth_status": dataset["activity_depth_status"],
            "dataset_report": "reports/sequence24/dataset/latest_lane_activity_dataset.json",
            "timeline_report": "reports/sequence24/dataset/latest_lane_timeline_summary.json",
            "live_trading_enabled": False,
            "execution_authority": timeline["execution_authority"],
        }
    )


@research_app.command("dynamic-signal-report")
def research_dynamic_signal_report(
    fixture_path: Annotated[Path | None, typer.Option("--fixture-path")] = None,
) -> None:
    payload = write_dynamic_signal_report(
        fixture_path=fixture_path or DEFAULT_POLYMARKET_LANE_ACTIVITY_FIXTURE,
    )
    print(
        {
            "status": "RESEARCH_ONLY",
            "lane_id": payload["lane_id"],
            "feature_count": payload["feature_count"],
            "signal_family_count": payload["signal_family_count"],
            "report": "reports/sequence24/signal_reports/latest_signal_reports.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("wallet-flow-report")
def research_wallet_flow_report(
    fixture_path: Annotated[Path | None, typer.Option("--fixture-path")] = None,
) -> None:
    payload = write_wallet_flow_report(
        fixture_path=fixture_path or DEFAULT_POLYMARKET_LANE_ACTIVITY_FIXTURE,
    )
    print(
        {
            "status": "RESEARCH_ONLY",
            "lane_id": payload["lane_id"],
            "market_count": payload["market_count"],
            "report": "reports/sequence24/signal_reports/latest_wallet_flow_features.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
            "copy_trading_enabled": payload["copy_trading_enabled"],
        }
    )


@research_app.command("lane-replay-readiness")
def research_lane_replay_readiness(
    fixture_path: Annotated[Path | None, typer.Option("--fixture-path")] = None,
) -> None:
    path = fixture_path or DEFAULT_POLYMARKET_LANE_ACTIVITY_FIXTURE
    lane_evaluation = write_lane_activity_evaluation_report(fixture_path=path)
    readiness = write_lane_replay_readiness_report(fixture_path=path)
    print(
        {
            "status": readiness["replay_readiness_status"],
            "lane_evaluation_status": lane_evaluation["lane_evaluation_status"],
            "ready_for_narrow_replay_design": readiness["ready_for_narrow_replay_design"],
            "blockers": readiness["blockers"],
            "lane_report": "reports/sequence24/lane_evaluation/latest_lane_evaluation.json",
            "readiness_report": "reports/sequence24/replay_readiness/latest_replay_readiness.json",
            "live_trading_enabled": False,
            "execution_authority": readiness["execution_authority"],
        }
    )


@research_app.command("lane-activity-dataset")
def research_lane_activity_dataset(
    fixture_path: Annotated[Path | None, typer.Option("--fixture-path")] = None,
    previous_fixture_path: Annotated[Path | None, typer.Option("--previous-fixture-path")] = None,
) -> None:
    path = fixture_path or DEFAULT_POLYMARKET_REAL_CACHED_ACTIVITY_FIXTURE
    previous_path = previous_fixture_path or DEFAULT_POLYMARKET_LANE_ACTIVITY_FIXTURE
    dataset = write_sequence25_activity_dataset_report(fixture_path=path)
    growth = write_activity_dataset_growth_report(
        previous_fixture_path=previous_path,
        expanded_fixture_path=path,
    )
    print(
        {
            "status": dataset["research_dataset_status"],
            "source_mode": dataset["source_mode"],
            "lane_id": dataset["lane_id"],
            "market_count": dataset["market_count"],
            "resolved_market_count": dataset["resolved_market_count"],
            "activity_observation_count": dataset["activity_observation_count"],
            "market_delta": growth["market_delta"],
            "resolved_delta": growth["resolved_delta"],
            "dataset_report": "reports/sequence25/dataset/latest_activity_dataset.json",
            "growth_report": "reports/sequence25/dataset/latest_activity_growth.json",
            "live_trading_enabled": False,
            "execution_authority": dataset["execution_authority"],
        }
    )


@research_app.command("lane-activity-quality")
def research_lane_activity_quality(
    fixture_path: Annotated[Path | None, typer.Option("--fixture-path")] = None,
) -> None:
    payload = write_lane_activity_quality_report(
        fixture_path=fixture_path or DEFAULT_POLYMARKET_REAL_CACHED_ACTIVITY_FIXTURE,
    )
    print(
        {
            "status": payload["activity_quality_status"],
            "source_mode": payload["source_mode"],
            "lane_id": payload["lane_id"],
            "warnings": payload["warnings"],
            "report": "reports/sequence25/dataset/latest_activity_quality.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("activity-signal-evaluation")
def research_activity_signal_evaluation(
    fixture_path: Annotated[Path | None, typer.Option("--fixture-path")] = None,
) -> None:
    payload = write_real_activity_signal_evaluation_report(
        fixture_path=fixture_path or DEFAULT_POLYMARKET_REAL_CACHED_ACTIVITY_FIXTURE,
    )
    print(
        {
            "status": payload["lane_evaluation_status"],
            "source_mode": payload["source_mode"],
            "lane_id": payload["lane_id"],
            "resolved_observation_count": payload["resolved_observation_count"],
            "report": "reports/sequence25/signal_evaluation/latest_signal_evaluation.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("real-activity-replay-readiness")
def research_real_activity_replay_readiness(
    fixture_path: Annotated[Path | None, typer.Option("--fixture-path")] = None,
) -> None:
    payload = write_real_activity_replay_readiness_report(
        fixture_path=fixture_path or DEFAULT_POLYMARKET_REAL_CACHED_ACTIVITY_FIXTURE,
    )
    print(
        {
            "status": payload["replay_readiness_status"],
            "source_mode": payload["source_mode"],
            "ready_for_narrow_replay_design": payload["ready_for_narrow_replay_design"],
            "blockers": payload["blockers"],
            "report": "reports/sequence25/replay_readiness/latest_replay_readiness.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("resolved-history-growth")
def research_resolved_history_growth(
    fixture_path: Annotated[Path | None, typer.Option("--fixture-path")] = None,
    previous_fixture_path: Annotated[Path | None, typer.Option("--previous-fixture-path")] = None,
) -> None:
    path = fixture_path or DEFAULT_POLYMARKET_OOS_ACTIVITY_FIXTURE
    previous_path = previous_fixture_path or DEFAULT_POLYMARKET_REAL_CACHED_ACTIVITY_FIXTURE
    dataset = write_sequence26_lane_dataset_summary_report(fixture_path=path)
    growth = write_resolved_history_growth_report(
        previous_fixture_path=previous_path,
        expanded_fixture_path=path,
    )
    print(
        {
            "status": growth["resolved_history_status"],
            "source_mode": growth["source_mode"],
            "lane_id": growth["lane_id"],
            "market_count": dataset["market_count"],
            "resolved_market_count": dataset["resolved_market_count"],
            "market_delta": growth["market_delta"],
            "resolved_delta": growth["resolved_delta"],
            "dataset_report": "reports/sequence26/dataset/latest_lane_dataset_summary.json",
            "growth_report": "reports/sequence26/dataset/latest_resolved_history_growth.json",
            "live_trading_enabled": False,
            "execution_authority": growth["execution_authority"],
        }
    )


@research_app.command("label-quality")
def research_label_quality(
    fixture_path: Annotated[Path | None, typer.Option("--fixture-path")] = None,
) -> None:
    payload = write_label_quality_report(
        fixture_path=fixture_path or DEFAULT_POLYMARKET_OOS_ACTIVITY_FIXTURE,
    )
    print(
        {
            "status": payload["label_quality_status"],
            "lane_id": payload["lane_id"],
            "usable_resolved_label_count": payload["summary"]["usable_resolved_label_count"],
            "warnings": payload["warnings"],
            "report": "reports/sequence26/label_quality/latest_label_quality.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("lane-oos-validation")
def research_lane_oos_validation(
    fixture_path: Annotated[Path | None, typer.Option("--fixture-path")] = None,
) -> None:
    payload = write_lane_oos_validation_report(
        fixture_path=fixture_path or DEFAULT_POLYMARKET_OOS_ACTIVITY_FIXTURE,
    )
    print(
        {
            "status": payload["oos_validation_status"],
            "lane_id": payload["lane_id"],
            "resolved_observation_count": payload["resolved_observation_count"],
            "oos_observation_count": payload["oos_observation_count"],
            "market_baseline_dominant": payload["market_baseline_dominant"],
            "report": "reports/sequence26/oos_validation/latest_oos_validation.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("lane-robustness")
def research_lane_robustness(
    fixture_path: Annotated[Path | None, typer.Option("--fixture-path")] = None,
) -> None:
    payload = write_lane_robustness_report(
        fixture_path=fixture_path or DEFAULT_POLYMARKET_OOS_ACTIVITY_FIXTURE,
    )
    print(
        {
            "status": payload["robustness_status"],
            "lane_id": payload["lane_id"],
            "warnings": payload["warnings"],
            "report": "reports/sequence26/robustness/latest_robustness.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("oos-replay-readiness")
def research_oos_replay_readiness(
    fixture_path: Annotated[Path | None, typer.Option("--fixture-path")] = None,
) -> None:
    payload = write_oos_replay_readiness_report(
        fixture_path=fixture_path or DEFAULT_POLYMARKET_OOS_ACTIVITY_FIXTURE,
    )
    print(
        {
            "status": payload["replay_readiness_status"],
            "lane_id": payload["lane_id"],
            "ready_for_narrow_replay_design": payload["ready_for_narrow_replay_design"],
            "blockers": payload["blockers"],
            "report": "reports/sequence26/replay_readiness/latest_replay_readiness.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("reference-context-report")
def research_reference_context_report(
    fixture_path: Annotated[Path | None, typer.Option("--fixture-path")] = None,
) -> None:
    payload = write_reference_context_report(
        fixture_path=fixture_path or DEFAULT_POLYMARKET_OOS_ACTIVITY_FIXTURE,
    )
    print(
        {
            "status": payload["reference_context_status"],
            "lane_id": payload["lane_id"],
            "attached_reference_count": payload["summary"]["attached_reference_count"],
            "missing_reference_count": payload["summary"]["missing_reference_count"],
            "report": "reports/sequence27/reference_context/latest_reference_context.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("reference-quality-report")
def research_reference_quality_report(
    fixture_path: Annotated[Path | None, typer.Option("--fixture-path")] = None,
) -> None:
    payload = write_reference_quality_report(
        fixture_path=fixture_path or DEFAULT_POLYMARKET_OOS_ACTIVITY_FIXTURE,
    )
    print(
        {
            "status": payload["reference_quality_status"],
            "lane_id": payload["lane_id"],
            "usable_reference_count": payload["summary"]["usable_reference_count"],
            "warnings": payload["warnings"],
            "report": "reports/sequence27/reference_quality/latest_reference_quality.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("market-quality-report")
def research_market_quality_filter_report(
    fixture_path: Annotated[Path | None, typer.Option("--fixture-path")] = None,
) -> None:
    payload = write_market_quality_filter_report(
        fixture_path=fixture_path or DEFAULT_POLYMARKET_OOS_ACTIVITY_FIXTURE,
    )
    print(
        {
            "status": payload["market_quality_status"],
            "lane_id": payload["lane_id"],
            "quality_filtered_count": payload["summary"]["quality_filtered_count"],
            "flagged_market_count": payload["summary"]["flagged_market_count"],
            "report": "reports/sequence27/market_quality/latest_market_quality.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("manipulation-flags-report")
def research_manipulation_flags_report(
    fixture_path: Annotated[Path | None, typer.Option("--fixture-path")] = None,
) -> None:
    payload = write_manipulation_flags_report(
        fixture_path=fixture_path or DEFAULT_POLYMARKET_OOS_ACTIVITY_FIXTURE,
    )
    print(
        {
            "status": payload["manipulation_flag_status"],
            "lane_id": payload["lane_id"],
            "flagged_market_count": payload["summary"]["flagged_market_count"],
            "report": "reports/sequence27/manipulation_flags/latest_manipulation_flags.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("venue-signal-report")
def research_venue_signal_report(
    fixture_path: Annotated[Path | None, typer.Option("--fixture-path")] = None,
) -> None:
    payload = write_venue_signal_report(
        fixture_path=fixture_path or DEFAULT_POLYMARKET_OOS_ACTIVITY_FIXTURE,
    )
    print(
        {
            "status": payload["venue_signal_status"],
            "lane_id": payload["lane_id"],
            "resolved_observation_count": payload["resolved_observation_count"],
            "oos_observation_count": payload["oos_observation_count"],
            "market_baseline_dominant": payload["market_baseline_dominant"],
            "report": "reports/sequence27/signal_evaluation/latest_signal_evaluation.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("venue-ablation-report")
def research_venue_ablation_report(
    fixture_path: Annotated[Path | None, typer.Option("--fixture-path")] = None,
) -> None:
    payload = write_ablation_report(
        fixture_path=fixture_path or DEFAULT_POLYMARKET_OOS_ACTIVITY_FIXTURE,
    )
    print(
        {
            "status": payload["ablation_status"],
            "lane_id": payload["lane_id"],
            "warnings": payload["warnings"],
            "report": "reports/sequence27/ablation/latest_ablation.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("lane-decision")
def research_lane_decision(
    fixture_path: Annotated[Path | None, typer.Option("--fixture-path")] = None,
) -> None:
    payload = write_lane_decision_report(
        fixture_path=fixture_path or DEFAULT_POLYMARKET_OOS_ACTIVITY_FIXTURE,
    )
    print(
        {
            "status": payload["lane_decision_status"],
            "lane_id": payload["lane_id"],
            "recommended_action": payload["recommended_action"],
            "ready_for_minimal_replay_spec": payload["ready_for_minimal_replay_spec"],
            "report": "reports/sequence27/lane_decision/latest_lane_decision.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("venue-replay-readiness")
def research_venue_replay_readiness(
    fixture_path: Annotated[Path | None, typer.Option("--fixture-path")] = None,
) -> None:
    payload = write_venue_replay_readiness_report(
        fixture_path=fixture_path or DEFAULT_POLYMARKET_OOS_ACTIVITY_FIXTURE,
    )
    print(
        {
            "status": payload["replay_readiness_status"],
            "lane_id": payload["lane_id"],
            "ready_for_minimal_replay_spec": payload["ready_for_minimal_replay_spec"],
            "ready_for_narrow_replay_design": payload["ready_for_narrow_replay_design"],
            "blockers": payload["blockers"],
            "report": "reports/sequence27/replay_readiness/latest_replay_readiness.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("lane-retirement")
def research_lane_retirement(
    fixture_path: Annotated[Path | None, typer.Option("--fixture-path")] = None,
) -> None:
    from quant_os.research.prediction_markets.lane_retirement import (
        write_lane_retirement_report,
    )

    payload = write_lane_retirement_report(
        fixture_path=fixture_path or DEFAULT_POLYMARKET_OOS_ACTIVITY_FIXTURE,
    )
    print(
        {
            "status": payload["lane_retirement_status"],
            "lane_id": payload["lane_id"],
            "recommended_action": payload["recommended_action"],
            "replay_ready": payload["replay_ready"],
            "report": "reports/sequence28/lane_retirement/latest_lane_retirement.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("next-lane-selection-v2")
def research_next_lane_selection_v2() -> None:
    from quant_os.research.next_lane_selection_v2 import write_next_lane_selection_report

    payload = write_next_lane_selection_report()
    print(
        {
            "status": payload["selection_status"],
            "selected_lane_id": payload["selected_lane_id"],
            "report": "reports/sequence28/next_lane/latest_next_lane_selection.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("replay-input-summary")
def research_replay_input_summary(
    polymarket_snapshot_path: Annotated[
        Path | None,
        typer.Option("--polymarket-snapshot-path"),
    ] = None,
    pmxt_manifest_path: Annotated[
        Path | None,
        typer.Option("--pmxt-manifest-path"),
    ] = None,
    reference_datasets_manifest_path: Annotated[
        Path | None,
        typer.Option("--reference-datasets-manifest-path"),
    ] = None,
) -> None:
    from quant_os.replay.prediction_market_replay_inputs import write_replay_input_summary

    payload = write_replay_input_summary(
        polymarket_snapshot_path=(
            polymarket_snapshot_path or DEFAULT_POLYMARKET_PUBLIC_SNAPSHOT_FIXTURE
        ),
        pmxt_manifest_path=pmxt_manifest_path or DEFAULT_PMXT_MANIFEST_FIXTURE,
        reference_datasets_manifest_path=(
            reference_datasets_manifest_path or DEFAULT_REFERENCE_DATASETS_MANIFEST_FIXTURE
        ),
    )
    print(
        {
            "status": payload["status"],
            "event_count": payload["event_count"],
            "event_counts": payload["event_counts"],
            "report": "reports/sequence28/replay_inputs/latest_replay_inputs_summary.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@research_app.command("replay-input-readiness")
def research_replay_input_readiness(
    polymarket_snapshot_path: Annotated[
        Path | None,
        typer.Option("--polymarket-snapshot-path"),
    ] = None,
    pmxt_manifest_path: Annotated[
        Path | None,
        typer.Option("--pmxt-manifest-path"),
    ] = None,
    reference_datasets_manifest_path: Annotated[
        Path | None,
        typer.Option("--reference-datasets-manifest-path"),
    ] = None,
) -> None:
    from quant_os.research.prediction_markets.replay_input_readiness import (
        write_replay_input_readiness_report,
    )

    payload = write_replay_input_readiness_report(
        polymarket_snapshot_path=(
            polymarket_snapshot_path or DEFAULT_POLYMARKET_PUBLIC_SNAPSHOT_FIXTURE
        ),
        pmxt_manifest_path=pmxt_manifest_path or DEFAULT_PMXT_MANIFEST_FIXTURE,
        reference_datasets_manifest_path=(
            reference_datasets_manifest_path or DEFAULT_REFERENCE_DATASETS_MANIFEST_FIXTURE
        ),
    )
    print(
        {
            "status": payload["replay_input_readiness_status"],
            "ready_for_narrow_replay_design": payload["ready_for_narrow_replay_design"],
            "blockers": payload["blockers"],
            "report": (
                "reports/sequence28/replay_input_readiness/"
                "latest_replay_input_readiness.json"
            ),
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@replay_app.command("design-report")
def replay_design_report(
    polymarket_snapshot_path: Annotated[
        Path | None,
        typer.Option("--polymarket-snapshot-path"),
    ] = None,
    pmxt_manifest_path: Annotated[
        Path | None,
        typer.Option("--pmxt-manifest-path"),
    ] = None,
    reference_datasets_manifest_path: Annotated[
        Path | None,
        typer.Option("--reference-datasets-manifest-path"),
    ] = None,
) -> None:
    from quant_os.replay.prediction_market_replay_design import write_replay_design_report

    payload = write_replay_design_report(
        polymarket_snapshot_path=(
            polymarket_snapshot_path or DEFAULT_POLYMARKET_PUBLIC_SNAPSHOT_FIXTURE
        ),
        pmxt_manifest_path=pmxt_manifest_path or DEFAULT_PMXT_MANIFEST_FIXTURE,
        reference_datasets_manifest_path=(
            reference_datasets_manifest_path or DEFAULT_REFERENCE_DATASETS_MANIFEST_FIXTURE
        ),
    )
    print(
        {
            "status": payload["replay_design_status"],
            "selected_lane_id": payload["selected_lane_id"],
            "events": len(payload["event_timeline"]),
            "report": "reports/sequence31/replay_design/latest_replay_design.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@replay_app.command("shadow-execution-report")
def replay_shadow_execution_report(
    polymarket_snapshot_path: Annotated[
        Path | None,
        typer.Option("--polymarket-snapshot-path"),
    ] = None,
    pmxt_manifest_path: Annotated[
        Path | None,
        typer.Option("--pmxt-manifest-path"),
    ] = None,
    reference_datasets_manifest_path: Annotated[
        Path | None,
        typer.Option("--reference-datasets-manifest-path"),
    ] = None,
) -> None:
    from quant_os.research.prediction_markets.shadow_execution_report import (
        write_shadow_execution_report,
    )

    payload = write_shadow_execution_report(
        polymarket_snapshot_path=(
            polymarket_snapshot_path or DEFAULT_POLYMARKET_PUBLIC_SNAPSHOT_FIXTURE
        ),
        pmxt_manifest_path=pmxt_manifest_path or DEFAULT_PMXT_MANIFEST_FIXTURE,
        reference_datasets_manifest_path=(
            reference_datasets_manifest_path or DEFAULT_REFERENCE_DATASETS_MANIFEST_FIXTURE
        ),
    )
    print(
        {
            "status": payload["shadow_execution_status"],
            "selected_lane_id": payload["selected_lane_id"],
            "intent_count": payload["metrics"]["intent_count"],
            "blocked_trade_count": payload["metrics"]["blocked_trade_count"],
            "report": "reports/sequence31/shadow_execution/latest_shadow_execution.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@replay_app.command("run")
def replay_run(periods: int = typer.Option(120, min=20)) -> None:
    dataset = build_crypto_research_dataset(periods=periods)
    frame = build_crypto_features(dataset.frame)
    btc = frame[frame["symbol"] == "BTC/USDT"].reset_index(drop=True)
    intents = [
        ReplayOrderIntent(
            "sequence1_replay_smoke",
            "BTC/USDT",
            "BUY",
            0.01,
            btc.loc[5, "timestamp"],
            reason_code="SEQUENCE1_SMOKE_ENTRY",
        ),
        ReplayOrderIntent(
            "sequence1_replay_smoke",
            "BTC/USDT",
            "SELL",
            0.01,
            btc.loc[min(len(btc) - 1, 30), "timestamp"],
            reason_code="SEQUENCE1_SMOKE_EXIT",
        ),
    ]
    result = ReplayEngine(fee_bps=5.0, slippage_bps=3.0).run(frame, intents)
    print(
        {
            "status": result.reconciliation["status"],
            "fills": len(result.fills),
            "rejections": len(result.rejections),
            "metrics": result.metrics,
            "live_trading_enabled": False,
        }
    )


@replay_app.command("realism-report")
def replay_realism_report(periods: int = typer.Option(120, min=20)) -> None:
    payload = write_replay_realism_report(periods=periods)
    print(
        {
            "status": payload["status"],
            "fills": payload["fills"],
            "rejections": payload["rejections"],
            "realism_penalty_bps": payload["metrics"].get("realism_penalty_bps", 0.0),
            "report": "reports/sequence2/replay_realism/latest_realism_report.json",
            "live_trading_enabled": False,
        }
    )


@calibration_app.command("run")
def calibration_run() -> None:
    probability = estimate_signal_probability(
        raw_score=0.62,
        volatility_regime="normal",
        liquidity_score=0.75,
        overextension_z=0.6,
    )
    uncertainty = estimate_uncertainty(
        sample_size=120,
        regime_observations=35,
        feature_stability=0.72,
    )
    edge = apply_edge_penalties(
        probability=probability,
        payoff_ratio=1.05,
        cost_bps=8.0,
        correlated_signal_count=1,
        liquidity_score=0.75,
        overextension_z=0.6,
        uncertainty=uncertainty,
    )
    diagnostics = calibration_diagnostics(
        probabilities=[0.35, probability, 0.68, 0.25],
        outcomes=[0, 1, 1, 0],
        expected_returns_bps=[-2.0, edge.edge_bps, 7.0, -4.0],
        equity_curve=[10_000.0, 9_998.0, 10_006.0, 10_011.0],
        regimes=["low", "normal", "normal", "high"],
    )
    print(
        {
            "approved": edge.approved,
            "probability": probability,
            "uncertainty": uncertainty,
            "edge_bps": edge.edge_bps,
            "reason_codes": edge.reason_codes,
            "diagnostics": diagnostics,
            "live_trading_enabled": False,
        }
    )


@calibration_app.command("venue-report")
def calibration_venue_report(
    fixture_path: Annotated[Path | None, typer.Option("--fixture-path")] = None,
    allow_network_fetch: bool = typer.Option(False, "--allow-network-fetch"),
    explicit_network_fetch: bool = typer.Option(False, "--explicit-network-fetch"),
) -> None:
    path_to_use = fixture_path
    if path_to_use is None:
        capture_dir = Path("data/venue_capture")
        if capture_dir.exists():
            captures = list(capture_dir.glob("*.json"))
            if captures:
                path_to_use = max(captures, key=lambda p: p.stat().st_mtime)

    payload = run_venue_calibration(
        fixture_path=path_to_use or DEFAULT_VENUE_FIXTURE,
        allow_network_fetch=allow_network_fetch,
        explicit_network_fetch=explicit_network_fetch,
    )
    print(
        {
            "status": payload["status"],
            "venue": payload["venue"],
            "symbols": payload["symbols"],
            "network_fetch_allowed": payload["network_fetch_allowed"],
            "blockers": payload["blockers"],
            "warnings": payload["warnings"],
            "report": "reports/sequence18/venue_calibration/latest_venue_calibration.json",
            "live_trading_enabled": False,
        }
    )


@validation_app.command("list-scenarios")
def validation_list_scenarios() -> None:
    print({"scenarios": [scenario.model_dump() for scenario in list_scenarios()]})


@validation_app.command("run")
def validation_run(scenario: str = typer.Option(..., "--scenario")) -> None:
    outcome = run_scenario(scenario)
    print(outcome.model_dump(mode="json"))
    if outcome.status != "PASS":
        raise typer.Exit(1)


@validation_app.command("run-all")
def validation_run_all() -> None:
    summary = run_all_scenarios()
    print(
        {
            "status": summary["status"],
            "scenario_count": summary["scenario_count"],
            "unsafe_action_failure_count": summary["unsafe_action_failure_count"],
            "blocked_correctly_count": summary["blocked_correctly_count"],
            "report": "reports/validation/latest_summary.json",
            "live_trading_enabled": False,
        }
    )


@validation_app.command("report")
def validation_report() -> None:
    validation_run_all()


@validation_app.command("walk-forward")
def validation_walk_forward(periods: int = typer.Option(180, min=60)) -> None:
    dataset = build_crypto_research_dataset(periods=periods)
    payload = run_crypto_walk_forward(
        dataset.frame,
        train_bars=60,
        validation_bars=30,
        test_bars=30,
        step_bars=30,
    )
    print(
        {
            "status": payload["status"],
            "split_count": payload["split_count"],
            "warnings": payload["warnings"],
            "report": "reports/sequence2/walk_forward/latest_walk_forward.json",
            "live_trading_enabled": False,
        }
    )


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


@proving_app.command("shadow-proving-report")
def proving_shadow_proving_report(
    polymarket_snapshot_path: Annotated[
        Path | None,
        typer.Option("--polymarket-snapshot-path"),
    ] = None,
    pmxt_manifest_path: Annotated[
        Path | None,
        typer.Option("--pmxt-manifest-path"),
    ] = None,
    reference_datasets_manifest_path: Annotated[
        Path | None,
        typer.Option("--reference-datasets-manifest-path"),
    ] = None,
) -> None:
    from quant_os.proving.shadow_proving_report import write_shadow_proving_report

    payload = write_shadow_proving_report(
        polymarket_snapshot_path=(
            polymarket_snapshot_path
            or _repo_default_path(DEFAULT_POLYMARKET_PUBLIC_SNAPSHOT_FIXTURE)
        ),
        pmxt_manifest_path=pmxt_manifest_path or _repo_default_path(DEFAULT_PMXT_MANIFEST_FIXTURE),
        reference_datasets_manifest_path=(
            reference_datasets_manifest_path
            or _repo_default_path(DEFAULT_REFERENCE_DATASETS_MANIFEST_FIXTURE)
        ),
    )
    print(
        {
            "status": payload["shadow_proving_status"],
            "ready_for_tiny_canary_consideration": payload[
                "ready_for_tiny_canary_consideration"
            ],
            "blockers": payload["blockers"],
            "report": "reports/sequence32/shadow_proving/latest_shadow_proving_report.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@proving_app.command("shadow-sample-windows")
def proving_shadow_sample_windows(
    polymarket_snapshot_path: Annotated[
        Path | None,
        typer.Option("--polymarket-snapshot-path"),
    ] = None,
    pmxt_manifest_path: Annotated[
        Path | None,
        typer.Option("--pmxt-manifest-path"),
    ] = None,
    reference_datasets_manifest_path: Annotated[
        Path | None,
        typer.Option("--reference-datasets-manifest-path"),
    ] = None,
) -> None:
    from quant_os.proving.shadow_window_report import write_shadow_window_report

    payload = write_shadow_window_report(
        polymarket_snapshot_path=(
            polymarket_snapshot_path
            or _repo_default_path(DEFAULT_POLYMARKET_PUBLIC_SNAPSHOT_FIXTURE)
        ),
        pmxt_manifest_path=pmxt_manifest_path or _repo_default_path(DEFAULT_PMXT_MANIFEST_FIXTURE),
        reference_datasets_manifest_path=(
            reference_datasets_manifest_path
            or _repo_default_path(DEFAULT_REFERENCE_DATASETS_MANIFEST_FIXTURE)
        ),
    )
    print(
        {
            "status": payload["shadow_sample_status"],
            "total_window_count": payload["total_window_count"],
            "proving_effective_window_count": payload["proving_effective_window_count"],
            "report": "reports/sequence33/shadow_samples/latest_shadow_windows.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@proving_app.command("shadow-blocker-attribution")
def proving_shadow_blocker_attribution(
    polymarket_snapshot_path: Annotated[
        Path | None,
        typer.Option("--polymarket-snapshot-path"),
    ] = None,
    pmxt_manifest_path: Annotated[
        Path | None,
        typer.Option("--pmxt-manifest-path"),
    ] = None,
    reference_datasets_manifest_path: Annotated[
        Path | None,
        typer.Option("--reference-datasets-manifest-path"),
    ] = None,
) -> None:
    from quant_os.proving.shadow_blocker_report import write_shadow_blocker_report

    payload = write_shadow_blocker_report(
        polymarket_snapshot_path=(
            polymarket_snapshot_path
            or _repo_default_path(DEFAULT_POLYMARKET_PUBLIC_SNAPSHOT_FIXTURE)
        ),
        pmxt_manifest_path=pmxt_manifest_path or _repo_default_path(DEFAULT_PMXT_MANIFEST_FIXTURE),
        reference_datasets_manifest_path=(
            reference_datasets_manifest_path
            or _repo_default_path(DEFAULT_REFERENCE_DATASETS_MANIFEST_FIXTURE)
        ),
    )
    print(
        {
            "status": payload["blocker_attribution_status"],
            "blocker_groups": payload["blocker_groups"],
            "report": "reports/sequence33/blocker_attribution/latest_blocker_attribution.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@proving_app.command("shadow-sensitivity")
def proving_shadow_sensitivity(
    polymarket_snapshot_path: Annotated[
        Path | None,
        typer.Option("--polymarket-snapshot-path"),
    ] = None,
    pmxt_manifest_path: Annotated[
        Path | None,
        typer.Option("--pmxt-manifest-path"),
    ] = None,
    reference_datasets_manifest_path: Annotated[
        Path | None,
        typer.Option("--reference-datasets-manifest-path"),
    ] = None,
) -> None:
    from quant_os.proving.shadow_sensitivity_report import (
        write_shadow_sensitivity_report,
    )

    payload = write_shadow_sensitivity_report(
        polymarket_snapshot_path=(
            polymarket_snapshot_path
            or _repo_default_path(DEFAULT_POLYMARKET_PUBLIC_SNAPSHOT_FIXTURE)
        ),
        pmxt_manifest_path=pmxt_manifest_path or _repo_default_path(DEFAULT_PMXT_MANIFEST_FIXTURE),
        reference_datasets_manifest_path=(
            reference_datasets_manifest_path
            or _repo_default_path(DEFAULT_REFERENCE_DATASETS_MANIFEST_FIXTURE)
        ),
    )
    print(
        {
            "status": payload["shadow_sensitivity_status"],
            "blocked_state_robust_across_assumptions": payload[
                "blocked_state_robust_across_assumptions"
            ],
            "report": "reports/sequence33/shadow_sensitivity/latest_shadow_sensitivity.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@proving_app.command("unblockability")
def proving_unblockability(
    polymarket_snapshot_path: Annotated[
        Path | None,
        typer.Option("--polymarket-snapshot-path"),
    ] = None,
    pmxt_manifest_path: Annotated[
        Path | None,
        typer.Option("--pmxt-manifest-path"),
    ] = None,
    reference_datasets_manifest_path: Annotated[
        Path | None,
        typer.Option("--reference-datasets-manifest-path"),
    ] = None,
) -> None:
    from quant_os.proving.unblockability_report import write_unblockability_report

    payload = write_unblockability_report(
        polymarket_snapshot_path=(
            polymarket_snapshot_path
            or _repo_default_path(DEFAULT_POLYMARKET_PUBLIC_SNAPSHOT_FIXTURE)
        ),
        pmxt_manifest_path=pmxt_manifest_path or _repo_default_path(DEFAULT_PMXT_MANIFEST_FIXTURE),
        reference_datasets_manifest_path=(
            reference_datasets_manifest_path
            or _repo_default_path(DEFAULT_REFERENCE_DATASETS_MANIFEST_FIXTURE)
        ),
    )
    print(
        {
            "status": payload["unblockability_status"],
            "ready_for_bounded_shadow_rehearsal": payload[
                "ready_for_bounded_shadow_rehearsal"
            ],
            "report": "reports/sequence33/unblockability/latest_unblockability.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@proving_app.command("dry-run-proving")
def proving_dry_run_proving(periods: int = typer.Option(180, min=60)) -> None:
    payload = run_dry_run_proving_cycle(config=DryRunProvingConfig(periods=periods))
    print(
        {
            "status": payload["status"],
            "allowed_action_count": payload["allowed_action_count"],
            "blocked_action_count": payload["blocked_action_count"],
            "readiness": payload["readiness"]["status"],
            "report": "reports/sequence2/proving/latest_proving_summary.json",
            "live_trading_enabled": False,
        }
    )


@proving_app.command("sequence2-report")
def proving_sequence2_report(periods: int = typer.Option(180, min=60)) -> None:
    proving_dry_run_proving(periods=periods)


@readiness_app.command("report")
def readiness_report() -> None:
    payload = write_sequence2_readiness_report()
    print(
        {
            "status": payload["status"],
            "blockers": payload["blockers"],
            "warnings": payload["warnings"],
            "report": "reports/sequence2/readiness/latest_readiness.json",
            "live_trading_enabled": False,
        }
    )


@readiness_app.command("shadow-autonomy")
def readiness_shadow_autonomy(
    polymarket_snapshot_path: Annotated[
        Path | None,
        typer.Option("--polymarket-snapshot-path"),
    ] = None,
    pmxt_manifest_path: Annotated[
        Path | None,
        typer.Option("--pmxt-manifest-path"),
    ] = None,
    reference_datasets_manifest_path: Annotated[
        Path | None,
        typer.Option("--reference-datasets-manifest-path"),
    ] = None,
) -> None:
    from quant_os.readiness.shadow_autonomy_report import write_shadow_autonomy_report

    payload = write_shadow_autonomy_report(
        polymarket_snapshot_path=(
            polymarket_snapshot_path or DEFAULT_POLYMARKET_PUBLIC_SNAPSHOT_FIXTURE
        ),
        pmxt_manifest_path=pmxt_manifest_path or DEFAULT_PMXT_MANIFEST_FIXTURE,
        reference_datasets_manifest_path=(
            reference_datasets_manifest_path or DEFAULT_REFERENCE_DATASETS_MANIFEST_FIXTURE
        ),
    )
    print(
        {
            "status": payload["shadow_autonomy_status"],
            "ready_for_bounded_shadow_autonomy": payload[
                "ready_for_bounded_shadow_autonomy"
            ],
            "report": "reports/sequence31/shadow_autonomy/latest_shadow_autonomy.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@readiness_app.command("canary-preconditions")
def readiness_canary_preconditions(
    polymarket_snapshot_path: Annotated[
        Path | None,
        typer.Option("--polymarket-snapshot-path"),
    ] = None,
    pmxt_manifest_path: Annotated[
        Path | None,
        typer.Option("--pmxt-manifest-path"),
    ] = None,
    reference_datasets_manifest_path: Annotated[
        Path | None,
        typer.Option("--reference-datasets-manifest-path"),
    ] = None,
) -> None:
    from quant_os.readiness.canary_preconditions_report import (
        write_canary_preconditions_report,
    )

    payload = write_canary_preconditions_report(
        polymarket_snapshot_path=(
            polymarket_snapshot_path
            or _repo_default_path(DEFAULT_POLYMARKET_PUBLIC_SNAPSHOT_FIXTURE)
        ),
        pmxt_manifest_path=pmxt_manifest_path or _repo_default_path(DEFAULT_PMXT_MANIFEST_FIXTURE),
        reference_datasets_manifest_path=(
            reference_datasets_manifest_path
            or _repo_default_path(DEFAULT_REFERENCE_DATASETS_MANIFEST_FIXTURE)
        ),
    )
    print(
        {
            "status": payload["canary_preconditions_status"],
            "ready_for_tiny_canary_consideration": payload[
                "ready_for_tiny_canary_consideration"
            ],
            "still_blocked_reasons": payload["still_blocked_reasons"],
            "report": "reports/sequence32/canary_preconditions/latest_canary_preconditions.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@readiness_app.command("canary-blockers")
def readiness_canary_blockers(
    polymarket_snapshot_path: Annotated[
        Path | None,
        typer.Option("--polymarket-snapshot-path"),
    ] = None,
    pmxt_manifest_path: Annotated[
        Path | None,
        typer.Option("--pmxt-manifest-path"),
    ] = None,
    reference_datasets_manifest_path: Annotated[
        Path | None,
        typer.Option("--reference-datasets-manifest-path"),
    ] = None,
) -> None:
    from quant_os.readiness.canary_blockers_report import write_canary_blockers_report

    payload = write_canary_blockers_report(
        polymarket_snapshot_path=(
            polymarket_snapshot_path
            or _repo_default_path(DEFAULT_POLYMARKET_PUBLIC_SNAPSHOT_FIXTURE)
        ),
        pmxt_manifest_path=pmxt_manifest_path or _repo_default_path(DEFAULT_PMXT_MANIFEST_FIXTURE),
        reference_datasets_manifest_path=(
            reference_datasets_manifest_path
            or _repo_default_path(DEFAULT_REFERENCE_DATASETS_MANIFEST_FIXTURE)
        ),
    )
    print(
        {
            "status": payload["canary_blocker_status"],
            "still_blocked": payload["still_blocked"],
            "not_almost_ready": payload["not_almost_ready"],
            "report": "reports/sequence32/canary_blockers/latest_canary_blockers.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@readiness_app.command("shadow-rehearsal")
def readiness_shadow_rehearsal(
    polymarket_snapshot_path: Annotated[
        Path | None,
        typer.Option("--polymarket-snapshot-path"),
    ] = None,
    pmxt_manifest_path: Annotated[
        Path | None,
        typer.Option("--pmxt-manifest-path"),
    ] = None,
    reference_datasets_manifest_path: Annotated[
        Path | None,
        typer.Option("--reference-datasets-manifest-path"),
    ] = None,
) -> None:
    from quant_os.readiness.shadow_rehearsal_report import write_shadow_rehearsal_report

    payload = write_shadow_rehearsal_report(
        polymarket_snapshot_path=(
            polymarket_snapshot_path
            or _repo_default_path(DEFAULT_POLYMARKET_PUBLIC_SNAPSHOT_FIXTURE)
        ),
        pmxt_manifest_path=pmxt_manifest_path or _repo_default_path(DEFAULT_PMXT_MANIFEST_FIXTURE),
        reference_datasets_manifest_path=(
            reference_datasets_manifest_path
            or _repo_default_path(DEFAULT_REFERENCE_DATASETS_MANIFEST_FIXTURE)
        ),
    )
    print(
        {
            "status": payload["shadow_rehearsal_status"],
            "ready_for_bounded_shadow_rehearsal": payload[
                "ready_for_bounded_shadow_rehearsal"
            ],
            "report": "reports/sequence33/shadow_rehearsal/latest_shadow_rehearsal.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@readiness_app.command("autonomy-milestones")
def readiness_autonomy_milestones() -> None:
    from quant_os.readiness.autonomy_milestone_report import (
        write_autonomy_milestone_report,
    )

    payload = write_autonomy_milestone_report()
    print(
        {
            "status": payload["ledger_status"],
            "milestone_count": payload["milestone_count"],
            "next_required_milestone": payload["next_required_milestone"]["milestone_id"],
            "report": "reports/sequence35/autonomy_milestones/latest_autonomy_milestones.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@readiness_app.command("replay-dataset-readiness")
def readiness_replay_dataset_readiness(
    fixture_root: Annotated[Path | None, typer.Option("--fixture-root")] = None,
) -> None:
    from quant_os.readiness.autonomy_milestone_report import (
        write_sequence36_autonomy_milestone_report,
    )
    from quant_os.readiness.replay_dataset_readiness_report import (
        write_replay_dataset_readiness_report,
    )
    from quant_os.research.replay_candidates.pm_crypto_updown_dataset_report import (
        write_pm_crypto_updown_dataset_report,
    )

    dataset = write_pm_crypto_updown_dataset_report(
        fixture_root=fixture_root or _repo_default_path(DEFAULT_PM_CRYPTO_UPDOWN_FIXTURE_ROOT),
    )
    payload = write_replay_dataset_readiness_report(dataset_report=dataset)
    write_sequence36_autonomy_milestone_report(replay_dataset_readiness=payload)
    print(
        {
            "status": payload["readiness_status"],
            "ready_for_phase37_candidate_replay": payload[
                "ready_for_phase37_candidate_replay"
            ],
            "report": "reports/sequence36/replay_dataset_readiness/latest_replay_dataset_readiness.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@readiness_app.command("candidate-replay-readiness")
def readiness_candidate_replay_readiness(
    fixture_root: Annotated[Path | None, typer.Option("--fixture-root")] = None,
) -> None:
    from quant_os.readiness.candidate_replay_readiness_report import (
        write_candidate_replay_readiness_report,
    )
    from quant_os.research.replay_candidates.pm_crypto_updown_replay_eval import (
        write_pm_crypto_updown_replay_eval_report,
    )

    evaluation = write_pm_crypto_updown_replay_eval_report(
        fixture_root=fixture_root or _repo_default_path(DEFAULT_PM_CRYPTO_UPDOWN_FIXTURE_ROOT),
    )
    payload = write_candidate_replay_readiness_report(evaluation_report=evaluation)
    print(
        {
            "status": payload["readiness_status"],
            "ready_for_expanded_shadow_replay": payload[
                "ready_for_expanded_shadow_replay"
            ],
            "report": "reports/sequence37/replay_readiness/latest_candidate_replay_readiness.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@readiness_app.command("expanded-shadow-replay")
def readiness_expanded_shadow_replay(
    fixture_root: Annotated[Path | None, typer.Option("--fixture-root")] = None,
) -> None:
    from quant_os.readiness.expanded_shadow_replay_readiness_report import (
        write_expanded_shadow_replay_readiness_report,
    )
    from quant_os.research.replay_candidates.pm_crypto_updown_expanded_replay_eval import (
        write_pm_crypto_updown_expanded_replay_eval_report,
    )

    evaluation = write_pm_crypto_updown_expanded_replay_eval_report(
        fixture_root=fixture_root or _repo_default_path(DEFAULT_PM_CRYPTO_UPDOWN_FIXTURE_ROOT),
    )
    payload = write_expanded_shadow_replay_readiness_report(
        expanded_replay_eval=evaluation,
    )
    print(
        {
            "status": payload["readiness_status"],
            "overall_status": payload["overall_status"],
            "ready_for_expanded_shadow_replay": payload[
                "ready_for_expanded_shadow_replay"
            ],
            "report": "reports/sequence38/expanded_shadow_replay_readiness/latest_expanded_shadow_replay_readiness.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@readiness_app.command("real-cached-replay-readiness")
def readiness_real_cached_replay(
    fixture_root: Annotated[Path | None, typer.Option("--fixture-root")] = None,
    real_cached_root: Annotated[list[Path] | None, typer.Option("--real-cached-root")] = None,
) -> None:
    from quant_os.readiness.real_cached_replay_readiness_report import (
        write_real_cached_replay_readiness_report,
    )
    from quant_os.research.replay_candidates.pm_crypto_updown_real_cached_replay_eval import (
        write_pm_crypto_updown_real_cached_replay_eval_report,
    )

    evaluation = write_pm_crypto_updown_real_cached_replay_eval_report(
        fixture_root=fixture_root or _repo_default_path(DEFAULT_PM_CRYPTO_UPDOWN_FIXTURE_ROOT),
        real_cached_artifact_roots=_optional_path_list(real_cached_root),
    )
    payload = write_real_cached_replay_readiness_report(
        real_cached_replay_eval=evaluation,
    )
    print(
        {
            "status": payload["readiness_status"],
            "overall_status": payload["overall_status"],
            "ready_for_expanded_shadow_replay": payload[
                "ready_for_expanded_shadow_replay"
            ],
            "primary_evidence_row_count": payload["primary_evidence_row_count"],
            "real_cached_replay_ready_row_count": payload[
                "real_cached_replay_ready_row_count"
            ],
            "report": "reports/sequence39/real_cached_readiness/latest_real_cached_replay_readiness.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@readiness_app.command("expanded-shadow-replay-readiness")
def readiness_expanded_shadow_replay_readiness(
    fixture_root: Annotated[Path | None, typer.Option("--fixture-root")] = None,
    real_cached_root: Annotated[list[Path] | None, typer.Option("--real-cached-root")] = None,
) -> None:
    from quant_os.readiness.expanded_shadow_replay_readiness_report import (
        write_sequence41_expanded_shadow_replay_readiness_report,
    )
    from quant_os.research.replay_candidates.pm_crypto_updown_real_cached_replay_eval import (
        write_pm_crypto_updown_sequence41_replay_eval_report,
    )

    evaluation = write_pm_crypto_updown_sequence41_replay_eval_report(
        fixture_root=fixture_root or _repo_default_path(DEFAULT_PM_CRYPTO_UPDOWN_FIXTURE_ROOT),
        real_cached_artifact_roots=_optional_path_list(real_cached_root),
    )
    payload = write_sequence41_expanded_shadow_replay_readiness_report(
        real_cached_replay_eval=evaluation,
    )
    print(
        {
            "status": payload["readiness_status"],
            "overall_status": payload["overall_status"],
            "ready_for_expanded_shadow_replay": payload[
                "ready_for_expanded_shadow_replay"
            ],
            "primary_evidence_row_count": payload["primary_evidence_row_count"],
            "real_cached_replay_ready_row_count": payload[
                "real_cached_replay_ready_row_count"
            ],
            "report": "reports/sequence41/expanded_shadow_replay_readiness/latest_expanded_shadow_replay_readiness.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@readiness_app.command("bounded-shadow-rehearsal")
def readiness_bounded_shadow_rehearsal(
    fixture_root: Annotated[Path | None, typer.Option("--fixture-root")] = None,
    real_cached_root: Annotated[list[Path] | None, typer.Option("--real-cached-root")] = None,
) -> None:
    from quant_os.readiness.bounded_shadow_rehearsal_readiness_report import (
        write_bounded_shadow_rehearsal_readiness_report,
    )
    from quant_os.research.replay_candidates.pm_crypto_updown_policy_replay_eval import (
        write_pm_crypto_updown_policy_replay_eval_report,
    )

    evaluation = write_pm_crypto_updown_policy_replay_eval_report(
        fixture_root=fixture_root or _repo_default_path(DEFAULT_PM_CRYPTO_UPDOWN_FIXTURE_ROOT),
        real_cached_artifact_roots=_optional_path_list(real_cached_root),
    )
    payload = write_bounded_shadow_rehearsal_readiness_report(
        policy_replay_eval=evaluation,
    )
    print(
        {
            "status": payload["readiness_status"],
            "overall_status": payload["overall_status"],
            "ready_for_bounded_shadow_rehearsal": payload[
                "ready_for_bounded_shadow_rehearsal"
            ],
            "primary_evidence_row_count": payload["primary_evidence_row_count"],
            "primary_allowed_intent_count": payload["primary_allowed_intent_count"],
            "report": "reports/sequence43/bounded_shadow_rehearsal_readiness/latest_bounded_shadow_rehearsal_readiness.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@readiness_app.command("pm-crypto-updown-candidate-decision")
def readiness_pm_crypto_updown_candidate_decision(
    fixture_root: Annotated[Path | None, typer.Option("--fixture-root")] = None,
    real_cached_root: Annotated[list[Path] | None, typer.Option("--real-cached-root")] = None,
) -> None:
    from quant_os.readiness.pm_crypto_updown_candidate_decision_report import (
        write_pm_crypto_updown_candidate_decision_report,
    )

    payload = write_pm_crypto_updown_candidate_decision_report(
        fixture_root=fixture_root or _repo_default_path(DEFAULT_PM_CRYPTO_UPDOWN_FIXTURE_ROOT),
        real_cached_artifact_roots=_optional_path_list(real_cached_root),
    )
    print(
        {
            "status": payload["decision_status"],
            "ready_for_bounded_shadow_rehearsal": payload[
                "ready_for_bounded_shadow_rehearsal"
            ],
            "allowed_primary_intent_count": payload["allowed_primary_intent_count"],
            "allowed_real_cached_intent_count": payload["allowed_real_cached_intent_count"],
            "report": "reports/sequence44/candidate_decision/latest_pm_crypto_updown_candidate_decision.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@readiness_app.command("pm-crypto-updown-allowed-intent-decision")
def readiness_pm_crypto_updown_allowed_intent_decision(
    fixture_root: Annotated[Path | None, typer.Option("--fixture-root")] = None,
    real_cached_root: Annotated[list[Path] | None, typer.Option("--real-cached-root")] = None,
) -> None:
    from quant_os.readiness.pm_crypto_updown_allowed_intent_decision_report import (
        write_pm_crypto_updown_allowed_intent_decision_report,
    )

    payload = write_pm_crypto_updown_allowed_intent_decision_report(
        fixture_root=fixture_root or _repo_default_path(DEFAULT_PM_CRYPTO_UPDOWN_FIXTURE_ROOT),
        real_cached_artifact_roots=_optional_path_list(real_cached_root),
    )
    print(
        {
            "status": payload["decision_status"],
            "ready_for_bounded_shadow_rehearsal": payload[
                "ready_for_bounded_shadow_rehearsal"
            ],
            "allowed_primary_intent_count": payload["allowed_primary_intent_count"],
            "allowed_real_cached_intent_count": payload["allowed_real_cached_intent_count"],
            "report": "reports/sequence45/candidate_decision/latest_pm_crypto_updown_candidate_decision.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@readiness_app.command("pm-crypto-updown-phase46-candidate-path")
def readiness_pm_crypto_updown_phase46_candidate_path(
    run_id: str = typer.Option("pm_crypto_updown_manual_046", "--run-id"),
    fixture_root: Annotated[Path | None, typer.Option("--fixture-root")] = None,
    real_cached_root: Annotated[list[Path] | None, typer.Option("--real-cached-root")] = None,
) -> None:
    from quant_os.readiness.pm_crypto_updown_phase46_candidate_path_report import (
        write_pm_crypto_updown_phase46_candidate_path_report,
    )
    from quant_os.research.replay_candidates.pm_crypto_updown_allowed_intent_capture_pass import (
        DEFAULT_CAPTURE_ROOT,
    )

    payload = write_pm_crypto_updown_phase46_candidate_path_report(
        run_id=run_id,
        capture_run_root=DEFAULT_CAPTURE_ROOT / run_id,
        baseline_real_cached_artifact_roots=_optional_path_list(real_cached_root),
        fixture_root=fixture_root or _repo_default_path(DEFAULT_PM_CRYPTO_UPDOWN_FIXTURE_ROOT),
    )
    print(
        {
            "status": payload["final_status"],
            "bounded_shadow_rehearsal_package_created": payload[
                "bounded_shadow_rehearsal_package_created"
            ],
            "next_candidate_handoff_created": payload["next_candidate_handoff_created"],
            "allowed_primary_intents_after": payload["allowed_primary_intents_after"],
            "allowed_real_cached_intents_after": payload[
                "allowed_real_cached_intents_after"
            ],
            "report": "reports/sequence46/candidate_path/latest_phase46_candidate_path.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@readiness_app.command("pm-lp-refresh-lag-candidate-readiness")
def readiness_pm_lp_refresh_lag_candidate_readiness(
    fixture_path: Annotated[Path | None, typer.Option("--fixture-path")] = None,
) -> None:
    from quant_os.readiness.autonomy_milestone_report import (
        write_sequence47_autonomy_milestone_report,
    )
    from quant_os.research.replay_candidates.pm_lp_refresh_lag_source_policy import (
        write_pm_lp_refresh_lag_candidate_readiness_report,
    )

    payload = write_pm_lp_refresh_lag_candidate_readiness_report(
        fixture_path=fixture_path or _repo_default_path(DEFAULT_PM_LP_REFRESH_LAG_FIXTURE),
    )
    write_sequence47_autonomy_milestone_report(candidate_readiness=payload)
    print(
        {
            "status": payload["candidate_readiness_status"],
            "data_availability_status": payload["data_availability_status"],
            "fixture_event_count": payload["fixture_event_count"],
            "report": "reports/sequence47/candidate_readiness/latest_candidate_readiness.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@readiness_app.command("pm-lp-refresh-lag-source-readiness")
def readiness_pm_lp_refresh_lag_source_readiness(
    fixture_path: Annotated[Path | None, typer.Option("--fixture-path")] = None,
) -> None:
    from quant_os.readiness.pm_lp_refresh_lag_source_readiness_report import (
        write_pm_lp_refresh_lag_source_readiness_report,
    )

    payload = write_pm_lp_refresh_lag_source_readiness_report(
        fixture_path=fixture_path
        or _repo_default_path(DEFAULT_PM_LP_REFRESH_LAG_PUBLIC_SOURCE_FIXTURE),
    )
    print(
        {
            "status": payload["source_readiness_status"],
            "active_blocker": payload["active_blocker"],
            "exact_missing_source_fields": payload["exact_missing_source_fields"],
            "report": "reports/sequence48/source_readiness/latest_source_readiness.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
        }
    )


@proving_app.command("pm-crypto-updown-bounded-shadow-rehearsal-spec")
def proving_pm_crypto_updown_bounded_shadow_rehearsal_spec(
    fixture_root: Annotated[Path | None, typer.Option("--fixture-root")] = None,
    real_cached_root: Annotated[list[Path] | None, typer.Option("--real-cached-root")] = None,
) -> None:
    from quant_os.proving.pm_crypto_updown_bounded_shadow_rehearsal_spec import (
        write_pm_crypto_updown_bounded_shadow_rehearsal_report,
    )
    from quant_os.readiness.pm_crypto_updown_allowed_intent_decision import (
        evaluate_pm_crypto_updown_allowed_intent_decision,
    )

    decision = evaluate_pm_crypto_updown_allowed_intent_decision(
        fixture_root=fixture_root or _repo_default_path(DEFAULT_PM_CRYPTO_UPDOWN_FIXTURE_ROOT),
        real_cached_artifact_roots=_optional_path_list(real_cached_root),
    )
    payload = write_pm_crypto_updown_bounded_shadow_rehearsal_report(
        candidate_decision=decision,
    )
    print(
        {
            "status": payload["status"],
            "package_created": payload["package_created"],
            "report": "reports/sequence45/bounded_shadow_rehearsal/latest_bounded_shadow_rehearsal.json",
            "live_trading_enabled": False,
            "execution_authority": payload["execution_authority"],
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


@canary_app.command("live-prepare")
def canary_live_prepare(
    credential_path: Annotated[Path | None, typer.Option("--credential-path")] = None,
) -> None:
    payload = prepare_live_canary(credential_path=credential_path)
    print(
        {
            "status": payload["status"],
            "credential_status": payload["credential_status"],
            "adapter_available": payload["adapter_available"],
            "blockers": payload["blockers"],
            "live_promotion_status": payload["live_promotion_status"],
            "report": "reports/live_canary/latest_prepare.md",
        }
    )


@canary_app.command("exchange-capabilities")
def canary_exchange_capabilities() -> None:
    payload = inspect_exchange_capabilities()
    print(
        {
            "status": payload["status"],
            "adapter_mode": payload["adapter_mode"],
            "dependency_status": payload["dependency_status"],
            "settings_status": payload["settings_status"],
            "real_order_possible": payload["real_order_possible"],
            "live_promotion_status": payload["live_promotion_status"],
            "report": "reports/live_canary/latest_capabilities.md",
        }
    )


@canary_app.command("live-preflight")
def canary_live_preflight(
    symbol: str | None = typer.Option(None, "--symbol"),
    notional_usd: float | None = typer.Option(None, "--notional-usd"),
    credential_path: Annotated[Path | None, typer.Option("--credential-path")] = None,
) -> None:
    payload = run_live_preflight(
        symbol=symbol,
        notional_usd=notional_usd,
        credential_path=credential_path,
    )
    print(
        {
            "status": payload["status"],
            "preflight_status": payload["preflight_status"],
            "blockers": payload["blockers"],
            "live_promotion_status": payload["live_promotion_status"],
            "report": "reports/live_canary/latest_preflight.md",
        }
    )


@canary_app.command("live-fire")
def canary_live_fire(
    symbol: str = typer.Option("BTC/USDT", "--symbol"),
    notional_usd: float = typer.Option(10.0, "--notional-usd"),
    side: str = typer.Option("buy", "--side"),
    confirm_live_fire: bool = typer.Option(False, "--confirm-live-fire"),
    credential_path: Annotated[Path | None, typer.Option("--credential-path")] = None,
) -> None:
    payload = fire_live_canary(
        symbol=symbol,
        notional_usd=notional_usd,
        side=side,
        confirm_live_fire=confirm_live_fire,
        credential_path=credential_path,
    )
    print(
        {
            "status": payload["status"],
            "real_order_possible": payload["real_order_possible"],
            "real_order_attempted": payload["real_order_attempted"],
            "blockers": payload["blockers"],
            "live_promotion_status": payload["live_promotion_status"],
            "report": "reports/live_canary/latest_fire_attempt.md",
        }
    )


@canary_app.command("live-status")
def canary_live_status() -> None:
    payload = live_canary_status()
    print(
        {
            "status": payload["status"],
            "adapter_available": payload["adapter_available"],
            "open_position_count": payload["open_position_count"],
            "live_fire_enabled": payload["live_fire_enabled"],
            "live_promotion_status": payload["live_promotion_status"],
            "report": "reports/live_canary/latest_status.md",
        }
    )


@canary_app.command("live-reconcile")
def canary_live_reconcile() -> None:
    payload = reconcile_live_canary()
    print(
        {
            "status": payload["status"],
            "observed_open_positions": payload["observed_open_positions"],
            "blockers": payload["blockers"],
            "live_promotion_status": payload["live_promotion_status"],
            "report": "reports/live_canary/latest_reconciliation.md",
        }
    )


@canary_app.command("live-stop")
def canary_live_stop() -> None:
    payload = stop_live_canary()
    print(
        {
            "status": payload["status"],
            "kill_switch_status": payload["kill_switch_status"],
            "live_promotion_status": payload["live_promotion_status"],
            "report": "reports/live_canary/latest_stop.md",
        }
    )


@canary_app.command("live-report")
def canary_live_report() -> None:
    payload = write_live_canary_report_bundle()
    print(
        {
            "status": payload["status"],
            "prepare_status": payload["prepare_status"],
            "preflight_status": payload["preflight_status"],
            "live_promotion_status": payload["live_promotion_status"],
            "report": payload["latest_report_path"],
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


@autonomous_app.command("dry-run-proving")
def autonomous_dry_run_proving(periods: int = typer.Option(180, min=60)) -> None:
    payload = run_dry_run_proving_cycle(config=DryRunProvingConfig(periods=periods))
    print(
        {
            "status": payload["status"],
            "allowed_action_count": payload["allowed_action_count"],
            "blocked_action_count": payload["blocked_action_count"],
            "readiness": payload["readiness"]["status"],
            "report": "reports/sequence2/proving/latest_proving_summary.json",
            "live_trading_enabled": False,
        }
    )


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


@research_app.command("calibrated-edge-report")
def research_calibrated_edge_report(periods: int = typer.Option(240, min=120)) -> None:
    dataset = build_crypto_research_dataset(periods=periods)
    calibration = run_venue_calibration()
    payload = write_calibrated_edge_report(
        dataset.frame,
        calibration_summary=calibration,
    )
    print(
        {
            "status": payload["status"],
            "credibility_status": payload["credibility_status"],
            "calibrated_cost_bps": payload["calibrated_cost_bps"],
            "blockers": payload["blockers"],
            "report": "reports/sequence18/calibrated_edge/latest_calibrated_edge.json",
            "live_trading_enabled": False,
        }
    )


@research_app.command("external-benchmark-report")
def research_external_benchmark_report() -> None:
    from quant_os.research.lane_benchmark_report import write_lane_benchmark_report

    payload = write_lane_benchmark_report(output_root=Path("."))
    print(
        {
            "status": payload["status"],
            "recommendation": payload["recommendation"]["staged_order"],
            "report": "reports/external_benchmarks/lane_benchmark/latest_external_benchmark_report.json",
            "live_trading_enabled": payload["live_trading_enabled"],
            "prediction_market_execution_authority_added": payload[
                "prediction_market_execution_authority_added"
            ],
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
