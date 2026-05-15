from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

BLOCKED_FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "fixtures"
    / "replay_candidates"
    / "pm_lp_refresh_lag"
    / "public_source_sample"
    / "blocked_missing_public_fill_attribution.json"
)


def _sufficient_public_feasibility() -> dict[str, str]:
    return {
        "market_id_condition_id": "AVAILABLE_PUBLIC_READ_ONLY",
        "token_ids_outcomes": "AVAILABLE_PUBLIC_READ_ONLY",
        "orderbook_snapshots": "AVAILABLE_WITH_MANUAL_CAPTURE",
        "bid_ask_levels": "AVAILABLE_WITH_MANUAL_CAPTURE",
        "quote_timestamps": "AVAILABLE_WITH_MANUAL_CAPTURE",
        "quote_refresh_timestamps": "AVAILABLE_WITH_MANUAL_CAPTURE",
        "trade_fill_events": "AVAILABLE_PUBLIC_READ_ONLY",
        "maker_taker_role": "AVAILABLE_PUBLIC_READ_ONLY",
        "maker_wallet_order_attribution": "AVAILABLE_PUBLIC_READ_ONLY",
        "two_sided_quoting_evidence": "AVAILABLE_WITH_MANUAL_CAPTURE",
        "spread_maintenance": "AVAILABLE_WITH_MANUAL_CAPTURE",
        "liquidity_reward_market_metadata": "AVAILABLE_PUBLIC_READ_ONLY",
        "spot_trigger_timestamps": "AVAILABLE_PUBLIC_READ_ONLY",
        "taker_burst_evidence": "AVAILABLE_PUBLIC_READ_ONLY",
        "resolution_labels": "AVAILABLE_PUBLIC_READ_ONLY",
    }


def _tiny_fixture_safe_row() -> dict[str, object]:
    return {
        "market_id": "pm_public_source_fixture_market",
        "token_id": "pm_public_source_fixture_token_yes",
        "outcome": "YES",
        "event_ts": "2026-05-15T12:00:00Z",
        "quote_before": {"bid": 0.48, "ask": 0.52, "ts": "2026-05-15T11:59:59Z"},
        "quote_after": {"bid": 0.48, "ask": 0.52, "ts": "2026-05-15T12:00:01Z"},
        "quote_refresh_lag_ms": 1000,
        "fill_event_ts": "2026-05-15T12:00:00Z",
        "stale_side": "ASK",
        "opposite_side_quote": {"price": 0.52, "size": 10.0},
        "spot_trigger": {
            "symbol": "BTCUSDT",
            "source": "public_binance_or_coinbase_reference",
            "trigger_ts": "2026-05-15T12:00:00Z",
            "direction": "UP",
        },
        "taker_burst": True,
        "spread": 0.04,
        "liquidity": 1250.0,
        "label_resolution": "YES",
        "source_quality": "fixture_safe_public_shape",
        "provenance_hash": "sha256:sequence48_fixture_safe_row",
    }


def test_sequence48_source_feasibility_report_is_deterministic(local_project: Path) -> None:
    from quant_os.research.replay_candidates.pm_lp_refresh_lag_source_feasibility import (
        build_pm_lp_refresh_lag_source_feasibility,
        write_pm_lp_refresh_lag_source_feasibility_report,
    )

    payload = build_pm_lp_refresh_lag_source_feasibility()
    first = write_pm_lp_refresh_lag_source_feasibility_report(output_root=local_project)
    first_text = Path(first["report_paths"]["json"]).read_text(encoding="utf-8")
    second = write_pm_lp_refresh_lag_source_feasibility_report(output_root=local_project)
    second_text = Path(second["report_paths"]["json"]).read_text(encoding="utf-8")

    statuses = {item["field_id"]: item["status"] for item in payload["required_fields"]}
    assert first_text == second_text
    assert payload["schema_version"] == "pm_lp_refresh_lag_source_feasibility_v1"
    assert payload["sequence"] == "48"
    assert payload["candidate_id"] == "pm_lp_refresh_lag_arbitrage"
    assert statuses["market_id_condition_id"] == "AVAILABLE_PUBLIC_READ_ONLY"
    assert statuses["token_ids_outcomes"] == "AVAILABLE_PUBLIC_READ_ONLY"
    assert statuses["orderbook_snapshots"] == "AVAILABLE_WITH_MANUAL_CAPTURE"
    assert statuses["quote_refresh_timestamps"] == "AVAILABLE_WITH_MANUAL_CAPTURE"
    assert statuses["maker_taker_role"] == "AVAILABLE_ONLY_AUTHENTICATED"
    assert statuses["maker_wallet_order_attribution"] == "AVAILABLE_ONLY_AUTHENTICATED"
    assert payload["public_source_acquisition_ready"] is False
    assert payload["active_blocker"] == "BLOCKED_MISSING_PUBLIC_FILL_ATTRIBUTION"
    assert payload["network_fetch_attempted"] is False
    assert payload["ci_network_dependency"] is False
    assert any("docs.polymarket.com" in item["url"] for item in payload["reviewed_sources"])


def test_sequence48_unsafe_and_auth_only_dependencies_are_rejected(
    local_project: Path,
) -> None:
    from quant_os.data.prediction_markets.pm_lp_refresh_lag_capture_plan import (
        write_pm_lp_refresh_lag_capture_plan,
    )
    from quant_os.readiness.pm_lp_refresh_lag_source_readiness import (
        evaluate_pm_lp_refresh_lag_source_readiness,
    )

    plan = write_pm_lp_refresh_lag_capture_plan(output_root=local_project)
    unsafe = evaluate_pm_lp_refresh_lag_source_readiness(
        source_feasibility_overrides={"unsafe_dependency_flags": ["copy_trading"]}
    )

    assert plan["schema_version"] == "pm_lp_refresh_lag_capture_plan_v1"
    assert plan["manual_only"] is True
    assert plan["read_only"] is True
    assert plan["network_enabled"] is False
    assert plan["auth_headers_allowed"] is False
    assert plan["browser_cookies_allowed"] is False
    assert plan["order_endpoints_allowed"] is False
    assert plan["manual_capture_must_be_source_policy_approved"] is True
    assert "source unavailable, do nothing" in plan["fallback_policy"].lower()
    rejected = {item["source_id"]: item for item in plan["rejected_sources"]}
    assert rejected["polymarket_authenticated_clob_trades"]["reason_code"] == (
        "AVAILABLE_ONLY_AUTHENTICATED"
    )
    assert rejected["copy_trade_or_wallet_mirroring"]["reason_code"] == "UNSAFE_DEPENDENCY"
    assert unsafe["source_readiness_status"] == "REJECTED_UNSAFE_COPY_TRADE_DEPENDENCY"
    assert unsafe["live_trading_enabled"] is False
    assert unsafe["execution_authority"] == "NONE"


def test_sequence48_missing_public_fill_attribution_blocks_source_readiness(
    local_project: Path,
) -> None:
    from quant_os.readiness.pm_lp_refresh_lag_source_readiness_report import (
        write_pm_lp_refresh_lag_source_readiness_report,
    )

    readiness = write_pm_lp_refresh_lag_source_readiness_report(
        fixture_path=BLOCKED_FIXTURE,
        output_root=local_project,
    )

    assert readiness["source_readiness_status"] == "BLOCKED_MISSING_PUBLIC_FILL_ATTRIBUTION"
    assert readiness["active_blocker"] == "BLOCKED_MISSING_PUBLIC_FILL_ATTRIBUTION"
    assert set(readiness["exact_missing_source_fields"]) == {
        "maker_taker_role",
        "maker_wallet_order_attribution",
    }
    assert readiness["blocked_fixture_valid"] is True
    assert Path(readiness["report_paths"]["json"]).exists()
    assert Path(readiness["report_paths"]["markdown"]).exists()
    assert readiness["canary_ready"] is False
    assert readiness["live_trading_enabled"] is False
    assert readiness["live_promotion_status"] == "LIVE_BLOCKED"


def test_sequence48_missing_quote_refresh_timestamps_blocks_source_readiness() -> None:
    from quant_os.readiness.pm_lp_refresh_lag_source_readiness import (
        evaluate_pm_lp_refresh_lag_source_readiness,
    )

    statuses = {
        **_sufficient_public_feasibility(),
        "quote_refresh_timestamps": "NOT_AVAILABLE_PUBLICLY",
    }
    readiness = evaluate_pm_lp_refresh_lag_source_readiness(field_status_overrides=statuses)

    assert readiness["source_readiness_status"] == "BLOCKED_MISSING_QUOTE_REFRESH_TIMESTAMPS"
    assert readiness["exact_missing_source_fields"] == ["quote_refresh_timestamps"]
    assert readiness["canary_ready"] is False
    assert readiness["live_trading_enabled"] is False


def test_sequence48_fixture_safe_sample_validates_when_all_fields_exist() -> None:
    from quant_os.readiness.pm_lp_refresh_lag_source_readiness import (
        evaluate_pm_lp_refresh_lag_source_readiness,
        validate_pm_lp_refresh_lag_public_source_sample,
    )

    fixture = {
        "schema_version": "pm_lp_refresh_lag_public_source_sample_v1",
        "dataset_status": "FIRST_REFRESH_LAG_DATASET_READY",
        "source_quality": "fixture_safe_public_shape",
        "events": [_tiny_fixture_safe_row()],
    }
    validation = validate_pm_lp_refresh_lag_public_source_sample(fixture)
    readiness = evaluate_pm_lp_refresh_lag_source_readiness(
        field_status_overrides=_sufficient_public_feasibility(),
        fixture_payload=fixture,
    )

    assert validation["valid"] is True
    assert validation["event_count"] == 1
    assert readiness["source_readiness_status"] == "FIRST_REFRESH_LAG_DATASET_READY"
    assert readiness["dataset_event_count"] == 1
    assert readiness["canary_ready"] is False
    assert readiness["live_trading_enabled"] is False
    assert readiness["execution_authority"] == "NONE"


def test_sequence48_baseline_placebo_fill_design_is_required() -> None:
    from quant_os.readiness.pm_lp_refresh_lag_source_readiness import (
        evaluate_pm_lp_refresh_lag_source_readiness,
    )

    readiness = evaluate_pm_lp_refresh_lag_source_readiness()
    requirements = set(readiness["baseline_placebo_fill_requirements"])

    assert {
        "no_skill_baseline",
        "stale_quote_random_timestamp_placebo",
        "trigger_sign_flip_placebo",
        "market_mid_holdout_baseline",
        "queue_no_fill_model",
        "partial_fill_sensitivity",
        "adverse_selection_stress",
        "latency_penalty",
    }.issubset(requirements)


def test_sequence48_cli_make_targets_and_forbidden_paths_are_non_executing(
    local_project: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = {
        **os.environ,
        "PYTHONPATH": str(repo_root / "src"),
    }
    commands = [
        [sys.executable, "-m", "quant_os.cli", "research", "pm-lp-refresh-lag-source-feasibility"],
        [sys.executable, "-m", "quant_os.cli", "data", "pm-lp-refresh-lag-capture-plan"],
        [sys.executable, "-m", "quant_os.cli", "readiness", "pm-lp-refresh-lag-source-readiness"],
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
    assert 'if "%TARGET%"=="sequence48-smoke"' in make_cmd
    assert "pm-lp-refresh-lag-source-feasibility" in make_cmd
    assert "pm-lp-refresh-lag-capture-plan" in make_cmd
    assert "pm-lp-refresh-lag-source-readiness" in make_cmd
    assert "tests/test_sequence48_lp_refresh_lag_public_sources.py" in make_cmd

    source_paths = [
        "src/quant_os/research/replay_candidates/pm_lp_refresh_lag_source_feasibility.py",
        "src/quant_os/data/prediction_markets/pm_lp_refresh_lag_capture_plan.py",
        "src/quant_os/readiness/pm_lp_refresh_lag_source_readiness.py",
        "src/quant_os/readiness/pm_lp_refresh_lag_source_readiness_report.py",
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
