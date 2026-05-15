from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def _row(
    row_id: str,
    *,
    outcome: str = "UP",
    ask: float = 0.46,
    bid: float = 0.44,
    liquidity: float = 800.0,
    seconds_to_window_end: float = 45.0,
    flags: list[str] | None = None,
    source_quality: str = "fixture_real_shaped",
    resolved_outcome: str = "UP",
    no_fill_probability: float | None = None,
    partial_fill_ratio: float | None = None,
    latency_penalty: float | None = None,
) -> dict[str, Any]:
    mid = (bid + ask) / 2.0
    return {
        "clob_snapshot_id": row_id,
        "market_id": f"market_{row_id}",
        "condition_id": f"condition_{row_id}",
        "token_id": f"token_{row_id}",
        "outcome": outcome,
        "event_ts": "2026-05-14T12:00:30Z",
        "window_start_ts": "2026-05-14T12:00:00Z",
        "window_end_ts": "2026-05-14T12:01:00Z",
        "market_bid": bid,
        "market_ask": ask,
        "market_mid": mid,
        "market_spread": ask - bid,
        "market_liquidity": liquidity,
        "market_last_trade_price": mid,
        "seconds_to_window_end": seconds_to_window_end,
        "spot_return_5s": 0.0002 if outcome == "UP" else -0.0002,
        "label_status": "RESOLVED",
        "resolved_outcome": resolved_outcome,
        "data_quality_flags": flags or ["LOOKAHEAD_PREVENTED"],
        "source_quality": source_quality,
        "source_name": source_quality,
        "primary_evidence_candidate": source_quality != "synthetic_stress",
        **({} if no_fill_probability is None else {"no_fill_probability": no_fill_probability}),
        **({} if partial_fill_ratio is None else {"expected_partial_fill_ratio": partial_fill_ratio}),
        **({} if latency_penalty is None else {"latency_penalty": latency_penalty}),
    }


def _phase43_rows() -> list[dict[str, Any]]:
    return [
        _row("allow_1", ask=0.46, bid=0.44, liquidity=900.0),
        _row("allow_2", ask=0.47, bid=0.45, liquidity=875.0, partial_fill_ratio=0.55),
        _row("wide", ask=0.60, bid=0.48, liquidity=900.0),
        _row("low_liquidity", ask=0.46, bid=0.44, liquidity=40.0),
        _row("stale", ask=0.46, bid=0.44, liquidity=900.0, flags=["STALE_CLOB_SNAPSHOT"]),
        _row("latency", ask=0.46, bid=0.44, liquidity=900.0, latency_penalty=0.08),
        _row("no_fill", ask=0.46, bid=0.44, liquidity=900.0, no_fill_probability=0.95),
        _row("partial_too_small", ask=0.46, bid=0.44, liquidity=900.0, partial_fill_ratio=0.05),
        _row("near_end", ask=0.46, bid=0.44, liquidity=900.0, seconds_to_window_end=2.0),
        _row("price_discipline", ask=0.66, bid=0.64, liquidity=900.0),
        _row("synthetic_allow", ask=0.46, bid=0.44, liquidity=900.0, source_quality="synthetic_stress"),
    ]


def _signal_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "row_decisions": [
            {
                "row_id": row["clob_snapshot_id"],
                "clob_snapshot_id": row["clob_snapshot_id"],
                "market_id": row["market_id"],
                "token_id": row["token_id"],
                "outcome": row["outcome"],
                "side": "BUY",
                "predicted_probability": 0.68,
                "signal_strength": abs(float(row["spot_return_5s"])),
                "primary_evidence": row["source_quality"] != "synthetic_stress",
                "blocked": False,
                "blockers": [],
            }
            for row in rows
        ],
        "candidate_signal_count": len(rows),
    }


def test_sequence43_fill_blocker_attribution_is_deterministic_and_explains_blockers(
    local_project: Path,
) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_fill_blocker_report import (
        write_pm_crypto_updown_fill_blocker_attribution_report,
    )

    rows = _phase43_rows()
    first = write_pm_crypto_updown_fill_blocker_attribution_report(
        rows=rows,
        signal_report=_signal_report(rows),
        output_root=local_project,
    )
    second = write_pm_crypto_updown_fill_blocker_attribution_report(
        rows=rows,
        signal_report=_signal_report(rows),
        output_root=local_project,
    )

    assert first == second
    assert first["blocked_counts_by_reason"]["SPREAD_TOO_WIDE"] == 1
    assert first["blocked_counts_by_reason"]["LOW_LIQUIDITY"] == 1
    assert first["blocked_counts_by_reason"]["STALE_CLOB"] == 1
    assert first["blocked_counts_by_reason"]["LATENCY_PENALTY_TOO_HIGH"] == 1
    assert first["blocked_counts_by_reason"]["NO_FILL_PROBABILITY_TOO_HIGH"] == 1
    assert first["blocked_counts_by_reason"]["PARTIAL_FILL_TOO_SMALL"] == 1
    assert first["blocked_counts_by_reason"]["TOO_CLOSE_TO_WINDOW_END"] == 1
    assert first["blocked_counts_by_reason"]["PRICE_DISCIPLINE_FAILED"] == 1
    assert first["potentially_tradeable_row_count"] == 3
    assert first["execution_authority"] == "NONE"
    assert first["live_trading_enabled"] is False
    assert (
        local_project
        / "reports"
        / "sequence43"
        / "fill_blockers"
        / "latest_fill_blocker_attribution.json"
    ).exists()
    assert (
        local_project
        / "reports"
        / "sequence43"
        / "fill_blockers"
        / "latest_fill_blocker_attribution.md"
    ).exists()


def test_sequence43_shadow_policy_is_offline_only_and_blocks_execution_risks(
    local_project: Path,
) -> None:
    from quant_os.execution.pm_crypto_updown_shadow_policy import (
        write_pm_crypto_updown_shadow_policy_report,
    )

    rows = _phase43_rows()
    payload = write_pm_crypto_updown_shadow_policy_report(
        rows=rows,
        signal_report=_signal_report(rows),
        output_root=local_project,
    )
    intents = {
        intent["candidate_id"] + ":" + intent["market_id"]: intent for intent in payload["intents"]
    }

    assert payload["schema_version"] == "pm_crypto_updown_shadow_policy_v1"
    assert payload["live_trading_enabled"] is False
    assert payload["execution_authority"] == "NONE"
    assert payload["order_routing_enabled"] is False
    assert payload["wallet_signing_enabled"] is False
    assert payload["order_cancellation_enabled"] is False
    assert payload["allowed_intent_count"] == 3
    assert all(intent["execution_authority"] == "NONE" for intent in payload["intents"])
    assert all(intent["live_trading_enabled"] is False for intent in payload["intents"])
    assert all(
        intent["hypothetical_limit_price"] <= intent["max_acceptable_price"]
        for intent in payload["intents"]
    )
    assert payload["assumptions"]["no_fill_allowed"] is True
    assert payload["assumptions"]["partial_fill_allowed"] is True
    assert any(
        intent["fill_assumption"] == "PASSIVE_LIMIT_NO_FILL_ALLOWED"
        for intent in payload["intents"]
    )
    assert intents["pm_crypto_updown_repricing_lag:market_wide"]["decision"] == "BLOCK_SHADOW_INTENT"
    assert intents["pm_crypto_updown_repricing_lag:market_wide"]["blocker_reason"] == "SPREAD_TOO_WIDE"
    assert intents["pm_crypto_updown_repricing_lag:market_stale"]["blocker_reason"] == "STALE_CLOB"
    assert intents["pm_crypto_updown_repricing_lag:market_low_liquidity"]["blocker_reason"] == "LOW_LIQUIDITY"


def test_sequence43_fill_variants_are_conservative_and_never_promote_too_lenient_control() -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_fill_variants import (
        evaluate_pm_crypto_updown_fill_variants,
    )

    rows = _phase43_rows()
    payload = evaluate_pm_crypto_updown_fill_variants(rows=rows, signal_report=_signal_report(rows))
    variants = {item["variant_id"]: item for item in payload["variants"]}

    assert set(variants) == {
        "STRICT_LIMIT_ONLY",
        "PASSIVE_LIMIT_WITH_NO_FILL",
        "SMALL_SIZE_SPREAD_CAPPED",
        "CROSS_ONLY_IF_EDGE_SURVIVES_WORST_CASE",
        "TOO_LENIENT_REJECTED_CONTROL",
    }
    for variant in variants.values():
        assert "allowed_intent_count" in variant
        assert "blocked_intent_count" in variant
        assert "filled_count" in variant
        assert "no_fill_count" in variant
        assert "partial_fill_count" in variant
        assert "cost_adjusted_result" in variant
        assert "baseline_comparison" in variant
        assert "placebo_comparison" in variant
    assert variants["TOO_LENIENT_REJECTED_CONTROL"]["assumption_classification"] == "TOO_LENIENT"
    assert variants["TOO_LENIENT_REJECTED_CONTROL"]["can_promote_readiness"] is False
    assert payload["too_lenient_control_promotes_readiness"] is False


def test_sequence43_policy_replay_preserves_source_separation_and_shadow_only_reports(
    local_project: Path,
) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_policy_replay_eval import (
        write_pm_crypto_updown_policy_replay_eval_report,
    )

    rows = _phase43_rows()
    payload = write_pm_crypto_updown_policy_replay_eval_report(
        rows=rows,
        signal_report=_signal_report(rows),
        output_root=local_project,
    )

    assert payload["schema_version"] == "pm_crypto_updown_policy_replay_eval_v1"
    assert payload["does_any_conservative_policy_allow_nonzero_intents"] is True
    assert payload["primary_allowed_intent_count"] == 2
    assert payload["synthetic_allowed_intent_count"] == 1
    assert payload["synthetic_rows_counted_as_primary"] is False
    assert payload["primary_vs_real_cached_vs_fixture_vs_synthetic_preserved"] is True
    assert payload["policy_answers"]["cost_fill_realism_still_blocks"] is True
    assert payload["network_fetch_attempted"] is False
    assert payload["live_trading_enabled"] is False
    assert (
        local_project
        / "reports"
        / "sequence43"
        / "policy_replay_eval"
        / "latest_policy_replay_eval.json"
    ).exists()


def test_sequence43_bounded_shadow_readiness_blocks_thin_or_cost_destroyed_policy_eval(
    local_project: Path,
) -> None:
    from quant_os.readiness.bounded_shadow_rehearsal_readiness_report import (
        write_bounded_shadow_rehearsal_readiness_report,
    )
    from quant_os.research.replay_candidates.pm_crypto_updown_policy_replay_eval import (
        evaluate_pm_crypto_updown_policy_replay,
    )

    rows = _phase43_rows()
    thin_eval = evaluate_pm_crypto_updown_policy_replay(rows=rows, signal_report=_signal_report(rows))
    thin = write_bounded_shadow_rehearsal_readiness_report(
        policy_replay_eval=thin_eval,
        output_root=local_project,
    )

    cost_destroyed = dict(thin_eval)
    cost_destroyed["primary_evidence_row_count"] = 20
    cost_destroyed["real_cached_replay_ready_row_count"] = 14
    cost_destroyed["primary_allowed_intent_count"] = 5
    cost_destroyed["allowed_intent_count"] = 5
    cost_destroyed["best_conservative_variant"] = {
        **cost_destroyed["best_conservative_variant"],
        "cost_adjusted_result": -0.01,
    }
    cost_block = write_bounded_shadow_rehearsal_readiness_report(
        policy_replay_eval=cost_destroyed,
        output_root=local_project,
    )

    assert thin["readiness_status"] == "INTENTS_TOO_THIN_AFTER_FILTERING"
    assert thin["overall_status"] == "CANDIDATE_REMAINS_BLOCKED"
    assert thin["ready_for_bounded_shadow_rehearsal"] is False
    assert thin["not_live_readiness"] is True
    assert thin["not_canary_readiness"] is True
    assert thin["live_readiness_claimed"] is False
    assert thin["canary_readiness_claimed"] is False
    assert cost_block["readiness_status"] == "FILL_REALISM_STILL_BLOCKS_EDGE"
    assert (
        local_project
        / "reports"
        / "sequence43"
        / "bounded_shadow_rehearsal_readiness"
        / "latest_bounded_shadow_rehearsal_readiness.json"
    ).exists()


def test_sequence43_cli_make_targets_and_forbidden_paths_are_non_executing(
    local_project: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = {
        **os.environ,
        "PYTHONPATH": str(repo_root / "src"),
    }
    commands = [
        [sys.executable, "-m", "quant_os.cli", "research", "pm-crypto-updown-fill-blockers"],
        [sys.executable, "-m", "quant_os.cli", "research", "pm-crypto-updown-shadow-policy"],
        [sys.executable, "-m", "quant_os.cli", "research", "pm-crypto-updown-policy-replay-eval"],
        [sys.executable, "-m", "quant_os.cli", "readiness", "bounded-shadow-rehearsal"],
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
    assert 'if "%TARGET%"=="sequence43-smoke"' in make_cmd
    assert 'if "%TARGET%"=="pm-crypto-updown-fill-policy-smoke"' in make_cmd
    assert 'if "%TARGET%"=="bounded-shadow-rehearsal-readiness-smoke"' in make_cmd

    source_paths = [
        "src/quant_os/research/replay_candidates/pm_crypto_updown_fill_blocker_attribution.py",
        "src/quant_os/research/replay_candidates/pm_crypto_updown_fill_blocker_report.py",
        "src/quant_os/execution/pm_crypto_updown_shadow_policy.py",
        "src/quant_os/execution/pm_crypto_updown_shadow_intents.py",
        "src/quant_os/research/replay_candidates/pm_crypto_updown_fill_variants.py",
        "src/quant_os/research/replay_candidates/pm_crypto_updown_policy_replay_eval.py",
        "src/quant_os/readiness/bounded_shadow_rehearsal_readiness.py",
        "src/quant_os/readiness/bounded_shadow_rehearsal_readiness_report.py",
    ]
    forbidden_tokens = [
        "create_order",
        "cancel_order",
        "post_order",
        "private_key",
        "wallet_signer",
        "sign_order",
        "copy_wallet_trade",
        "captcha_bypass",
        "proxy_rotation",
        "stealth_evasion",
    ]
    for source_path in source_paths:
        text = (repo_root / source_path).read_text(encoding="utf-8").lower()
        for token in forbidden_tokens:
            assert token not in text
