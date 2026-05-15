from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "fixtures"
    / "replay_candidates"
    / "pm_lp_refresh_lag"
    / "refresh_lag_windows.json"
)


def _fixture_events() -> list[dict[str, object]]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["events"]


def test_sequence47_candidate_pack_formalizes_unproven_hypothesis_without_execution() -> None:
    from quant_os.research.replay_candidates.pm_lp_refresh_lag_candidate_pack import (
        build_pm_lp_refresh_lag_candidate_pack,
    )
    from quant_os.research.replay_candidates.pm_lp_refresh_lag_schema import CANDIDATE_ID

    payload = build_pm_lp_refresh_lag_candidate_pack()

    assert payload["schema_version"] == "pm_lp_refresh_lag_candidate_pack_v1"
    assert payload["sequence"] == "47"
    assert payload["candidate_id"] == CANDIDATE_ID
    assert payload["aliases"] == [
        "pm_stale_lp_quote_arbitrage",
        "pm_refresh_lag_window",
    ]
    assert payload["candidate_readiness_status"] == "CANDIDATE_PACK_READY_FOR_DATA_ACQUISITION"
    assert payload["hypothesis_status"] == "UNPROVEN_HYPOTHESIS_ONLY"
    assert "unproven hypothesis" in payload["hypothesis"].lower()
    assert payload["social_claim_policy"]["claimed_pnl_is_evidence"] is False
    assert payload["social_claim_policy"]["wallet_lists_are_truth"] is False
    assert payload["source_policy_summary"]["public_read_only_only"] is True
    assert payload["source_policy_summary"]["social_post_to_trade_shortcut_allowed"] is False
    assert payload["execution_authority"] == "NONE"
    assert payload["live_trading_enabled"] is False
    assert payload["copy_trading_enabled"] is False
    assert payload["wallet_signing_enabled"] is False
    assert payload["real_orders_enabled"] is False

    required_future_data = set(payload["required_future_data"])
    assert {
        "public CLOB/orderbook snapshots",
        "public trade/fill events if available",
        "quote refresh timestamps",
        "maker/order attribution if available from public data",
        "two-sided quoting behavior",
        "inter-trade intervals",
        "spread maintenance",
        "liquidity/reward-market metadata",
        "spot directional triggers",
        "taker burst detection",
        "resolution labels",
        "fill/no-fill realism",
    }.issubset(required_future_data)
    assert "no copy trading" in payload["hard_guardrails"]
    assert "no live execution" in payload["hard_guardrails"]
    assert "no authenticated APIs" in payload["hard_guardrails"]


def test_sequence47_replay_schema_validates_fixture_events_and_refresh_lag_definition() -> None:
    from pydantic import ValidationError

    from quant_os.research.replay_candidates.pm_lp_refresh_lag_schema import (
        CANDIDATE_ID,
        REQUIRED_PM_LP_REFRESH_LAG_FIELDS,
        PmLpRefreshLagReplayEvent,
        build_pm_lp_refresh_lag_replay_schema,
        load_pm_lp_refresh_lag_fixture_events,
    )

    schema = build_pm_lp_refresh_lag_replay_schema()
    events = load_pm_lp_refresh_lag_fixture_events(FIXTURE_PATH)

    assert schema["schema_version"] == "pm_lp_refresh_lag_replay_schema_v1"
    assert schema["event_type"] == "refresh_lag_window"
    assert "stale_quote_side" in schema["event_definition"]["required_window_fields"]
    assert "quote_refresh_lag_ms" in schema["event_definition"]["required_window_fields"]
    assert set(REQUIRED_PM_LP_REFRESH_LAG_FIELDS).issubset(events[0].model_dump())
    assert len(events) == 2
    assert all(event.candidate_id == CANDIDATE_ID for event in events)
    assert all(event.event_type == "refresh_lag_window" for event in events)
    assert all(event.quote_refresh_lag_ms > 0 for event in events)
    assert events[0].stale_quote_side == "ASK"
    assert events[1].stale_quote_side == "BID"
    assert events[0].maker_attribution_public is False
    assert events[0].fill_realism["queue_position_observed"] is False
    assert "NO_WALLET_LABEL_TRUTH" in events[0].data_quality_flags

    bad_candidate = {**_fixture_events()[0], "candidate_id": "copy_trade_wallet_lane"}
    with pytest.raises(ValidationError):
        PmLpRefreshLagReplayEvent.model_validate(bad_candidate)

    bad_time = {**_fixture_events()[0], "window_start_ts": "2026-05-14T12:00:01"}
    with pytest.raises(ValidationError):
        PmLpRefreshLagReplayEvent.model_validate(bad_time)


def test_sequence47_public_source_policy_and_readiness_reject_copy_trade_dependencies() -> None:
    from quant_os.research.replay_candidates.pm_lp_refresh_lag_schema import (
        load_pm_lp_refresh_lag_fixture_events,
    )
    from quant_os.research.replay_candidates.pm_lp_refresh_lag_source_policy import (
        build_pm_lp_refresh_lag_source_policy,
        evaluate_pm_lp_refresh_lag_candidate_readiness,
    )

    policy = build_pm_lp_refresh_lag_source_policy()
    events = load_pm_lp_refresh_lag_fixture_events(FIXTURE_PATH)
    readiness = evaluate_pm_lp_refresh_lag_candidate_readiness(
        source_policy=policy,
        fixture_events=events,
    )
    unsafe = evaluate_pm_lp_refresh_lag_candidate_readiness(
        source_policy={
            **policy,
            "unsafe_dependency_flags": [
                "copy_trading",
                "wallet_mirroring",
            ],
        },
        fixture_events=events,
    )

    allowed_source_types = {item["source_type"] for item in policy["allowed_sources"]}
    blocked_source_types = {item["source_type"] for item in policy["blocked_sources"]}
    assert {
        "public_clob_orderbook_snapshots",
        "public_trade_or_fill_events",
        "public_quote_refresh_timestamps",
        "public_liquidity_reward_market_metadata",
        "public_spot_directional_triggers",
        "public_resolution_labels",
    }.issubset(allowed_source_types)
    assert {
        "copy_trading",
        "wallet_mirroring",
        "private_wallet_label_truth",
        "authenticated_trading_api",
        "order_endpoint",
        "claimed_pnl_social_post",
    }.issubset(blocked_source_types)
    assert policy["public_read_only_only"] is True
    assert policy["network_capture_allowed_without_auth"] is True
    assert policy["authenticated_api_allowed"] is False
    assert policy["order_endpoints_allowed"] is False
    assert readiness["candidate_readiness_status"] == "CANDIDATE_PACK_READY_FOR_DATA_ACQUISITION"
    assert readiness["fixture_event_count"] == 2
    assert readiness["fixture_schema_valid"] is True
    assert readiness["data_availability_status"] == "PUBLIC_SOURCES_REQUIRED_NOT_ACQUIRED"
    assert readiness["live_trading_enabled"] is False
    assert readiness["execution_authority"] == "NONE"
    assert unsafe["candidate_readiness_status"] == "REJECTED_UNSAFE_COPY_TRADE_DEPENDENCY"
    assert unsafe["rejected_unsafe_copy_trade_dependency"] is True


def test_sequence47_reports_include_blockers_baselines_fill_requirements_and_autonomy(
    local_project: Path,
) -> None:
    from quant_os.readiness.autonomy_milestone_report import (
        write_sequence47_autonomy_milestone_report,
    )
    from quant_os.research.replay_candidates.pm_lp_refresh_lag_candidate_pack import (
        write_pm_lp_refresh_lag_candidate_pack_report,
    )
    from quant_os.research.replay_candidates.pm_lp_refresh_lag_source_policy import (
        write_pm_lp_refresh_lag_candidate_readiness_report,
        write_pm_lp_refresh_lag_source_policy_report,
    )

    pack = write_pm_lp_refresh_lag_candidate_pack_report(output_root=local_project)
    policy = write_pm_lp_refresh_lag_source_policy_report(output_root=local_project)
    readiness = write_pm_lp_refresh_lag_candidate_readiness_report(
        fixture_path=FIXTURE_PATH,
        output_root=local_project,
    )
    autonomy = write_sequence47_autonomy_milestone_report(
        candidate_readiness=readiness,
        output_root=local_project,
    )

    assert Path(pack["report_paths"]["json"]).exists()
    assert Path(pack["report_paths"]["markdown"]).exists()
    assert Path(policy["report_paths"]["json"]).exists()
    assert Path(readiness["report_paths"]["json"]).exists()
    assert Path(autonomy["report_paths"]["json"]).exists()
    assert readiness["candidate_readiness_status"] == "CANDIDATE_PACK_READY_FOR_DATA_ACQUISITION"
    assert readiness["blockers"] == ["PUBLIC_SOURCES_REQUIRED_NOT_ACQUIRED"]
    assert "market_midquote_holdout" in pack["baseline_placebo_requirements"]
    assert "randomized_refresh_lag_timestamp_placebo" in pack["baseline_placebo_requirements"]
    assert "directional_trigger_sign_flip_placebo" in pack["baseline_placebo_requirements"]
    assert "queue_position_or_no_fill_model" in pack["fill_cost_realism_requirements"]
    assert "fees_spread_slippage_and_adverse_selection" in pack["fill_cost_realism_requirements"]
    assert "partial_fill_sensitivity" in pack["fill_cost_realism_requirements"]
    assert autonomy["sequence"] == "47"
    assert autonomy["prior_candidate_status"] == "DEPRIORITIZE_CANDIDATE"
    assert autonomy["selected_candidate_id"] == "pm_lp_refresh_lag_arbitrage"
    assert autonomy["live_orders_allowed"] is False
    assert autonomy["live_promotion_status"] == "LIVE_BLOCKED"
    assert autonomy["phase47_movement"]["candidate_pack"] == "ready_for_data_acquisition"


def test_sequence47_cli_make_targets_and_forbidden_paths_are_non_executing(
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
            "research",
            "pm-lp-refresh-lag-candidate-pack",
        ],
        [
            sys.executable,
            "-m",
            "quant_os.cli",
            "research",
            "pm-lp-refresh-lag-source-policy",
        ],
        [
            sys.executable,
            "-m",
            "quant_os.cli",
            "readiness",
            "pm-lp-refresh-lag-candidate-readiness",
            "--fixture-path",
            str(FIXTURE_PATH),
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

    make_cmd = (repo_root / "make.cmd").read_text(encoding="utf-8")
    assert 'if "%TARGET%"=="sequence47-smoke"' in make_cmd

    source_paths = [
        "src/quant_os/research/replay_candidates/pm_lp_refresh_lag_candidate_pack.py",
        "src/quant_os/research/replay_candidates/pm_lp_refresh_lag_schema.py",
        "src/quant_os/research/replay_candidates/pm_lp_refresh_lag_source_policy.py",
        "src/quant_os/readiness/autonomy_milestones.py",
    ]
    forbidden_tokens = [
        "create_order(",
        "cancel_order(",
        "post_order(",
        "private_key",
        "wallet_signer",
        "sign_order(",
        "place_order(",
        "authenticated_client",
    ]
    for source_path in source_paths:
        text = (repo_root / source_path).read_text(encoding="utf-8").lower()
        for token in forbidden_tokens:
            assert token not in text
