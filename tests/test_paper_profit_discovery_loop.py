from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_lane_tournament_is_deterministic_and_selects_by_score(local_project: Path) -> None:
    from quant_os.research.lane_selection.paper_profit_lane_models import (
        build_default_lane_universe,
        rank_paper_profit_lanes,
    )
    from quant_os.research.lane_selection.paper_profit_lane_report import (
        write_paper_profit_lane_tournament_report,
    )

    lanes = build_default_lane_universe()
    first = rank_paper_profit_lanes(lanes)
    second = rank_paper_profit_lanes(lanes)
    report = write_paper_profit_lane_tournament_report(output_root=local_project)

    assert [lane.to_report_dict() for lane in first] == [
        lane.to_report_dict() for lane in second
    ]
    assert first[0].lane_id == report["selected_lane_id"]
    assert first[0].total_score == max(lane.total_score for lane in first)
    assert first[0].status in {"PROMOTE_TO_DATA_CAPTURE", "PROMOTE_TO_PAPER_TEST"}
    assert first[0].lane_id == "pm_weather_forecast_market_mismatch"
    assert Path(report["report_paths"]["json"]).exists()
    assert Path(report["report_paths"]["markdown"]).exists()


def test_unsafe_auth_only_copy_trade_and_leverage_lanes_cannot_promote() -> None:
    from quant_os.research.lane_selection.paper_profit_lane_models import (
        build_default_lane_universe,
        rank_paper_profit_lanes,
    )

    ranked = {lane.lane_id: lane for lane in rank_paper_profit_lanes(build_default_lane_universe())}

    assert ranked["copy_trader_wallet_following_strategies"].status == (
        "BLOCKED_EXECUTION_UNSAFE"
    )
    assert ranked["copy_trader_wallet_following_strategies"].promotable is False
    assert ranked["funding_basis_arbitrage"].status == "RESEARCH_ONLY"
    assert ranked["funding_basis_arbitrage"].promotable is False
    assert "leverage_or_margin_or_futures_required" in ranked["funding_basis_arbitrage"].blockers
    assert ranked["options_volatility_arbitrage"].status == "RESEARCH_ONLY"
    assert ranked["options_volatility_arbitrage"].promotable is False


def test_lp_refresh_lag_source_blocker_prevents_promotion() -> None:
    from quant_os.research.lane_selection.paper_profit_lane_models import (
        build_default_lane_universe,
        rank_paper_profit_lanes,
    )

    ranked = {lane.lane_id: lane for lane in rank_paper_profit_lanes(build_default_lane_universe())}
    lp_lane = ranked["pm_lp_refresh_lag_arbitrage"]

    assert lp_lane.status == "BLOCKED_SOURCE_UNAVAILABLE"
    assert lp_lane.promotable is False
    assert "BLOCKED_MISSING_PUBLIC_FILL_ATTRIBUTION" in lp_lane.blockers


def test_discovery_loop_is_bounded_and_emits_diagnostic_candidate(local_project: Path) -> None:
    from quant_os.proving.paper_profit_discovery_loop import run_paper_profit_discovery_loop

    payload = run_paper_profit_discovery_loop(
        output_root=local_project,
        max_lanes=3,
        max_promoted_lanes=1,
        max_fixture_only_diagnostics=1,
    )

    assert payload["bounded_limits"] == {
        "max_lanes": 3,
        "max_promoted_lanes": 1,
        "max_fixture_only_diagnostics": 1,
    }
    assert payload["evaluated_lane_count"] <= 3
    assert payload["promoted_lane_count"] <= 1
    assert payload["fixture_only_diagnostic_count"] <= 1
    assert payload["selected_lane_id"] == "pm_weather_forecast_market_mismatch"
    assert payload["paper_profit_status"] == "PAPER_PROFIT_DIAGNOSTIC_ONLY"
    assert payload["live_trading_enabled"] is False
    assert payload["execution_authority"] == "NONE"
    assert Path(payload["report_paths"]["json"]).exists()
    assert Path(payload["report_paths"]["markdown"]).exists()


def test_weather_candidate_mini_pack_has_required_design() -> None:
    from quant_os.proving.paper_profit_discovery_loop import build_candidate_mini_pack

    mini_pack = build_candidate_mini_pack("pm_weather_forecast_market_mismatch")

    assert mini_pack["lane_id"] == "pm_weather_forecast_market_mismatch"
    assert {
        "forecast_snapshots",
        "forecast_timestamp",
        "market_metadata",
        "bucket_range_rules",
        "market_price_snapshots",
        "liquidity_spread",
        "resolution_labels",
    }.issubset(set(mini_pack["required_data"]))
    assert {
        "market_baseline",
        "forecast_baseline",
        "stale_forecast_placebo",
        "random_bucket_placebo",
        "timestamp_shift_placebo",
        "spread_liquidity_stress",
        "oos_by_event_date",
    }.issubset(set(mini_pack["required_tests"]))
    assert mini_pack["paper_only"] is True
    assert mini_pack["profit_claim_allowed"] is False


def test_paper_proving_harness_requires_costs_fills_baselines_and_placebos(
    local_project: Path,
) -> None:
    from quant_os.proving.paper_proving_harness import (
        build_fixture_safe_paper_proving_input,
        run_paper_proving_harness,
    )
    from quant_os.proving.paper_proving_report import write_paper_proving_report

    proving_input = build_fixture_safe_paper_proving_input(
        lane_id="pm_weather_forecast_market_mismatch"
    )
    result = run_paper_proving_harness(proving_input)
    report = write_paper_proving_report(output_root=local_project, proving_input=proving_input)

    assert result["cost_model_present"] is True
    assert result["fill_model_present"] is True
    assert result["baseline_comparison"]["baseline_count"] >= 2
    assert result["placebo_comparison"]["placebo_count"] >= 3
    assert "net_simulated_pnl_after_costs" in result
    assert "fill_adjusted_pnl" in result
    assert "COST_MODEL_ASSUMPTION" in result["warnings"]
    assert "SIMULATED_FILLS_NOT_REAL_FILLS" in result["warnings"]
    assert result["readiness_status"] == "PAPER_PROFIT_DIAGNOSTIC_ONLY"
    assert Path(report["report_paths"]["json"]).exists()
    assert Path(report["report_paths"]["markdown"]).exists()


def test_crypto_fixture_safe_input_uses_crypto_spot_shape() -> None:
    from quant_os.proving.paper_proving_harness import build_fixture_safe_paper_proving_input

    proving_input = build_fixture_safe_paper_proving_input(
        lane_id="btc_eth_relative_strength_rotation"
    )

    assert proving_input.lane_id == "btc_eth_relative_strength_rotation"
    assert proving_input.source_dependencies == ("public_spot_candle_design",)
    assert {row.provenance for row in proving_input.signals} == {
        "fixture_safe_crypto_spot_shape"
    }
    assert {row.signal for row in proving_input.signals} == {
        "btc_eth_relative_strength_rotation"
    }


def test_profit_claim_guard_blocks_synthetic_missing_oos_and_one_row_dominance(
    local_project: Path,
) -> None:
    from quant_os.proving.paper_proving_harness import (
        build_fixture_safe_paper_proving_input,
        run_paper_proving_harness,
    )
    from quant_os.proving.profit_claim_guard import (
        evaluate_profit_claim_guard,
        write_profit_claim_guard_report,
    )

    result = run_paper_proving_harness(
        build_fixture_safe_paper_proving_input(lane_id="pm_weather_forecast_market_mismatch")
    )
    guarded = evaluate_profit_claim_guard(
        {
            **result,
            "readiness_status": "PAPER_PROFIT_CANDIDATE",
            "oos_walk_forward_status": "MISSING",
            "one_row_dominance": True,
        }
    )
    report = write_profit_claim_guard_report(output_root=local_project, proving_result=result)

    assert guarded["guard_status"] == "NO_PROFIT_CLAIM_ALLOWED"
    assert "SYNTHETIC_ONLY_DATA" in guarded["blockers"]
    assert "OOS_WALK_FORWARD_MISSING" in guarded["blockers"]
    assert "ONE_ROW_DOMINANCE" in guarded["blockers"]
    assert guarded["live_trading_enabled"] is False
    assert guarded["execution_authority"] == "NONE"
    assert report["guard_status"] == "NO_PROFIT_CLAIM_ALLOWED"
    assert Path(report["report_paths"]["json"]).exists()
    assert Path(report["report_paths"]["markdown"]).exists()


def test_profit_claim_guard_blocks_private_auth_and_copy_trade_dependencies() -> None:
    from quant_os.proving.paper_proving_harness import (
        build_fixture_safe_paper_proving_input,
        run_paper_proving_harness,
    )
    from quant_os.proving.profit_claim_guard import evaluate_profit_claim_guard

    result = run_paper_proving_harness(
        build_fixture_safe_paper_proving_input(lane_id="pm_weather_forecast_market_mismatch")
    )
    guarded = evaluate_profit_claim_guard(
        {
            **result,
            "source_dependencies": ["private_authenticated_api", "wallet_mirroring"],
            "uses_copy_trade_or_wallet_mirroring": True,
            "uses_leverage_futures_or_margin": True,
        }
    )

    assert "UNAVAILABLE_PRIVATE_AUTH_DATA" in guarded["blockers"]
    assert "COPY_TRADE_OR_WALLET_MIRRORING" in guarded["blockers"]
    assert "LEVERAGE_FUTURES_MARGIN" in guarded["blockers"]
    assert guarded["guard_status"] == "NO_PROFIT_CLAIM_ALLOWED"


def test_no_live_canary_or_forbidden_authority_paths_are_introduced() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_paths = [
        repo_root / "src/quant_os/research/lane_selection/paper_profit_lane_models.py",
        repo_root / "src/quant_os/research/lane_selection/paper_profit_lane_report.py",
        repo_root / "src/quant_os/proving/paper_profit_discovery_loop.py",
        repo_root / "src/quant_os/proving/paper_proving_models.py",
        repo_root / "src/quant_os/proving/paper_proving_harness.py",
        repo_root / "src/quant_os/proving/paper_proving_report.py",
        repo_root / "src/quant_os/proving/profit_claim_guard.py",
        repo_root / "src/quant_os/cli.py",
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
        "live_ready",
        "canary_ready",
        "guaranteed",
        "profitable",
    ]

    for source_path in source_paths:
        assert source_path.exists(), source_path
        text = source_path.read_text(encoding="utf-8").lower()
        for token in forbidden_tokens:
            assert token not in text


def test_cli_and_make_targets_generate_reports(local_project: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = {
        **os.environ,
        "PYTHONPATH": str(repo_root / "src"),
    }
    commands = [
        [sys.executable, "-m", "quant_os.cli", "research", "paper-profit-lane-tournament"],
        [sys.executable, "-m", "quant_os.cli", "proving", "paper-profit-discovery-loop"],
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
    assert 'if "%TARGET%"=="paper-profit-lane-tournament-smoke"' in make_cmd
    assert 'if "%TARGET%"=="paper-profit-discovery-smoke"' in make_cmd
    assert "paper-profit-lane-tournament" in make_cmd
    assert "paper-profit-discovery-loop" in make_cmd
    assert "paper-proving-report" in make_cmd
    assert "profit-claim-guard" in make_cmd
    assert "tests/test_paper_profit_discovery_loop.py" in make_cmd
