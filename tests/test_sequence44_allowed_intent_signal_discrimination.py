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
    resolved_outcome: str = "UP",
    ask: float = 0.46,
    bid: float = 0.44,
    liquidity: float = 800.0,
    seconds_to_window_end: float = 45.0,
    spot_return_5s: float | None = 0.0002,
    flags: list[str] | None = None,
    source_quality: str = "fixture_real_shaped",
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
        "spot_return_5s": spot_return_5s,
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


def _phase44_rows() -> list[dict[str, Any]]:
    return [
        _row("allow_fixture_win", resolved_outcome="UP", ask=0.46, bid=0.44),
        _row("allow_fixture_loss", resolved_outcome="DOWN", ask=0.46, bid=0.44),
        _row(
            "allow_real_cached_win",
            resolved_outcome="UP",
            ask=0.47,
            bid=0.45,
            source_quality="real_cached",
            partial_fill_ratio=0.55,
        ),
        _row(
            "allow_real_cached_loss",
            resolved_outcome="DOWN",
            ask=0.47,
            bid=0.45,
            source_quality="real_cached",
            partial_fill_ratio=0.55,
        ),
        _row("wide_blocked", ask=0.62, bid=0.48, liquidity=900.0),
        _row("low_liquidity_blocked", ask=0.46, bid=0.44, liquidity=40.0),
        _row("near_end_blocked", ask=0.46, bid=0.44, seconds_to_window_end=2.0),
        _row(
            "synthetic_allow",
            ask=0.46,
            bid=0.44,
            source_quality="synthetic_stress",
            resolved_outcome="UP",
        ),
    ]


def _signal_report(rows: list[dict[str, Any]], *, probability: float = 0.68) -> dict[str, Any]:
    return {
        "row_decisions": [
            {
                "row_id": row["clob_snapshot_id"],
                "clob_snapshot_id": row["clob_snapshot_id"],
                "market_id": row["market_id"],
                "token_id": row["token_id"],
                "outcome": row["outcome"],
                "resolved_outcome": row["resolved_outcome"],
                "side": "BUY",
                "predicted_probability": probability,
                "signal_strength": abs(float(row.get("spot_return_5s") or 0.0)),
                "primary_evidence": row["source_quality"] != "synthetic_stress",
                "blocked": False,
                "blockers": [],
                "spot_direction": "UP" if (row.get("spot_return_5s") or 0.0) > 0 else "DOWN",
            }
            for row in rows
        ],
        "candidate_signal_count": len(rows),
    }


def test_sequence44_allowed_intent_diagnostics_are_deterministic(local_project: Path) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_allowed_intent_report import (
        write_pm_crypto_updown_allowed_intent_diagnostics_report,
    )

    rows = _phase44_rows()
    first = write_pm_crypto_updown_allowed_intent_diagnostics_report(
        rows=rows,
        signal_report=_signal_report(rows),
        output_root=local_project,
    )
    second = write_pm_crypto_updown_allowed_intent_diagnostics_report(
        rows=rows,
        signal_report=_signal_report(rows),
        output_root=local_project,
    )

    assert first == second
    assert first["schema_version"] == "pm_crypto_updown_allowed_intent_diagnostics_v1"
    assert first["allowed_primary_intent_count"] == 4
    assert first["allowed_real_cached_intent_count"] == 2
    assert first["allowed_synthetic_diagnostic_intent_count"] == 1
    assert first["active_blocker"] == "BASELINE_OR_PLACEBO_BLOCKED"
    assert first["blocker_causes"]["too_few_allowed_intents"] is True
    assert first["blocker_causes"]["placebo_similarity"] is True
    assert first["live_trading_enabled"] is False
    assert first["execution_authority"] == "NONE"
    assert (
        local_project
        / "reports"
        / "sequence44"
        / "allowed_intent_diagnostics"
        / "latest_allowed_intent_diagnostics.json"
    ).exists()
    assert (
        local_project
        / "reports"
        / "sequence44"
        / "allowed_intent_diagnostics"
        / "latest_allowed_intent_diagnostics.md"
    ).exists()


def test_sequence44_diagnostics_use_only_allowed_primary_intents_for_primary_claims() -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_allowed_intent_diagnostics import (
        evaluate_pm_crypto_updown_allowed_intent_diagnostics,
    )

    rows = _phase44_rows()
    payload = evaluate_pm_crypto_updown_allowed_intent_diagnostics(
        rows=rows,
        signal_report=_signal_report(rows),
    )

    assert payload["baseline_placebo_scope"] == "allowed_primary_shadow_intents_only"
    assert set(payload["allowed_primary_row_ids"]) == {
        "allow_fixture_win",
        "allow_fixture_loss",
        "allow_real_cached_win",
        "allow_real_cached_loss",
    }
    assert "synthetic_allow" not in payload["allowed_primary_row_ids"]
    assert payload["synthetic_rows_counted_as_primary"] is False
    assert payload["primary_claim_row_count"] == payload["allowed_primary_intent_count"]


def test_sequence44_discriminators_are_deterministic_and_cannot_invent_evidence() -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_allowed_intent_diagnostics import (
        evaluate_pm_crypto_updown_allowed_intent_diagnostics,
    )
    from quant_os.research.replay_candidates.pm_crypto_updown_discriminators import (
        evaluate_pm_crypto_updown_discriminators,
    )

    rows = _phase44_rows()
    diagnostics = evaluate_pm_crypto_updown_allowed_intent_diagnostics(
        rows=rows,
        signal_report=_signal_report(rows),
    )
    first = evaluate_pm_crypto_updown_discriminators(diagnostics=diagnostics)
    second = evaluate_pm_crypto_updown_discriminators(diagnostics=diagnostics)

    assert first == second
    assert first["input_allowed_primary_count"] == 4
    assert [item["name"] for item in first["discriminators"]] == [
        "SPOT_LAG_STRENGTH",
        "MARKET_UNDERREACTION_GAP",
        "SPREAD_QUALITY_FILTER",
        "LIQUIDITY_QUALITY_FILTER",
        "TIME_TO_WINDOW_END_FILTER",
        "COMBINED_CONSERVATIVE_FILTER",
    ]
    for item in first["discriminators"]:
        assert item["rows_kept"] + item["rows_rejected"] == first["input_allowed_primary_count"]
        assert item["rows_kept"] <= first["input_allowed_primary_count"]
        assert item["threshold_predeclared"] is True
        assert item["diagnostic_only"] is True
        assert item["result_vs_baseline"]["promotion_claimed"] is False
        assert item["result_vs_placebo"]["promotion_claimed"] is False


def test_sequence44_overfit_guard_blocks_too_thin_allowed_subsets() -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_allowed_intent_diagnostics import (
        evaluate_pm_crypto_updown_allowed_intent_diagnostics,
    )
    from quant_os.research.replay_candidates.pm_crypto_updown_discriminators import (
        evaluate_pm_crypto_updown_discriminators,
    )
    from quant_os.research.replay_candidates.pm_crypto_updown_overfit_guard import (
        evaluate_pm_crypto_updown_overfit_guard,
    )

    rows = _phase44_rows()
    diagnostics = evaluate_pm_crypto_updown_allowed_intent_diagnostics(
        rows=rows,
        signal_report=_signal_report(rows),
    )
    discriminators = evaluate_pm_crypto_updown_discriminators(diagnostics=diagnostics)
    payload = evaluate_pm_crypto_updown_overfit_guard(
        diagnostics=diagnostics,
        discriminator_report=discriminators,
    )

    assert payload["status"] == "ALLOWED_INTENTS_TOO_THIN"
    assert payload["passes"] is False
    assert "ALLOWED_PRIMARY_INTENTS_4_LT_5" in payload["blockers"]
    assert payload["live_trading_enabled"] is False


def test_sequence44_overfit_guard_blocks_one_row_dominance() -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_overfit_guard import (
        evaluate_pm_crypto_updown_overfit_guard,
    )

    diagnostics = {
        "allowed_primary_intent_count": 6,
        "allowed_real_cached_intent_count": 3,
        "allowed_synthetic_diagnostic_intent_count": 0,
        "synthetic_rows_counted_as_primary": False,
        "placebo_similarity_score": 0.02,
        "one_row_dominance_share": 0.75,
        "allowed_primary_rows": [{"clob_snapshot_id": f"row_{index}"} for index in range(6)],
    }
    discriminator_report = {
        "discriminators": [
            {
                "name": "SPOT_LAG_STRENGTH",
                "rows_kept": 6,
                "diagnostic_only": False,
                "threshold_predeclared": True,
            }
        ]
    }
    payload = evaluate_pm_crypto_updown_overfit_guard(
        diagnostics=diagnostics,
        discriminator_report=discriminator_report,
    )

    assert payload["status"] == "ONE_ROW_DOMINANCE"
    assert payload["passes"] is False
    assert "ONE_ROW_DOMINANCE_SHARE_0.750_GT_0.500" in payload["blockers"]


def test_sequence44_baseline_placebo_attribution_identifies_active_blocker(
    local_project: Path,
) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_allowed_intent_diagnostics import (
        evaluate_pm_crypto_updown_allowed_intent_diagnostics,
    )
    from quant_os.research.replay_candidates.pm_crypto_updown_baseline_placebo_attribution import (
        write_pm_crypto_updown_baseline_placebo_attribution_report,
    )

    rows = _phase44_rows()
    diagnostics = evaluate_pm_crypto_updown_allowed_intent_diagnostics(
        rows=rows,
        signal_report=_signal_report(rows),
    )
    payload = write_pm_crypto_updown_baseline_placebo_attribution_report(
        diagnostics=diagnostics,
        output_root=local_project,
    )

    assert payload["active_blocker"] == "BASELINE_OR_PLACEBO_BLOCKED"
    assert payload["candidate_needs_more_data_or_retirement"] in {
        "NEEDS_MORE_ALLOWED_INTENTS",
        "DEPRIORITIZE_CANDIDATE",
        "RETIRE_CANDIDATE",
    }
    assert payload["additional_allowed_primary_intents_required"] >= 1
    assert payload["candidate_meaningfully_different_from_placebo"] is False
    assert (
        local_project
        / "reports"
        / "sequence44"
        / "baseline_placebo_attribution"
        / "latest_baseline_placebo_attribution.json"
    ).exists()
    assert (
        local_project
        / "reports"
        / "sequence44"
        / "baseline_placebo_attribution"
        / "latest_baseline_placebo_attribution.md"
    ).exists()


def test_sequence44_candidate_decision_cannot_promote_if_baselines_or_placebos_block(
    local_project: Path,
) -> None:
    from quant_os.readiness.pm_crypto_updown_candidate_decision_report import (
        write_pm_crypto_updown_candidate_decision_report,
    )

    rows = _phase44_rows()
    payload = write_pm_crypto_updown_candidate_decision_report(
        rows=rows,
        signal_report=_signal_report(rows),
        output_root=local_project,
    )

    assert payload["decision_status"] != "READY_FOR_BOUNDED_SHADOW_REHEARSAL"
    assert payload["decision_status"] in {
        "NEEDS_MORE_ALLOWED_INTENTS",
        "NEEDS_MORE_REAL_CACHED_EVIDENCE",
        "BASELINE_OR_PLACEBO_BLOCKED",
        "OVERFIT_RISK_TOO_HIGH",
        "RETIRE_CANDIDATE",
        "DEPRIORITIZE_CANDIDATE",
        "CANDIDATE_REMAINS_BLOCKED",
    }
    assert payload["ready_for_bounded_shadow_rehearsal"] is False
    assert payload["not_live_readiness"] is True
    assert payload["not_canary_readiness"] is True
    assert payload["live_readiness_claimed"] is False
    assert payload["canary_readiness_claimed"] is False
    assert payload["execution_authority"] == "NONE"
    assert (
        local_project
        / "reports"
        / "sequence44"
        / "candidate_decision"
        / "latest_pm_crypto_updown_candidate_decision.json"
    ).exists()
    assert (
        local_project
        / "reports"
        / "sequence44"
        / "candidate_decision"
        / "latest_pm_crypto_updown_candidate_decision.md"
    ).exists()


def test_sequence44_candidate_decision_cannot_promote_if_overfit_guard_fails() -> None:
    from quant_os.readiness.pm_crypto_updown_candidate_decision import (
        evaluate_pm_crypto_updown_candidate_decision,
    )

    diagnostics = {
        "primary_evidence_row_count": 24,
        "real_cached_replay_ready_row_count": 14,
        "allowed_primary_intent_count": 6,
        "allowed_real_cached_intent_count": 4,
        "allowed_synthetic_diagnostic_intent_count": 0,
        "does_any_conservative_policy_allow_nonzero_intents": True,
        "synthetic_rows_counted_as_primary": False,
        "cost_fill_adjusted_result": 0.25,
        "active_blocker": "NONE",
        "blocker_causes": {"cost_fill_erosion": False},
    }
    attribution = {
        "active_blocker": "NONE",
        "candidate_beats_market_baseline": True,
        "candidate_beats_no_skill_baseline": True,
        "candidate_beats_or_separates_from_placebos": True,
        "market_baseline_dominant": False,
    }
    overfit = {
        "status": "ONE_ROW_DOMINANCE",
        "passes": False,
        "blockers": ["ONE_ROW_DOMINANCE_SHARE_0.750_GT_0.500"],
    }
    retirement = {"retirement_action": "CONTINUE_WITH_MORE_ALLOWED_INTENTS"}

    payload = evaluate_pm_crypto_updown_candidate_decision(
        diagnostics=diagnostics,
        attribution=attribution,
        overfit_guard=overfit,
        retirement=retirement,
    )

    assert payload["decision_status"] == "OVERFIT_RISK_TOO_HIGH"
    assert payload["ready_for_bounded_shadow_rehearsal"] is False


def test_sequence44_retirement_record_does_not_auto_retire_without_gate_status() -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_retirement import (
        evaluate_pm_crypto_updown_retirement,
    )

    payload = evaluate_pm_crypto_updown_retirement(
        decision_status="BASELINE_OR_PLACEBO_BLOCKED",
        diagnostics={"allowed_primary_intent_count": 4, "allowed_real_cached_intent_count": 2},
        attribution={"candidate_needs_more_data_or_retirement": "NEEDS_MORE_ALLOWED_INTENTS"},
    )

    assert payload["retirement_action"] == "CONTINUE_WITH_MORE_ALLOWED_INTENTS"
    assert payload["auto_retired"] is False
    assert payload["exact_next_data_need"] == "collect_at_least_1_more_allowed_primary_intent"


def test_sequence44_autonomy_milestones_keep_live_and_canary_blocked() -> None:
    from quant_os.readiness.autonomy_milestones import build_sequence44_autonomy_milestones

    payload = build_sequence44_autonomy_milestones(
        candidate_decision={
            "decision_status": "NEEDS_MORE_ALLOWED_INTENTS",
            "ready_for_bounded_shadow_rehearsal": False,
            "blockers": ["ALLOWED_PRIMARY_INTENTS_4_LT_5"],
            "autonomy_milestones": {"bounded_shadow_rehearsal": "blocked"},
        }
    )

    milestones = {item["milestone_id"]: item for item in payload["milestones"]}
    assert milestones["evidence_acquisition_repeatable"]["status"] == "MET"
    assert milestones["replay_inputs_sufficient"]["status"] == "MET"
    assert milestones["shadow_proving_threshold_met"]["status"] == "MET"
    assert milestones["bounded_shadow_rehearsal_ready"]["status"] == "BLOCKED"
    assert milestones["first_tiny_canary_allowed"]["status"] == "BLOCKED"
    assert payload["live_orders_allowed"] is False
    assert payload["live_trading_enabled"] is False


def test_sequence44_cli_make_targets_and_forbidden_paths_are_non_executing(
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
            "pm-crypto-updown-allowed-intent-diagnostics",
        ],
        [sys.executable, "-m", "quant_os.cli", "research", "pm-crypto-updown-discriminators"],
        [
            sys.executable,
            "-m",
            "quant_os.cli",
            "research",
            "pm-crypto-updown-baseline-placebo-attribution",
        ],
        [
            sys.executable,
            "-m",
            "quant_os.cli",
            "readiness",
            "pm-crypto-updown-candidate-decision",
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
    assert 'if "%TARGET%"=="sequence44-smoke"' in make_cmd
    assert 'if "%TARGET%"=="allowed-intent-diagnostics-smoke"' in make_cmd
    assert 'if "%TARGET%"=="candidate-decision-smoke"' in make_cmd

    source_paths = [
        "src/quant_os/research/replay_candidates/pm_crypto_updown_allowed_intent_diagnostics.py",
        "src/quant_os/research/replay_candidates/pm_crypto_updown_allowed_intent_report.py",
        "src/quant_os/research/replay_candidates/pm_crypto_updown_discriminators.py",
        "src/quant_os/research/replay_candidates/pm_crypto_updown_overfit_guard.py",
        "src/quant_os/research/replay_candidates/pm_crypto_updown_baseline_placebo_attribution.py",
        "src/quant_os/research/replay_candidates/pm_crypto_updown_retirement.py",
        "src/quant_os/readiness/pm_crypto_updown_candidate_decision.py",
        "src/quant_os/readiness/pm_crypto_updown_candidate_decision_report.py",
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
