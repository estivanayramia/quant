from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "replay_candidates" / "pm_crypto_updown"


def test_sequence37_replay_eval_uses_only_ready_rows_as_primary_evidence(
    local_project: Path,
) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_replay_eval import (
        write_pm_crypto_updown_replay_eval_report,
    )

    payload = write_pm_crypto_updown_replay_eval_report(
        fixture_root=FIXTURE_ROOT,
        output_root=local_project,
    )

    assert payload["schema_version"] == "pm_crypto_updown_replay_eval_v1"
    assert payload["row_count"] == 4
    assert payload["replay_ready_row_count"] == 2
    assert payload["primary_evidence_row_count"] == 2
    assert payload["candidate_signal_count"] == 1
    assert payload["blocked_row_count"] == 2
    assert {row["clob_snapshot_id"] for row in payload["primary_rows"]} == {
        "clob_1200_up_01",
        "clob_1200_down_01",
    }
    assert {row["clob_snapshot_id"] for row in payload["excluded_rows"]} == {
        "clob_1201_up_01",
        "clob_1201_down_01",
    }
    assert "SAMPLE_TOO_THIN_FOR_CONFIDENCE" in payload["confidence_warnings"]
    assert payload["live_trading_enabled"] is False
    assert payload["execution_authority"] == "NONE"
    assert (
        local_project
        / "reports"
        / "sequence37"
        / "replay_eval"
        / "latest_pm_crypto_updown_replay_eval.json"
    ).exists()
    assert (
        local_project
        / "reports"
        / "sequence37"
        / "replay_eval"
        / "latest_pm_crypto_updown_replay_eval.md"
    ).exists()


def test_sequence37_signal_scoring_is_transparent_and_deterministic() -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_alignment import (
        build_pm_crypto_updown_dataset,
    )
    from quant_os.research.replay_candidates.pm_crypto_updown_signals import (
        score_pm_crypto_updown_signals,
    )

    rows = build_pm_crypto_updown_dataset(fixture_root=FIXTURE_ROOT)["rows"]
    first = score_pm_crypto_updown_signals(rows)
    second = score_pm_crypto_updown_signals(rows)

    assert first == second
    assert [definition["name"] for definition in first["signal_definitions"]] == [
        "spot_return_direction",
        "market_lag_vs_spot",
        "spread_liquidity_time_filter",
    ]
    up = next(item for item in first["row_decisions"] if item["clob_snapshot_id"] == "clob_1200_up_01")
    down = next(
        item for item in first["row_decisions"] if item["clob_snapshot_id"] == "clob_1200_down_01"
    )
    caveated = next(
        item for item in first["row_decisions"] if item["clob_snapshot_id"] == "clob_1201_up_01"
    )

    assert up["side"] == "BUY"
    assert up["predicted_probability"] == pytest.approx(0.6)
    assert up["rationale"]
    assert up["failure_mode"]
    assert down["side"] == "NO_SIGNAL"
    assert down["predicted_probability"] == pytest.approx(0.4)
    assert caveated["primary_evidence"] is False
    assert caveated["blocked"] is True
    assert "LABEL_UNRESOLVED" in caveated["blockers"]


def test_sequence37_baselines_warn_when_sample_is_too_thin() -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_alignment import (
        build_pm_crypto_updown_dataset,
    )
    from quant_os.research.replay_candidates.pm_crypto_updown_baselines import (
        evaluate_pm_crypto_updown_baselines,
    )
    from quant_os.research.replay_candidates.pm_crypto_updown_signals import (
        score_pm_crypto_updown_signals,
    )

    rows = build_pm_crypto_updown_dataset(fixture_root=FIXTURE_ROOT)["rows"]
    signals = score_pm_crypto_updown_signals(rows)
    payload = evaluate_pm_crypto_updown_baselines(rows=rows, signal_report=signals)

    assert payload["primary_evidence_row_count"] == 2
    assert payload["candidate_metrics"]["brier_score"] < payload["baselines"]["market_probability"][
        "brier_score"
    ]
    assert payload["candidate_metrics"]["brier_score"] < payload["baselines"]["no_skill"][
        "brier_score"
    ]
    assert payload["candidate_beats_market_baseline"] is True
    assert payload["candidate_beats_no_skill"] is True
    assert "SAMPLE_TOO_THIN_FOR_CONFIDENCE" in payload["warnings"]
    assert "previous_market_probability" in payload["baselines"]


def test_sequence37_placebos_are_diagnostic_and_block_promotion_when_thin() -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_alignment import (
        build_pm_crypto_updown_dataset,
    )
    from quant_os.research.replay_candidates.pm_crypto_updown_placebos import (
        run_pm_crypto_updown_placebos,
    )
    from quant_os.research.replay_candidates.pm_crypto_updown_signals import (
        score_pm_crypto_updown_signals,
    )

    rows = build_pm_crypto_updown_dataset(fixture_root=FIXTURE_ROOT)["rows"]
    signals = score_pm_crypto_updown_signals(rows)
    payload = run_pm_crypto_updown_placebos(rows=rows, signal_report=signals)

    assert payload["placebo_comparison_status"] == "PLACEBO_DIAGNOSTIC_TOO_THIN"
    assert payload["candidate_beats_placebos_for_readiness"] is False
    assert payload["promotion_blocked"] is True
    assert {item["placebo_type"] for item in payload["placebo_tests"]} >= {
        "timestamp_shift",
        "label_permutation",
        "spot_return_sign_flip",
        "random_entry",
        "market_window_shuffle",
    }
    assert "PLACEBO_SAMPLE_TOO_THIN_DIAGNOSTIC_ONLY" in payload["warnings"]


def test_sequence37_cost_and_fill_stress_can_block_attractive_rows() -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_alignment import (
        build_pm_crypto_updown_dataset,
    )
    from quant_os.research.replay_candidates.pm_crypto_updown_costs import (
        apply_pm_crypto_updown_cost_stress,
    )
    from quant_os.research.replay_candidates.pm_crypto_updown_fill_stress import (
        apply_pm_crypto_updown_fill_stress,
    )
    from quant_os.research.replay_candidates.pm_crypto_updown_signals import (
        score_pm_crypto_updown_signals,
    )

    rows = build_pm_crypto_updown_dataset(fixture_root=FIXTURE_ROOT)["rows"]
    signals = score_pm_crypto_updown_signals(rows)
    cost_payload = apply_pm_crypto_updown_cost_stress(rows=rows, signal_report=signals)
    fill_payload = apply_pm_crypto_updown_fill_stress(rows=rows, cost_report=cost_payload)

    assert cost_payload["candidate_signal_count"] == 1
    assert cost_payload["costs_destroy_edge"] is False
    assert fill_payload["fill_realism_blocks_edge"] is False

    stressed = [dict(row) for row in rows]
    stressed_up = next(row for row in stressed if row["clob_snapshot_id"] == "clob_1200_up_01")
    stressed_up["market_ask"] = 0.98
    stressed_up["market_mid"] = 0.89
    stressed_up["market_spread"] = 0.18
    stressed_up["market_liquidity"] = 50.0
    stressed_up["data_quality_flags"] = ["LOOKAHEAD_PREVENTED"]
    stressed_signals = score_pm_crypto_updown_signals(stressed)
    stressed_cost = apply_pm_crypto_updown_cost_stress(
        rows=stressed,
        signal_report=stressed_signals,
    )
    stressed_fill = apply_pm_crypto_updown_fill_stress(
        rows=stressed,
        cost_report=stressed_cost,
    )

    assert stressed_cost["costs_destroy_edge"] is True
    assert stressed_fill["fill_realism_blocks_edge"] is True
    assert "WIDE_SPREAD_REJECTION" in stressed_fill["rows"][0]["fill_blockers"]
    assert "LOW_LIQUIDITY_REJECTION" in stressed_fill["rows"][0]["fill_blockers"]


def test_sequence37_shadow_bridge_outputs_offline_blocked_intents(
    local_project: Path,
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
        fixture_root=FIXTURE_ROOT,
        output_root=local_project,
    )
    readiness = write_candidate_replay_readiness_report(
        evaluation_report=evaluation,
        output_root=local_project,
    )
    bridge = write_pm_crypto_updown_shadow_bridge_report(
        evaluation_report=evaluation,
        readiness_report=readiness,
        output_root=local_project,
    )

    assert bridge["schema_version"] == "pm_crypto_updown_shadow_bridge_v1"
    assert bridge["offline_shadow_intents_only"] is True
    assert bridge["shadow_intent_count"] == 1
    assert bridge["blocked_intent_count"] == 1
    assert all(intent["blocked"] is True for intent in bridge["shadow_intents"])
    intent = bridge["shadow_intents"][0]
    assert intent["row_id"] == "clob_1200_up_01"
    assert intent["side"] == "BUY"
    assert intent["risk_caveat"] == "CANDIDATE_REPLAY_TOO_THIN"
    assert intent["real_order_submitted"] is False
    assert bridge["execution_authority"] == "NONE"
    assert (
        local_project
        / "reports"
        / "sequence37"
        / "shadow_bridge"
        / "latest_pm_crypto_updown_shadow_bridge.json"
    ).exists()


def test_sequence37_readiness_blocks_thin_evidence_and_cannot_claim_live_or_canary(
    local_project: Path,
) -> None:
    from quant_os.readiness.candidate_replay_readiness_report import (
        write_candidate_replay_readiness_report,
    )
    from quant_os.research.replay_candidates.pm_crypto_updown_replay_eval import (
        write_pm_crypto_updown_replay_eval_report,
    )

    evaluation = write_pm_crypto_updown_replay_eval_report(
        fixture_root=FIXTURE_ROOT,
        output_root=local_project,
    )
    readiness = write_candidate_replay_readiness_report(
        evaluation_report=evaluation,
        output_root=local_project,
    )

    assert readiness["schema_version"] == "candidate_replay_readiness_v1"
    assert readiness["readiness_status"] == "CANDIDATE_REPLAY_TOO_THIN"
    assert readiness["ready_for_expanded_shadow_replay"] is False
    assert readiness["not_live_readiness"] is True
    assert readiness["not_canary_readiness"] is True
    assert readiness["live_trading_enabled"] is False
    assert readiness["execution_authority"] == "NONE"
    assert readiness["canary_readiness_claimed"] is False
    assert readiness["live_readiness_claimed"] is False
    assert readiness["autonomy_milestones"]["candidate_replay_tested"] == "complete"
    assert readiness["autonomy_milestones"]["expanded_shadow_replay"] == "blocked"
    assert (
        local_project
        / "reports"
        / "sequence37"
        / "replay_readiness"
        / "latest_candidate_replay_readiness.json"
    ).exists()
    assert (
        local_project
        / "reports"
        / "sequence37"
        / "autonomy_milestones"
        / "latest_autonomy_milestones.json"
    ).exists()


def test_sequence37_cli_commands_are_fixture_safe_and_non_executing(
    local_project: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = {
        **os.environ,
        "PYTHONPATH": str(repo_root / "src"),
    }
    commands = [
        [sys.executable, "-m", "quant_os.cli", "research", "pm-crypto-updown-replay-eval"],
        [sys.executable, "-m", "quant_os.cli", "research", "pm-crypto-updown-placebo"],
        [sys.executable, "-m", "quant_os.cli", "research", "pm-crypto-updown-shadow-bridge"],
        [sys.executable, "-m", "quant_os.cli", "readiness", "candidate-replay-readiness"],
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


def test_sequence37_modules_do_not_add_live_signing_order_or_copy_paths() -> None:
    source_paths = [
        Path("src/quant_os/research/replay_candidates/pm_crypto_updown_signals.py"),
        Path("src/quant_os/research/replay_candidates/pm_crypto_updown_baselines.py"),
        Path("src/quant_os/research/replay_candidates/pm_crypto_updown_placebos.py"),
        Path("src/quant_os/research/replay_candidates/pm_crypto_updown_costs.py"),
        Path("src/quant_os/research/replay_candidates/pm_crypto_updown_fill_stress.py"),
        Path("src/quant_os/research/replay_candidates/pm_crypto_updown_replay_eval.py"),
        Path("src/quant_os/research/replay_candidates/pm_crypto_updown_shadow_bridge.py"),
        Path("src/quant_os/readiness/candidate_replay_readiness.py"),
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

    for path in source_paths:
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        for token in forbidden_tokens:
            assert token not in lowered
