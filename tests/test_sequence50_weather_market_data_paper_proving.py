from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURE_PATH = (
    Path("tests")
    / "fixtures"
    / "replay_candidates"
    / "weather_market_mismatch"
    / "fixture_only_rows.json"
)


def test_sequence50_weather_candidate_definition_is_deterministic(
    local_project: Path,
) -> None:
    from quant_os.research.replay_candidates.weather_market_mismatch_candidate import (
        build_weather_market_mismatch_candidate,
        write_weather_market_mismatch_candidate_report,
    )

    first = build_weather_market_mismatch_candidate()
    second = build_weather_market_mismatch_candidate()
    report = write_weather_market_mismatch_candidate_report(output_root=local_project)

    assert first == second
    assert first["candidate_id"] == "pm_weather_forecast_market_mismatch"
    assert first["hypothesis_status"] == "UNPROVEN_HYPOTHESIS_ONLY"
    assert "binary_yes_no_weather_bucket" in first["supported_market_types"]
    assert "range_bucket_weather_market" in first["supported_market_types"]
    assert {
        "market_implied_baseline",
        "forecast_baseline",
        "no_skill_baseline",
    }.issubset(set(first["baselines"]))
    assert {
        "stale_forecast_placebo",
        "random_bucket_placebo",
        "timestamp_shift_placebo",
        "sign_flip_mismatch_placebo",
    }.issubset(set(first["placebos"]))
    assert first["profit_claim_allowed"] is False
    assert Path(report["report_paths"]["json"]).exists()
    assert Path(report["report_paths"]["markdown"]).exists()


def test_sequence50_public_source_policy_rejects_paid_auth_and_unsafe_sources(
    local_project: Path,
) -> None:
    from quant_os.data.weather.weather_source_policy import (
        classify_weather_source,
        write_weather_source_policy_report,
    )

    report = write_weather_source_policy_report(output_root=local_project)

    assert classify_weather_source("nws_api") == "PUBLIC_READ_ONLY_RATE_LIMITED"
    assert classify_weather_source("open_meteo_free_forecast") == (
        "PUBLIC_READ_ONLY_RATE_LIMITED"
    )
    assert classify_weather_source("manual_local_capture") == "MANUAL_CAPTURE_ALLOWED"
    assert classify_weather_source("open_meteo_paid_subscription") == "PAID_OR_AUTH_REQUIRED"
    assert classify_weather_source("account_only_weather_vendor") == "PAID_OR_AUTH_REQUIRED"
    assert classify_weather_source("browser_cookie_capture") == "UNSAFE_OR_BLOCKED"
    assert classify_weather_source("polymarket_order_endpoint") == "UNSAFE_OR_BLOCKED"
    assert classify_weather_source("unknown_new_source") == "UNKNOWN_REVIEW_REQUIRED"
    assert report["paid_api_allowed"] is False
    assert report["browser_cookies_allowed"] is False
    assert Path(report["report_paths"]["json"]).exists()
    assert Path(report["report_paths"]["markdown"]).exists()


def test_sequence50_capture_plan_is_read_only_local_only(local_project: Path) -> None:
    from quant_os.data.weather.weather_market_capture_plan import (
        write_weather_market_capture_plan,
    )

    payload = write_weather_market_capture_plan(output_root=local_project)

    assert payload["status"] == "LOCAL_ONLY_CAPTURE_PLAN_READY_NEEDS_OPERATOR_MARKET"
    assert payload["manual_only"] is True
    assert payload["read_only"] is True
    assert payload["network_enabled"] is False
    assert payload["network_fetch_attempted"] is False
    assert payload["auth_headers_allowed"] is False
    assert payload["browser_cookies_allowed"] is False
    assert payload["order_placement_allowed"] is False
    assert payload["order_cancellation_allowed"] is False
    assert payload["raw_captures_commit_allowed"] is False
    assert "data/external/manual_captures/weather_market_mismatch" in payload[
        "capture_root"
    ]
    assert any("weather-market-capture-plan" in item for item in payload["exact_next_commands"])
    assert Path(payload["report_paths"]["json"]).exists()
    assert Path(payload["report_paths"]["markdown"]).exists()


def test_sequence50_replay_schema_enforces_no_lookahead_timestamps() -> None:
    from quant_os.research.replay_candidates.weather_market_replay_schema import (
        WeatherMarketReplayRow,
        build_fixture_weather_market_replay_row,
    )

    valid = WeatherMarketReplayRow.model_validate(build_fixture_weather_market_replay_row())

    assert valid.candidate_id == "pm_weather_forecast_market_mismatch"
    assert valid.forecast_ts.endswith("Z")
    assert valid.orderbook_ts.endswith("Z")
    assert valid.known_at_ts.endswith("Z")
    assert valid.forecast_ts <= valid.known_at_ts <= valid.orderbook_ts

    invalid = {
        **build_fixture_weather_market_replay_row(),
        "forecast_ts": "2026-05-15T13:00:00Z",
        "known_at_ts": "2026-05-15T12:00:00Z",
        "orderbook_ts": "2026-05-15T12:05:00Z",
    }
    with pytest.raises(ValueError, match="forecast_ts must be <= known_at_ts"):
        WeatherMarketReplayRow.model_validate(invalid)

    missing_label = {
        **build_fixture_weather_market_replay_row(),
        "proof_eligible": True,
        "resolution_label": "",
    }
    with pytest.raises(ValueError, match="resolution_label is required"):
        WeatherMarketReplayRow.model_validate(missing_label)


def test_sequence50_fixture_rows_are_synthetic_and_cannot_support_profit_claim() -> None:
    from quant_os.proving.profit_claim_guard import evaluate_profit_claim_guard
    from quant_os.proving.weather_market_paper_proving import (
        run_weather_market_paper_proving,
    )
    from quant_os.research.replay_candidates.weather_market_replay_schema import (
        load_weather_market_replay_rows,
    )

    rows = load_weather_market_replay_rows(FIXTURE_PATH)
    result = run_weather_market_paper_proving(rows)
    guard = evaluate_profit_claim_guard(result)

    assert rows
    assert all(row.fixture_only for row in rows)
    assert result["dataset_status"] == "FIXTURE_ONLY_NOT_PROOF"
    assert result["readiness_status"] == "PAPER_PROFIT_DIAGNOSTIC_ONLY"
    assert result["synthetic_rows_counted_as_profit_evidence"] is False
    assert guard["claim_status"] == "NO_PROFIT_CLAIM_ALLOWED"
    assert "SYNTHETIC_ONLY_DATA" in guard["blockers"]
    assert "SAMPLE_TOO_THIN" in guard["blockers"]
    assert "OOS_WALK_FORWARD_MISSING" in guard["blockers"]
    assert "SOURCE_QUALITY_TOO_WEAK" in guard["blockers"]


def test_sequence50_weather_paper_proving_includes_costs_fills_baselines_placebos(
    local_project: Path,
) -> None:
    from quant_os.proving.weather_market_paper_report import (
        write_weather_market_paper_proving_report,
    )

    payload = write_weather_market_paper_proving_report(
        output_root=local_project,
        fixture_path=FIXTURE_PATH,
    )

    assert payload["costs_included"] is True
    assert payload["fill_assumptions_included"] is True
    assert payload["baseline_comparison"]["included"] is True
    assert payload["baseline_comparison"]["baseline_count"] >= 3
    assert payload["placebo_comparison"]["included"] is True
    assert payload["placebo_comparison"]["placebo_count"] >= 4
    assert "edge_after_costs" in payload["paper_intents"][0]
    assert "fill_fraction" in payload["paper_intents"][0]
    assert payload["profit_claim_guard"]["claim_status"] == "NO_PROFIT_CLAIM_ALLOWED"
    assert Path(payload["report_paths"]["json"]).exists()
    assert Path(payload["report_paths"]["markdown"]).exists()


def test_sequence50_profit_claim_guard_blocks_thin_fixture_missing_oos_results() -> None:
    from quant_os.proving.profit_claim_guard import evaluate_profit_claim_guard
    from quant_os.proving.weather_market_paper_proving import (
        run_weather_market_paper_proving,
    )
    from quant_os.research.replay_candidates.weather_market_replay_schema import (
        load_weather_market_replay_rows,
    )

    result = run_weather_market_paper_proving(load_weather_market_replay_rows(FIXTURE_PATH))
    guarded = evaluate_profit_claim_guard(
        {
            **result,
            "readiness_status": "PAPER_PROFIT_CANDIDATE",
            "oos_walk_forward_status": "OOS_WALK_FORWARD_MISSING",
        }
    )

    assert guarded["claim_status"] == "NO_PROFIT_CLAIM_ALLOWED"
    assert "SYNTHETIC_ONLY_DATA" in guarded["blockers"]
    assert "SAMPLE_TOO_THIN" in guarded["blockers"]
    assert "OOS_WALK_FORWARD_MISSING" in guarded["blockers"]


def test_sequence50_data_readiness_cannot_claim_live_or_canary_readiness(
    local_project: Path,
) -> None:
    from quant_os.readiness.weather_market_data_readiness_report import (
        write_weather_market_data_readiness_report,
    )

    payload = write_weather_market_data_readiness_report(
        output_root=local_project,
        fixture_path=FIXTURE_PATH,
    )

    assert payload["readiness_status"] == "PAPER_PROFIT_DIAGNOSTIC_ONLY"
    assert payload["paper_profit_status"] == "NO_PROFIT_CLAIM_ALLOWED"
    assert payload["canary_ready"] is False
    assert payload["live_ready"] is False
    assert payload["live_trading_enabled"] is False
    assert payload["execution_authority"] == "NONE"
    assert payload["autonomy_milestones"]["profit_lane_selected"] == "met"
    assert payload["autonomy_milestones"]["weather_data_acquisition"] in {
        "partial",
        "blocked",
    }
    assert payload["autonomy_milestones"]["paper_profit_candidate"] == "blocked"
    assert Path(payload["report_paths"]["json"]).exists()
    assert Path(payload["report_paths"]["markdown"]).exists()


def test_sequence50_no_auth_signing_order_cancel_wallet_copy_trade_or_evasion_paths() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_paths = [
        "src/quant_os/data/weather/weather_source_policy.py",
        "src/quant_os/data/weather/weather_source_registry.py",
        "src/quant_os/data/weather/weather_market_capture_plan.py",
        "src/quant_os/data/weather/weather_market_manual_capture.py",
        "src/quant_os/research/replay_candidates/weather_market_mismatch_candidate.py",
        "src/quant_os/research/replay_candidates/weather_market_mismatch_report.py",
        "src/quant_os/research/replay_candidates/weather_market_replay_schema.py",
        "src/quant_os/proving/weather_market_paper_proving.py",
        "src/quant_os/proving/weather_market_paper_report.py",
        "src/quant_os/readiness/weather_market_data_readiness.py",
        "src/quant_os/readiness/weather_market_data_readiness_report.py",
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
        "live_ready = True",
        "canary_ready = True",
        "guaranteed",
        "safe profit",
    ]

    for relative_path in source_paths:
        source_path = repo_root / relative_path
        assert source_path.exists(), source_path
        text = source_path.read_text(encoding="utf-8").lower()
        for token in forbidden_tokens:
            assert token not in text


def test_sequence50_cli_and_make_targets_generate_reports(local_project: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = {
        **os.environ,
        "PYTHONPATH": str(repo_root / "src"),
    }
    commands = [
        [sys.executable, "-m", "quant_os.cli", "research", "weather-market-candidate"],
        [sys.executable, "-m", "quant_os.cli", "research", "weather-source-policy"],
        [sys.executable, "-m", "quant_os.cli", "data", "weather-market-capture-plan"],
        [sys.executable, "-m", "quant_os.cli", "research", "weather-market-replay-schema"],
        [sys.executable, "-m", "quant_os.cli", "proving", "weather-market-paper-proving"],
        [sys.executable, "-m", "quant_os.cli", "readiness", "weather-market-data-readiness"],
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
    assert 'if "%TARGET%"=="weather-market-candidate-smoke"' in make_cmd
    assert 'if "%TARGET%"=="weather-market-paper-proving-smoke"' in make_cmd
    assert 'if "%TARGET%"=="sequence50-smoke"' in make_cmd
    assert "tests/test_sequence50_weather_market_data_paper_proving.py" in make_cmd
