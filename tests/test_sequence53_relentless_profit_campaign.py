from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def _candidate_report(**overrides: object) -> dict[str, object]:
    report: dict[str, object] = {
        "schema_version": "paper_proving_report_v1",
        "lane_id": "crypto_spot_momentum_reversion_intraday",
        "source_quality_tier": "PUBLIC_REPLAY",
        "proof_row_count": 36,
        "trade_count": 36,
        "minimum_sample_size": 30,
        "labels_valid": True,
        "no_lookahead": True,
        "costs_included": True,
        "cost_model": {"fee_bps": 8.0, "spread_bps": 12.0, "slippage_bps": 18.0},
        "fill_assumptions_included": True,
        "fill_model": {"assumption": "conservative_partial_fill", "fill_ratio": 0.5},
        "baseline_comparison": {"included": True, "paper_beats_comparison": True},
        "placebo_comparison": {"included": True, "paper_beats_comparison": True},
        "one_row_dominance": {"detected": False, "dominance_ratio": "0.12"},
        "oos_walk_forward_status": "OOS_WALK_FORWARD_AVAILABLE",
        "net_simulated_pnl_after_costs": "12.5",
        "requires_private_or_authenticated_data": False,
        "copy_trading_enabled": False,
        "wallet_signing_enabled": False,
        "requires_leverage": False,
        "requires_futures_or_margin": False,
        "requires_options": False,
        "live_trading_enabled": False,
        "execution_authority": "NONE",
        "synthetic_rows_counted_as_profit_evidence": False,
        "reproducible_commands": [
            "python -m quant_os.cli proving relentless-profit-campaign-run"
        ],
    }
    report.update(overrides)
    return report


def test_sequence53_campaign_state_rehydrates_correctly(local_project: Path) -> None:
    from quant_os.proving.relentless_profit_campaign_state import (
        default_campaign_state,
        load_campaign_state,
        write_campaign_state,
    )

    state = default_campaign_state(current_branch="phase-53-relentless-profit-campaign")
    state["active_lane"] = "pm_weather_forecast_market_mismatch"
    state["lanes_attempted"] = ["pm_weather_forecast_market_mismatch"]
    state["blockers"] = {"pm_weather_forecast_market_mismatch": ["SAMPLE_TOO_THIN"]}

    write_campaign_state(state, output_root=local_project)
    rehydrated = load_campaign_state(output_root=local_project)

    assert rehydrated["current_branch"] == "phase-53-relentless-profit-campaign"
    assert rehydrated["active_lane"] == "pm_weather_forecast_market_mismatch"
    assert rehydrated["lanes_attempted"] == ["pm_weather_forecast_market_mismatch"]
    assert rehydrated["blockers"]["pm_weather_forecast_market_mismatch"] == ["SAMPLE_TOO_THIN"]
    assert Path(rehydrated["report_paths"]["json"]).exists()
    assert Path(rehydrated["report_paths"]["markdown"]).exists()


def test_sequence53_lane_scoring_is_deterministic() -> None:
    from quant_os.research.lane_selection.relentless_profit_campaign_engine import (
        score_campaign_lanes,
    )
    from quant_os.research.lane_selection.relentless_profit_campaign_models import (
        build_initial_lane_universe,
    )

    first = score_campaign_lanes(build_initial_lane_universe())
    second = score_campaign_lanes(build_initial_lane_universe())

    assert first == second
    assert len(first) == 35
    assert first[0]["lane_id"] == "pm_weather_forecast_market_mismatch"
    assert first[0]["score"] >= first[-1]["score"]


def test_sequence53_failed_lanes_are_not_repeated_unless_blocker_changes() -> None:
    from quant_os.proving.relentless_profit_campaign_state import default_campaign_state
    from quant_os.research.lane_selection.relentless_profit_campaign_engine import (
        select_next_lane,
    )
    from quant_os.research.lane_selection.relentless_profit_campaign_models import (
        build_initial_lane_universe,
    )

    lanes = build_initial_lane_universe()
    state = default_campaign_state()
    state["lanes_attempted"] = ["pm_weather_forecast_market_mismatch"]
    state["lane_blocker_signatures"] = {
        "pm_weather_forecast_market_mismatch": "HISTORICAL_FORECAST_SNAPSHOTS_MISSING"
    }

    selected = select_next_lane(lanes, state)
    assert selected is not None
    assert selected["lane_id"] != "pm_weather_forecast_market_mismatch"

    changed = default_campaign_state()
    changed["lanes_attempted"] = ["pm_weather_forecast_market_mismatch"]
    changed["lane_blocker_signatures"] = {
        "pm_weather_forecast_market_mismatch": "OLD_BLOCKER"
    }
    selected_changed = select_next_lane(lanes, changed)
    assert selected_changed is not None
    assert selected_changed["lane_id"] == "pm_weather_forecast_market_mismatch"


def test_sequence53_safe_queue_expansion_works_and_unsafe_expansion_is_rejected() -> None:
    from quant_os.research.lane_selection.relentless_profit_campaign_engine import (
        expand_safe_lane_queue,
    )

    expansion = expand_safe_lane_queue(
        [
            {
                "lane_id": "macro_event_etf_reaction_paper_only",
                "family": "equity_etf_paper",
                "public_data_available": True,
                "requires_private_auth": False,
                "requires_wallet_or_signing": False,
                "requires_live_execution": False,
                "requires_paid_api": False,
                "requires_evasion": False,
                "requires_futures_or_margin": False,
                "copy_trade_dependency": False,
            },
            {
                "lane_id": "broker_orderflow_copy_trade",
                "family": "unsafe",
                "public_data_available": False,
                "requires_private_auth": True,
                "requires_wallet_or_signing": False,
                "requires_live_execution": True,
                "requires_paid_api": False,
                "requires_evasion": False,
                "requires_futures_or_margin": False,
                "copy_trade_dependency": True,
            },
        ]
    )

    assert [lane["lane_id"] for lane in expansion["added"]] == [
        "macro_event_etf_reaction_paper_only"
    ]
    assert [lane["lane_id"] for lane in expansion["rejected"]] == ["broker_orderflow_copy_trade"]
    assert "PRIVATE_OR_AUTHENTICATED_SOURCE_REQUIRED" in expansion["rejected"][0]["blockers"]
    assert "COPY_TRADE_DEPENDENCY_FORBIDDEN" in expansion["rejected"][0]["blockers"]


def test_sequence53_weather_cannot_use_realized_values_as_forecasts() -> None:
    from quant_os.research.lane_selection.relentless_profit_campaign_engine import (
        validate_weather_forecast_inputs,
    )

    result = validate_weather_forecast_inputs(
        {
            "forecast_source": "realized_weather_resolution",
            "forecast_ts": "2026-05-16T23:00:00Z",
            "orderbook_ts": "2026-05-16T12:00:00Z",
            "uses_resolution_as_forecast": True,
        }
    )

    assert result["valid"] is False
    assert "REALIZED_WEATHER_CANNOT_BE_FORECAST" in result["blockers"]
    assert "FORECAST_AFTER_ORDERBOOK" in result["blockers"]


def test_sequence53_weather_blocks_missing_historical_forecast_snapshots() -> None:
    from quant_os.research.lane_selection.relentless_profit_campaign_engine import attempt_lane
    from quant_os.research.lane_selection.relentless_profit_campaign_models import (
        lane_by_id,
    )

    attempt = attempt_lane(lane_by_id("pm_weather_forecast_market_mismatch"))

    assert attempt["status"] == "NEEDS_FORWARD_DATA_CAPTURE"
    assert "HISTORICAL_FORECAST_SNAPSHOTS_MISSING" in attempt["blockers"]
    assert attempt["proof_rows_created"] == 0
    assert attempt["paper_profit_candidate"] is False


def test_sequence53_structural_prediction_market_lanes_require_validated_relations() -> None:
    from quant_os.research.lane_selection.relentless_profit_campaign_engine import attempt_lane
    from quant_os.research.lane_selection.relentless_profit_campaign_models import lane_by_id

    attempt = attempt_lane(lane_by_id("pm_negation_pair_arbitrage"))

    assert attempt["status"] == "CONTINUE_TO_NEXT_LANE"
    assert "VALIDATED_SEMANTIC_RELATION_MISSING" in attempt["blockers"]
    assert attempt["paper_profit_candidate"] is False


def test_sequence53_crypto_spot_lanes_are_paper_only_and_spot_only() -> None:
    from quant_os.research.lane_selection.relentless_profit_campaign_models import lane_by_id

    lane = lane_by_id("crypto_spot_momentum_reversion_intraday")

    assert lane["family"] == "crypto_spot"
    assert lane["paper_only"] is True
    assert lane["spot_only"] is True
    assert lane["requires_futures_or_margin"] is False
    assert lane["requires_leverage"] is False
    assert lane["allows_shorting"] is False


def test_sequence53_equity_etf_lanes_are_paper_only_and_no_broker() -> None:
    from quant_os.research.lane_selection.relentless_profit_campaign_models import lane_by_id

    lane = lane_by_id("spy_qqq_relative_strength_rotation")

    assert lane["family"] == "equity_etf_paper"
    assert lane["paper_only"] is True
    assert lane["requires_broker_credentials"] is False
    assert lane["requires_live_execution"] is False
    assert lane["allows_shorting"] is False


def test_sequence53_research_only_lanes_cannot_promote() -> None:
    from quant_os.research.lane_selection.relentless_profit_campaign_engine import attempt_lane
    from quant_os.research.lane_selection.relentless_profit_campaign_models import lane_by_id

    attempt = attempt_lane(lane_by_id("funding_basis_arbitrage"))

    assert attempt["status"] == "CONTINUE_TO_NEXT_LANE"
    assert attempt["promotion_allowed"] is False
    assert "RESEARCH_ONLY_LANE_CANNOT_PROMOTE" in attempt["blockers"]
    assert "FUTURES_LEVERAGE_OR_MARGIN_OUT_OF_SCOPE" in attempt["blockers"]


def test_sequence53_campaign_loop_is_bounded_per_run_but_resumable(local_project: Path) -> None:
    from quant_os.proving.relentless_profit_campaign_runner import run_relentless_profit_campaign

    first = run_relentless_profit_campaign(output_root=local_project, max_lanes=2)
    second = run_relentless_profit_campaign(output_root=local_project, max_lanes=2)

    assert first["run_summary"]["lanes_attempted_this_run"] == 2
    assert second["run_summary"]["lanes_attempted_this_run"] == 2
    assert len(second["state"]["lanes_attempted"]) == 4
    assert first["campaign_status"] == "CAMPAIGN_CHECKPOINTED_NOT_COMPLETE"
    assert second["state"]["exact_resume_command"] == (
        "python -m quant_os.cli proving relentless-profit-campaign-run"
    )


def test_sequence53_no_new_expansion_lanes_preserves_tool_limit_checkpoint(
    local_project: Path,
) -> None:
    from quant_os.proving.relentless_profit_campaign_runner import run_relentless_profit_campaign

    exhausted = run_relentless_profit_campaign(output_root=local_project, max_lanes=100)
    resumed = run_relentless_profit_campaign(output_root=local_project, max_lanes=1)

    assert exhausted["paper_profit_status"] == "TOOL_OR_CONTEXT_LIMIT_REACHED"
    assert resumed["paper_profit_status"] == "TOOL_OR_CONTEXT_LIMIT_REACHED"
    assert resumed["run_summary"]["lanes_attempted_this_run"] == 0
    assert resumed["state"]["next_action"] == (
        "Research another safe public-data-compatible expansion tranche, then resume."
    )


def test_sequence53_no_no_edge_status_can_mark_campaign_complete() -> None:
    from quant_os.research.lane_selection.relentless_profit_campaign_engine import (
        is_campaign_complete_status,
    )
    from quant_os.research.lane_selection.relentless_profit_campaign_models import (
        FORBIDDEN_COMPLETION_STATUSES,
    )

    assert is_campaign_complete_status("PAPER_PROFIT_CANDIDATE_FOUND") is True
    for status in FORBIDDEN_COMPLETION_STATUSES:
        assert is_campaign_complete_status(status) is False


def test_sequence53_profit_guard_blocks_synthetic_only_results() -> None:
    from quant_os.proving.relentless_profit_guard import evaluate_relentless_profit_guard

    guard = evaluate_relentless_profit_guard(
        _candidate_report(source_quality_tier="SYNTHETIC_ONLY")
    )

    assert guard["claim_status"] == "NO_PROFIT_CLAIM_ALLOWED"
    assert "SYNTHETIC_ONLY_DATA" in guard["blockers"]


def test_sequence53_profit_guard_blocks_missing_costs_fills_baselines_and_placebos() -> None:
    from quant_os.proving.relentless_profit_guard import evaluate_relentless_profit_guard

    guard = evaluate_relentless_profit_guard(
        _candidate_report(
            costs_included=False,
            fill_assumptions_included=False,
            baseline_comparison={"included": False},
            placebo_comparison={"included": False},
        )
    )

    assert guard["claim_status"] == "NO_PROFIT_CLAIM_ALLOWED"
    assert "COST_MODEL_MISSING" in guard["blockers"]
    assert "FILL_MODEL_MISSING" in guard["blockers"]
    assert "BASELINE_COMPARISON_MISSING" in guard["blockers"]
    assert "PLACEBO_COMPARISON_MISSING" in guard["blockers"]


def test_sequence53_profit_guard_blocks_one_row_dominance() -> None:
    from quant_os.proving.relentless_profit_guard import evaluate_relentless_profit_guard

    guard = evaluate_relentless_profit_guard(
        _candidate_report(one_row_dominance={"detected": True, "dominance_ratio": "0.91"})
    )

    assert guard["claim_status"] == "NO_PROFIT_CLAIM_ALLOWED"
    assert "ONE_ROW_DOMINANCE" in guard["blockers"]


def test_sequence53_profit_guard_blocks_unavailable_private_auth_data_dependency() -> None:
    from quant_os.proving.relentless_profit_guard import evaluate_relentless_profit_guard

    guard = evaluate_relentless_profit_guard(
        _candidate_report(requires_private_or_authenticated_data=True)
    )

    assert guard["claim_status"] == "NO_PROFIT_CLAIM_ALLOWED"
    assert "PRIVATE_OR_AUTHENTICATED_DATA_DEPENDENCY" in guard["blockers"]


def test_sequence53_profit_guard_blocks_leverage_futures_margin_and_options_lanes() -> None:
    from quant_os.proving.relentless_profit_guard import evaluate_relentless_profit_guard

    guard = evaluate_relentless_profit_guard(
        _candidate_report(
            requires_leverage=True,
            requires_futures_or_margin=True,
            requires_options=True,
        )
    )

    assert guard["claim_status"] == "NO_PROFIT_CLAIM_ALLOWED"
    assert "LEVERAGE_FUTURES_MARGIN_OR_OPTIONS_DEPENDENCY" in guard["blockers"]


def test_sequence53_paper_profit_candidate_requires_all_gates() -> None:
    from quant_os.proving.relentless_profit_guard import evaluate_relentless_profit_guard

    guard = evaluate_relentless_profit_guard(_candidate_report())

    assert guard["claim_status"] == "PAPER_PROFIT_CANDIDATE"
    assert guard["all_required_gates_passed"] is True
    assert guard["paper_profit_candidate"] is True
    assert guard["profitable_label_allowed"] is False
    assert guard["live_ready_label_allowed"] is False


def test_sequence53_no_live_or_canary_readiness_is_claimed(local_project: Path) -> None:
    from quant_os.proving.relentless_profit_campaign_runner import run_relentless_profit_campaign

    payload = run_relentless_profit_campaign(output_root=local_project, max_lanes=1)

    assert payload["live_trading_enabled"] is False
    assert payload["execution_authority"] == "NONE"
    assert payload["live_ready"] is False
    assert payload["canary_ready"] is False
    assert payload["live_readiness_claimed"] is False
    assert payload["canary_readiness_claimed"] is False


def test_sequence53_no_auth_signing_order_cancel_wallet_copytrade_or_evasion_path_introduced() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_paths = [
        "src/quant_os/research/lane_selection/relentless_profit_campaign_models.py",
        "src/quant_os/research/lane_selection/relentless_profit_campaign_engine.py",
        "src/quant_os/research/lane_selection/relentless_profit_campaign_report.py",
        "src/quant_os/proving/relentless_profit_campaign_runner.py",
        "src/quant_os/proving/relentless_profit_campaign_state.py",
        "src/quant_os/proving/relentless_profit_guard.py",
        "src/quant_os/autonomy/forward_capture_plan.py",
        "src/quant_os/readiness/profit_candidate_autonomy_path.py",
    ]
    forbidden_tokens = [
        "create_order(",
        "cancel_order(",
        "post_order(",
        "place_order(",
        "sign_order(",
        "wallet_signer",
        "authenticated_client",
        "auth_header",
        "private_key",
        "bypass_captcha(",
        "proxy_evasion(",
        "copy_trade(",
        "mirror_wallet(",
    ]

    for source_path in source_paths:
        text = (repo_root / source_path).read_text(encoding="utf-8").lower()
        for token in forbidden_tokens:
            assert token not in text


def test_sequence53_forward_capture_plan_is_data_only(local_project: Path) -> None:
    from quant_os.autonomy.forward_capture_plan import write_forward_capture_plan

    plan = write_forward_capture_plan(output_root=local_project)

    assert plan["status"] == "FORWARD_CAPTURE_PLAN_READY"
    assert plan["data_only"] is True
    assert plan["live_trading_enabled"] is False
    assert plan["execution_authority"] == "NONE"
    assert "schtasks /Create" in plan["windows_task_scheduler_command"]
    assert Path(plan["report_paths"]["json"]).exists()
    assert Path(plan["report_paths"]["markdown"]).exists()


def test_sequence53_cli_make_targets_are_fixture_safe(local_project: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = {
        **os.environ,
        "PYTHONPATH": str(repo_root / "src"),
    }
    commands = [
        [sys.executable, "-m", "quant_os.cli", "research", "relentless-profit-campaign"],
        [sys.executable, "-m", "quant_os.cli", "proving", "relentless-profit-campaign-run"],
        [sys.executable, "-m", "quant_os.cli", "proving", "relentless-profit-campaign-state"],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "forward-capture-plan"],
        [sys.executable, "-m", "quant_os.cli", "readiness", "profit-candidate-autonomy-path"],
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

    make_cmd = (repo_root / "make.cmd").read_text(encoding="utf-8")
    assert 'if "%TARGET%"=="relentless-profit-campaign-smoke"' in make_cmd
    assert 'if "%TARGET%"=="sequence53-smoke"' in make_cmd


def test_sequence53_reports_and_state_are_written(local_project: Path) -> None:
    from quant_os.proving.relentless_profit_campaign_runner import run_relentless_profit_campaign

    payload = run_relentless_profit_campaign(output_root=local_project, max_lanes=3)
    report = json.loads(
        (local_project / "reports/profit_campaign/latest_profit_campaign.json").read_text(
            encoding="utf-8"
        )
    )
    state = json.loads(
        (local_project / "reports/profit_campaign/state/latest_state.json").read_text(
            encoding="utf-8"
        )
    )

    assert report["schema_version"] == "relentless_profit_campaign_v1"
    assert report["campaign_status"] == payload["campaign_status"]
    assert state["current_paper_status"] in {
        "CONTINUE_TO_NEXT_LANE",
        "NEEDS_FORWARD_DATA_CAPTURE",
        "EXPAND_SAFE_LANE_QUEUE",
        "CAMPAIGN_CHECKPOINTED_NOT_COMPLETE",
    }
    assert state["safety_constraints"]["live_trading_enabled"] is False
    assert state["forbidden_actions"]["wallets_private_keys_or_signing"] is True
