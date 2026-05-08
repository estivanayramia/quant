from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

BENCHMARK_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "benchmark_sources"
POLYMARKET_SNAPSHOT = BENCHMARK_FIXTURE_ROOT / "polymarket_public_snapshot.json"
PMXT_MANIFEST = BENCHMARK_FIXTURE_ROOT / "pmxt_manifest.json"
REFERENCE_DATASETS = BENCHMARK_FIXTURE_ROOT / "reference_datasets_manifest.json"


def test_sequence31_replay_design_is_deterministic_and_orders_events(
    local_project: Path,
) -> None:
    from quant_os.replay.prediction_market_replay_design import write_replay_design_report

    first = write_replay_design_report(
        output_root=local_project,
        polymarket_snapshot_path=POLYMARKET_SNAPSHOT,
        pmxt_manifest_path=PMXT_MANIFEST,
        reference_datasets_manifest_path=REFERENCE_DATASETS,
    )
    second = write_replay_design_report(
        output_root=local_project,
        polymarket_snapshot_path=POLYMARKET_SNAPSHOT,
        pmxt_manifest_path=PMXT_MANIFEST,
        reference_datasets_manifest_path=REFERENCE_DATASETS,
    )

    assert first["replay_design_status"] == "REPLAY_DESIGN_PARTIAL"
    assert first["event_ordering_rules"] == second["event_ordering_rules"]
    assert first["event_timeline"] == second["event_timeline"]
    assert [event["event_index"] for event in first["event_timeline"]] == list(
        range(len(first["event_timeline"]))
    )
    assert "no_guaranteed_queue_position" in first["venue_limitations"]
    assert "uncertain_fill_priority" in first["venue_limitations"]
    assert first["live_trading_enabled"] is False
    assert first["execution_authority"] == "NONE"
    assert (
        local_project
        / "reports"
        / "sequence31"
        / "replay_design"
        / "latest_replay_design.json"
    ).exists()


def test_sequence31_fill_model_defaults_are_conservative_and_reject_optimism() -> None:
    from quant_os.execution.shadow_order_intents import ShadowOrderIntent
    from quant_os.replay.fill_model import (
        ConservativeFillConfig,
        evaluate_conservative_fill,
    )
    from quant_os.replay.prediction_market_replay_inputs import normalize_replay_inputs

    orderbook_event = next(
        event
        for event in normalize_replay_inputs(polymarket_snapshot_path=POLYMARKET_SNAPSHOT)
        if event.event_type == "orderbook_snapshot"
    )
    intent = ShadowOrderIntent(
        timestamp="2025-01-01T00:00:01+00:00",
        lane_id="prediction_market_replay_input_infrastructure",
        market_id=orderbook_event.market_id,
        token_id=orderbook_event.token_id,
        side="BUY",
        intended_size="4",
        limit_price="0.45",
        price_discipline="cross_best_ask_with_penalties",
        reason="fill-model-regression",
        signal_family="fixture_replay_shape",
    )

    fill = evaluate_conservative_fill(intent=intent, orderbook_event=orderbook_event)

    assert fill["fill_status"] == "PARTIAL_FILL_CONSERVATIVE"
    assert fill["filled_size"] == "3"
    assert fill["filled_size"] < intent.intended_size
    assert fill["effective_price"] > orderbook_event.best_ask_price
    assert "latency_penalty_bps" in fill["deterministic_assumptions"]
    assert "queue_position_unknown" in fill["unknowns"]

    try:
        ConservativeFillConfig(max_fill_fraction="1.0", allow_full_fill=True)
    except ValueError as exc:
        assert "optimistic" in str(exc).lower()
    else:  # pragma: no cover - the model must reject this path
        raise AssertionError("optimistic fill assumptions must be rejected")


def test_sequence31_shadow_policy_produces_blocked_intents_without_authority(
    local_project: Path,
) -> None:
    from quant_os.execution.shadow_execution_policy import generate_shadow_order_intents
    from quant_os.replay.prediction_market_replay_design import write_replay_design_report

    design = write_replay_design_report(
        output_root=local_project,
        polymarket_snapshot_path=POLYMARKET_SNAPSHOT,
        pmxt_manifest_path=PMXT_MANIFEST,
        reference_datasets_manifest_path=REFERENCE_DATASETS,
    )
    intents = generate_shadow_order_intents(replay_design=design)
    intent_dicts = [intent.to_report_dict() for intent in intents]

    assert intent_dicts
    assert all(intent["execution_authority"] == "NONE" for intent in intent_dicts)
    assert all(intent["live_trading_enabled"] is False for intent in intent_dicts)
    assert all(intent["status"] == "BLOCKED" for intent in intent_dicts)
    assert any("CONFIDENCE_TOO_WEAK" in intent["blocking_reasons"] for intent in intent_dicts)
    assert any("REPLAY_INPUT_INSUFFICIENT" in intent["blocking_reasons"] for intent in intent_dicts)


def test_sequence31_shadow_risk_envelope_fails_closed() -> None:
    from quant_os.execution.shadow_order_intents import ShadowOrderIntent
    from quant_os.execution.shadow_risk import ShadowRiskLimits, evaluate_shadow_risk

    intent = ShadowOrderIntent(
        timestamp="2025-01-01T00:00:01+00:00",
        lane_id="prediction_market_replay_input_infrastructure",
        market_id="0xabc",
        token_id="yes-token",
        side="BUY",
        intended_size="2",
        limit_price="0.45",
        price_discipline="cross_best_ask_with_penalties",
        reason="risk-regression",
        signal_family="fixture_replay_shape",
    )

    result = evaluate_shadow_risk(
        intent=intent,
        limits=ShadowRiskLimits(),
        current_intent_count=0,
        current_market_exposure="0",
        replay_inputs_sufficient=False,
    )

    assert result["risk_status"] == "RISK_BLOCKED"
    assert "KILL_STATE_REPLAY_INPUTS_INSUFFICIENT" in result["blocking_reasons"]
    assert result["live_trading_enabled"] is False
    assert result["execution_authority"] == "NONE"


def test_sequence31_shadow_execution_report_is_conservative(
    local_project: Path,
) -> None:
    from quant_os.research.prediction_markets.shadow_execution_report import (
        write_shadow_execution_report,
    )

    payload = write_shadow_execution_report(
        output_root=local_project,
        polymarket_snapshot_path=POLYMARKET_SNAPSHOT,
        pmxt_manifest_path=PMXT_MANIFEST,
        reference_datasets_manifest_path=REFERENCE_DATASETS,
    )

    assert payload["shadow_execution_status"] == "SHADOW_EXECUTION_NOT_JUSTIFIED"
    assert payload["metrics"]["intent_count"] >= 1
    assert payload["metrics"]["blocked_trade_count"] == payload["metrics"]["intent_count"]
    assert payload["metrics"]["fill_rate"] == "0"
    assert "INTENTS_TOO_THIN" in payload["blockers"]
    assert "RISK_BLOCKS_SHADOW_AUTONOMY" in payload["blockers"]
    assert payload["live_trading_enabled"] is False
    assert payload["prediction_market_execution_authority_added"] is False


def test_sequence31_shadow_autonomy_gate_requires_hard_evidence(
    local_project: Path,
) -> None:
    from quant_os.readiness.shadow_autonomy_report import write_shadow_autonomy_report

    payload = write_shadow_autonomy_report(
        output_root=local_project,
        polymarket_snapshot_path=POLYMARKET_SNAPSHOT,
        pmxt_manifest_path=PMXT_MANIFEST,
        reference_datasets_manifest_path=REFERENCE_DATASETS,
    )

    assert payload["shadow_autonomy_status"] == "SHADOW_EXECUTION_NOT_JUSTIFIED"
    assert payload["ready_for_bounded_shadow_autonomy"] is False
    assert payload["not_live_readiness"] is True
    assert payload["requirements"]["normalized_replay_inputs"] is True
    assert payload["requirements"]["conservative_fill_model"] is True
    assert payload["requirements"]["deterministic_shadow_policy"] is True
    assert payload["requirements"]["no_optimistic_fill_assumption"] is True
    assert payload["requirements"]["credible_signal_for_shadow"] is False
    assert payload["requirements"]["no_weak_signal_promotion"] is True
    assert payload["live_trading_enabled"] is False
    assert payload["execution_authority"] == "NONE"


def test_sequence31_cli_commands_are_fixture_safe_and_non_executing(
    local_project: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = {
        **os.environ,
        "PYTHONPATH": str(repo_root / "src"),
    }
    commands = [
        [
            sys.executable,
            "-m",
            "quant_os.cli",
            "replay",
            "design-report",
            "--polymarket-snapshot-path",
            str(POLYMARKET_SNAPSHOT),
            "--pmxt-manifest-path",
            str(PMXT_MANIFEST),
            "--reference-datasets-manifest-path",
            str(REFERENCE_DATASETS),
        ],
        [
            sys.executable,
            "-m",
            "quant_os.cli",
            "replay",
            "shadow-execution-report",
            "--polymarket-snapshot-path",
            str(POLYMARKET_SNAPSHOT),
            "--pmxt-manifest-path",
            str(PMXT_MANIFEST),
            "--reference-datasets-manifest-path",
            str(REFERENCE_DATASETS),
        ],
        [
            sys.executable,
            "-m",
            "quant_os.cli",
            "readiness",
            "shadow-autonomy",
            "--polymarket-snapshot-path",
            str(POLYMARKET_SNAPSHOT),
            "--pmxt-manifest-path",
            str(PMXT_MANIFEST),
            "--reference-datasets-manifest-path",
            str(REFERENCE_DATASETS),
        ],
    ]

    for command in commands:
        result = subprocess.run(
            command,
            cwd=local_project,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        assert "live_trading_enabled" in result.stdout
        assert "False" in result.stdout
        assert "execution_authority" in result.stdout
        assert "NONE" in result.stdout
