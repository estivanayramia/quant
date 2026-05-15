from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_sequence49_profit_lane_tournament_is_deterministic(local_project: Path) -> None:
    from quant_os.research.lane_selection.profit_lane_tournament import (
        build_profit_lane_tournament,
        write_profit_lane_tournament_report,
    )

    first = write_profit_lane_tournament_report(output_root=local_project)
    first_text = Path(first["report_paths"]["json"]).read_text(encoding="utf-8")
    second = write_profit_lane_tournament_report(output_root=local_project)
    second_text = Path(second["report_paths"]["json"]).read_text(encoding="utf-8")
    payload = build_profit_lane_tournament()

    assert first_text == second_text
    assert payload["schema_version"] == "profit_lane_tournament_v1"
    assert payload["sequence"] == "49"
    assert payload["tournament_status"] == "SELECTED_LANE_NEEDS_DATA_CAPTURE"
    assert payload["selected_lane_id"] == "pm_weather_forecast_market_mismatch"
    assert payload["selected_lane"]["promotion_status"] == "PROMOTE_TO_DATA_CAPTURE"
    assert payload["selected_lane"]["total_score"] == max(
        lane["total_score"] for lane in payload["lanes"]
    )
    assert payload["live_trading_enabled"] is False
    assert payload["execution_authority"] == "NONE"


def test_sequence49_unsafe_auth_copy_and_leverage_lanes_cannot_promote() -> None:
    from quant_os.research.lane_selection.profit_lane_tournament import (
        BLOCKED_EXECUTION_UNSAFE,
        BLOCKED_SOURCE_UNAVAILABLE,
        RESEARCH_ONLY,
        build_profit_lane_tournament,
    )

    payload = build_profit_lane_tournament()
    lanes = {lane["lane_id"]: lane for lane in payload["lanes"]}

    assert lanes["pm_lp_refresh_lag_arbitrage"]["promotion_status"] == (
        BLOCKED_SOURCE_UNAVAILABLE
    )
    assert lanes["pm_lp_refresh_lag_arbitrage"]["blockers"] == [
        "BLOCKED_MISSING_PUBLIC_FILL_ATTRIBUTION"
    ]
    assert lanes["funding_basis_arbitrage"]["promotion_status"] == RESEARCH_ONLY
    assert lanes["funding_basis_arbitrage"]["requires_futures_or_margin"] is True
    assert lanes["defi_cex_dex_arbitrage"]["promotion_status"] == BLOCKED_EXECUTION_UNSAFE
    assert lanes["defi_cex_dex_arbitrage"]["requires_wallet_or_signing"] is True
    assert lanes["crypto_cross_exchange_spot_arbitrage"]["promotion_status"] == RESEARCH_ONLY
    assert all(
        lane["promotion_status"] not in {"PROMOTE_TO_PAPER_PROVING", "PROMOTE_TO_DATA_CAPTURE"}
        for lane in lanes.values()
        if lane["requires_private_auth"]
        or lane["requires_wallet_or_signing"]
        or lane["copy_trade_dependency"]
    )


def test_sequence49_selected_lane_is_score_driven_not_hardcoded() -> None:
    from quant_os.research.lane_selection.profit_lane_tournament import (
        PROMOTE_TO_PAPER_PROVING,
        build_profit_lane_tournament,
    )

    payload = build_profit_lane_tournament(
        lane_overrides={
            "crypto_stat_arb_pairs": {
                "evidence": {"historical_depth": 5, "replayability": 5},
                "trading_realism": {"spread_liquidity": 5, "cost_burden": 5},
                "validation": {"oos_walk_forward_feasibility": 5, "baseline_testability": 5},
                "safety_fit": {"time_to_honest_paper_evidence": 5, "complexity": 5},
                "promotion_status": PROMOTE_TO_PAPER_PROVING,
            }
        }
    )

    assert payload["selected_lane_id"] == "crypto_stat_arb_pairs"
    assert payload["tournament_status"] == "PAPER_PROVING_READY_FOR_SELECTED_LANE"


def test_sequence49_selected_lane_handoff_describes_data_and_rejections(
    local_project: Path,
) -> None:
    from quant_os.research.lane_selection.selected_profit_lane import (
        build_selected_profit_lane_handoff,
        write_selected_profit_lane_report,
    )

    payload = build_selected_profit_lane_handoff()
    report = write_selected_profit_lane_report(output_root=local_project)

    assert payload["selected_lane_id"] == "pm_weather_forecast_market_mismatch"
    assert "forecast snapshots" in payload["required_data"]
    assert "stale_forecast_placebo" in payload["required_tests"]
    assert "pm_lp_refresh_lag_arbitrage" in payload["why_others_not_selected"]
    assert payload["why_others_not_selected"]["pm_lp_refresh_lag_arbitrage"]["status"] == (
        "BLOCKED_SOURCE_UNAVAILABLE"
    )
    assert payload["paper_proving_readiness"] == "SELECTED_LANE_NEEDS_DATA_CAPTURE"
    assert payload["exact_next_command"] == (
        "python -m quant_os.cli research selected-profit-lane"
    )
    assert Path(report["report_paths"]["json"]).exists()
    assert Path(report["report_paths"]["markdown"]).exists()


def test_sequence49_paper_proving_harness_includes_costs_fills_baselines_and_placebos(
    local_project: Path,
) -> None:
    from quant_os.proving.paper_proving_harness import (
        build_default_paper_proving_input,
        run_paper_proving,
    )
    from quant_os.proving.paper_proving_report import write_paper_proving_report

    payload = run_paper_proving(build_default_paper_proving_input())
    report = write_paper_proving_report(output_root=local_project)

    assert payload["lane_id"] == "pm_weather_forecast_market_mismatch"
    assert payload["readiness_status"] == "PAPER_PROFIT_DIAGNOSTIC_ONLY"
    assert payload["cost_model"]["fee_bps"] > 0
    assert payload["costs_included"] is True
    assert payload["fill_model"]["assumption"] == "conservative_partial_fill"
    assert payload["fill_assumptions_included"] is True
    assert payload["baseline_comparison"]["included"] is True
    assert payload["placebo_comparison"]["included"] is True
    assert payload["sample_warnings"] == ["SAMPLE_TOO_THIN"]
    assert "PAPER_ONLY_NOT_LIVE" in payload["warnings"]
    assert "SIMULATED_FILLS_NOT_REAL_FILLS" in payload["warnings"]
    assert "NO_LIVE_AUTHORITY" in payload["warnings"]
    assert payload["live_trading_enabled"] is False
    assert payload["execution_authority"] == "NONE"
    assert Path(report["report_paths"]["json"]).exists()
    assert Path(report["report_paths"]["markdown"]).exists()


def test_sequence49_profit_claim_guard_blocks_weak_profit_claims(local_project: Path) -> None:
    from quant_os.proving.paper_proving_harness import (
        build_default_paper_proving_input,
        run_paper_proving,
    )
    from quant_os.proving.profit_claim_guard import (
        evaluate_profit_claim_guard,
        write_profit_claim_guard_report,
    )

    paper = run_paper_proving(build_default_paper_proving_input())
    guard = evaluate_profit_claim_guard(paper)
    report = write_profit_claim_guard_report(output_root=local_project)

    assert guard["claim_status"] == "NO_PROFIT_CLAIM_ALLOWED"
    assert "SYNTHETIC_ONLY_DATA" in guard["blockers"]
    assert "SAMPLE_TOO_THIN" in guard["blockers"]
    assert "OOS_WALK_FORWARD_MISSING" in guard["blockers"]
    assert "ONE_ROW_DOMINANCE" in guard["blockers"]
    assert guard["profitable_label_allowed"] is False
    assert guard["live_ready_label_allowed"] is False
    assert guard["allowed_statuses"] == [
        "PAPER_PROFIT_DIAGNOSTIC_ONLY",
        "PAPER_PROFIT_CANDIDATE",
        "PAPER_PROFIT_BLOCKED",
        "NO_PROFIT_CLAIM_ALLOWED",
    ]
    rendered_statuses = " ".join(
        [guard["claim_status"], paper["readiness_status"], *guard["allowed_statuses"]]
    )
    assert "PROFITABLE" not in rendered_statuses
    assert "LIVE_READY" not in rendered_statuses
    assert Path(report["report_paths"]["json"]).exists()
    assert Path(report["report_paths"]["markdown"]).exists()


def test_sequence49_guard_blocks_missing_comparisons_and_costs() -> None:
    from quant_os.proving.paper_proving_harness import (
        build_default_paper_proving_input,
        run_paper_proving,
    )
    from quant_os.proving.profit_claim_guard import evaluate_profit_claim_guard

    paper = run_paper_proving(
        build_default_paper_proving_input(
            cost_model={"fee_bps": 0.0, "spread_bps": 0.0, "slippage_bps": 0.0},
            fill_model=None,
            baseline_rows=[],
            placebo_rows=[],
        )
    )
    guard = evaluate_profit_claim_guard(paper)

    assert paper["readiness_status"] == "PAPER_PROFIT_BLOCKED_BY_COSTS"
    assert "COST_MODEL_MISSING" in guard["blockers"]
    assert "FILL_MODEL_MISSING" in guard["blockers"]
    assert "BASELINE_COMPARISON_MISSING" in guard["blockers"]
    assert "PLACEBO_COMPARISON_MISSING" in guard["blockers"]
    assert guard["claim_status"] == "NO_PROFIT_CLAIM_ALLOWED"


def test_sequence49_cli_make_targets_and_forbidden_paths_are_non_executing(
    local_project: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = {
        **os.environ,
        "PYTHONPATH": str(repo_root / "src"),
    }
    commands = [
        [sys.executable, "-m", "quant_os.cli", "research", "profit-lane-tournament"],
        [sys.executable, "-m", "quant_os.cli", "research", "selected-profit-lane"],
        [sys.executable, "-m", "quant_os.cli", "proving", "paper-proving-report"],
        [sys.executable, "-m", "quant_os.cli", "proving", "profit-claim-guard"],
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
    assert 'if "%TARGET%"=="profit-lane-tournament-smoke"' in make_cmd
    assert 'if "%TARGET%"=="paper-proving-smoke"' in make_cmd
    assert 'if "%TARGET%"=="sequence49-smoke"' in make_cmd

    source_paths = [
        "src/quant_os/research/lane_selection/profit_lane_tournament.py",
        "src/quant_os/research/lane_selection/selected_profit_lane.py",
        "src/quant_os/proving/paper_proving_models.py",
        "src/quant_os/proving/paper_proving_harness.py",
        "src/quant_os/proving/paper_proving_report.py",
        "src/quant_os/proving/profit_claim_guard.py",
        "src/quant_os/cli.py",
    ]
    forbidden_tokens = [
        "create_order(",
        "cancel_order(",
        "post_order(",
        "place_order(",
        "sign_order(",
        "wallet_signer",
        "authenticated_client",
        "bypass_captcha(",
        "proxy_evasion(",
        "copy_trade(",
        "mirror_wallet(",
    ]
    for source_path in source_paths:
        text = (repo_root / source_path).read_text(encoding="utf-8").lower()
        for token in forbidden_tokens:
            assert token not in text
