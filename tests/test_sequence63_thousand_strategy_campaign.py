from __future__ import annotations

import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path


def test_sequence63_social_intake_treats_x_as_hypotheses_not_proof(local_project: Path) -> None:
    from quant_os.research.social_hypotheses.x_quant_batch_intake import (
        write_x_quant_hypotheses_report,
    )

    zip_path = local_project / "x_capture.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr(
            "posts.txt",
            "huge pnl screenshot copy trade wallet mirror stealth browser captcha proxy "
            "up down basket arbitrage weather forecast mismatch orderbook imbalance",
        )

    payload = write_x_quant_hypotheses_report(zip_path=zip_path, output_root=local_project)

    assert payload["status"] == "X_QUANT_HYPOTHESES_EXTRACTED"
    assert payload["social_claims_are_proof"] is False
    assert payload["unsafe_claims_rejected"] >= 3
    assert "COPY_TRADE_OR_WALLET_FOLLOWING_REJECTED" in payload["rejection_reasons"]
    assert "STEALTH_OR_ANTI_BOT_TOOLING_REJECTED" in payload["rejection_reasons"]
    assert payload["safe_hypotheses_count"] >= 3
    assert payload["execution_authority"] == "NONE"
    assert payload["live_trading_enabled"] is False


def test_sequence63_strategy_research_uses_public_sources_and_blocks_hype(
    local_project: Path,
) -> None:
    from quant_os.research.strategy_factory.strategy_research import (
        write_strategy_research_report,
    )

    payload = write_strategy_research_report(output_root=local_project)

    assert payload["status"] == "STRATEGY_RESEARCH_READY"
    assert len(payload["families"]) >= 15
    assert all(card["eligible_for_live_sim"] for card in payload["families"][:10])
    assert all(card["social_or_web_claim_is_proof"] is False for card in payload["families"])
    assert any("developers.binance.com" in source["url"] for source in payload["sources"])
    assert any("docs.polymarket.com" in source["url"] for source in payload["sources"])
    assert any("docs.kalshi.com" in source["url"] for source in payload["sources"])
    assert any("weather.gov" in source["url"] for source in payload["sources"])


def test_sequence63_generator_preregisters_1000_deterministic_safe_variants(
    local_project: Path,
) -> None:
    from quant_os.research.strategy_factory.strategy_variant_generator import (
        generate_strategy_variants,
        write_strategy_variants_report,
    )

    first = generate_strategy_variants(target_count=1000)
    second = generate_strategy_variants(target_count=1000)
    report = write_strategy_variants_report(output_root=local_project, target_count=1000)

    assert first == second
    assert len(first) >= 1000
    assert report["status"] == "STRATEGY_VARIANTS_PREREGISTERED"
    assert report["variant_count"] >= 1000
    assert report["pre_registered_before_testing"] is True
    assert len({variant["family"] for variant in first}) >= 15
    assert len({asset for variant in first for asset in variant["assets"]}) >= 5
    assert all(variant["pre_registration_timestamp"] for variant in first)
    assert all(variant["no_live_metadata"]["order_transmission_enabled"] is False for variant in first)
    assert all(variant["no_live_metadata"]["request_signing_enabled"] is False for variant in first)


def test_sequence63_tournament_is_staged_and_failure_is_checkpoint_not_completion(
    local_project: Path,
) -> None:
    from quant_os.research.strategy_factory.strategy_tournament import (
        write_strategy_tournament_report,
    )

    payload = write_strategy_tournament_report(output_root=local_project)

    assert payload["status"] == "THOUSAND_STRATEGY_CAMPAIGN_CHECKPOINTED_NOT_COMPLETE"
    assert payload["variants_generated"] >= 1000
    assert payload["variants_tested"] >= 250
    assert payload["stage_counts"]["stage1_tested"] >= 250
    assert payload["stage_counts"]["stage2_tested"] >= 50
    assert payload["stage_counts"]["stage3_tested"] >= 10
    assert payload["campaign_complete"] is False
    assert payload["top_candidates"][0]["status"] in {
        "STRATEGY_RETIRED",
        "NEEDS_MORE_OBSERVATIONS",
        "MONEY_WORTHY_NOT_PROVEN",
    }
    assert len(payload["leaderboard_top_50"]) == 50


def test_sequence63_overfit_guard_blocks_multiple_testing_leakage_and_fragility(
    local_project: Path,
) -> None:
    from quant_os.proving.thousand_strategy_overfit_guard import (
        build_thousand_strategy_overfit_guard,
        write_thousand_strategy_overfit_guard_report,
    )

    guard = write_thousand_strategy_overfit_guard_report(output_root=local_project)
    leakage = build_thousand_strategy_overfit_guard(
        attempted_variants=1000,
        top_candidate={
            "holdout_passed": True,
            "purged_validation_passed": False,
            "neighbor_parameter_pass_rate": 0.2,
            "placebo_survives_similarly": True,
            "adjusted_performance_significant": False,
        },
    )

    assert guard["status"] == "OVERFIT_GUARD_BLOCKED"
    assert "MULTIPLE_TESTING_PENALTY_REQUIRED" in guard["blockers"]
    assert "HOLDOUT_OR_FORWARD_WINDOW_NOT_PROVEN" in guard["blockers"]
    assert "PURGED_NO_LEAKAGE_VALIDATION_NOT_PASSED" in leakage["blockers"]
    assert "NEIGHBORING_PARAMETERS_FAIL_ROBUSTNESS" in leakage["blockers"]
    assert "PLACEBO_SURVIVES_SIMILARLY" in leakage["blockers"]


def test_sequence63_conflict_repeatability_capacity_and_readiness_block_promotion(
    local_project: Path,
) -> None:
    from quant_os.proving.thousand_strategy_capacity import write_thousand_strategy_capacity_report
    from quant_os.proving.thousand_strategy_repeatability import (
        write_thousand_strategy_repeatability_report,
    )
    from quant_os.readiness.money_worthy_strategy_readiness import (
        build_money_worthy_strategy_readiness,
    )
    from quant_os.risk.strategy_conflict_detector import write_strategy_conflict_detector_report

    conflict = write_strategy_conflict_detector_report(
        output_root=local_project,
        candidate={
            "strategy_signal": "buy",
            "regime_signal": "sell",
            "edge_bps": 4.0,
            "execution_uncertainty_bps": 8.0,
        },
    )
    repeatability = write_thousand_strategy_repeatability_report(output_root=local_project)
    capacity = write_thousand_strategy_capacity_report(output_root=local_project)
    readiness = build_money_worthy_strategy_readiness(
        tournament={"current_best_candidate": {"id": "tsv_test", "fake_net_pnl": 12.0}},
        overfit={"status": "OVERFIT_GUARD_BLOCKED"},
        conflict=conflict,
        repeatability=repeatability,
        capacity=capacity,
        fresh_repro={"status": "FRESH_REPRO_BLOCKED"},
    )

    assert conflict["status"] == "CONFLICT_DETECTOR_VETOED"
    assert "REGIME_CONFLICT" in conflict["veto_reasons"]
    assert "EDGE_SMALLER_THAN_EXECUTION_UNCERTAINTY" in conflict["veto_reasons"]
    assert repeatability["status"] == "REPEATABILITY_BLOCKED"
    assert "ONE_TRADE_DOMINANCE_TOO_HIGH" in repeatability["blockers"]
    assert "ONE_WINDOW_DOMINANCE_TOO_HIGH" in repeatability["blockers"]
    assert "ONE_ASSET_DOMINANCE_TOO_HIGH" in repeatability["blockers"]
    assert capacity["status"] == "CAPACITY_TINY_CANARY_PASSED"
    assert capacity["scalability_claim_allowed"] is False
    assert "CAPACITY_ABOVE_1_USD_NOT_SUPPORTED" in capacity["scalability_blockers"]
    assert readiness["status"] == "MONEY_WORTHY_BLOCKED_BY_OVERFIT"
    assert readiness["campaign_complete"] is False


def test_sequence63_fake_intents_are_no_transmit_unsigned_and_pnl_uses_future_marks(
    local_project: Path,
) -> None:
    from quant_os.autonomy.variant_live_sim_fill import write_variant_live_sim_fill_report
    from quant_os.autonomy.variant_live_sim_intents import write_variant_live_sim_intents_report
    from quant_os.autonomy.variant_live_sim_pnl import write_variant_live_sim_pnl_report

    intents = write_variant_live_sim_intents_report(output_root=local_project)
    fills = write_variant_live_sim_fill_report(output_root=local_project)
    pnl = write_variant_live_sim_pnl_report(output_root=local_project)

    assert intents["status"] == "VARIANT_LIVE_SIM_INTENTS_READY"
    assert all(intent["fake_money"] is True for intent in intents["intents"])
    assert all(intent["no_transmit"] is True for intent in intents["intents"])
    assert all("signed_headers" not in intent for intent in intents["intents"])
    assert all("order" not in intent["endpoint"].lower() for intent in intents["intents"])
    assert fills["guaranteed_fill"] is False
    assert all(row["mark_timestamp"] > row["entry_timestamp"] for row in pnl["pnl_rows"])
    assert pnl["lookahead_detected"] is False


def test_sequence63_scheduler_fresh_repro_manual_packet_and_state_are_blocked_until_proven(
    local_project: Path,
) -> None:
    from quant_os.autonomy.thousand_strategy_campaign_schedule import (
        write_thousand_strategy_campaign_schedule_report,
    )
    from quant_os.readiness.money_worthy_strategy_readiness_report import (
        write_money_worthy_strategy_readiness_report,
    )
    from quant_os.readiness.thousand_strategy_manual_canary_packet import (
        write_thousand_strategy_manual_canary_packet,
    )

    readiness = write_money_worthy_strategy_readiness_report(output_root=local_project)
    packet = write_thousand_strategy_manual_canary_packet(output_root=local_project)
    schedule = write_thousand_strategy_campaign_schedule_report(output_root=local_project)
    state = json.loads(
        (
            local_project / "reports/thousand_strategy_campaign/state/latest_state.json"
        ).read_text(encoding="utf-8")
    )

    assert readiness["status"] != "MONEY_WORTHY_CANARY_GRADE_PROFITABILITY_PROVEN"
    assert packet["status"] == "FIRST_TINY_MANUAL_CANARY_PACKET_BLOCKED"
    assert schedule["status"] == "THOUSAND_STRATEGY_CAMPAIGN_SCHEDULE_READY"
    assert "no credentials" in schedule["powershell_command"].lower()
    assert "no orders" in schedule["powershell_command"].lower()
    assert state["campaign_status"] == "THOUSAND_STRATEGY_CAMPAIGN_CHECKPOINTED_NOT_COMPLETE"
    assert state["money_worthy_readiness_status"] != "MONEY_WORTHY_CANARY_GRADE_PROFITABILITY_PROVEN"
    assert state["safety_state"]["actual_order_count"] == 0
    assert state["safety_state"]["actual_cancel_count"] == 0


def test_sequence63_cli_make_targets_are_fixture_safe(local_project: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = {**os.environ, "PYTHONPATH": str(repo_root / "src")}
    commands = [
        [sys.executable, "-m", "quant_os.cli", "research", "x-quant-hypothesis-intake"],
        [sys.executable, "-m", "quant_os.cli", "research", "strategy-research"],
        [sys.executable, "-m", "quant_os.cli", "research", "generate-strategy-variants"],
        [sys.executable, "-m", "quant_os.cli", "research", "strategy-tournament"],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "variant-live-sim-run"],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "variant-public-forward-live-sim"],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "variant-public-forward-observe"],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "variant-public-forward-intents"],
        [
            sys.executable,
            "-m",
            "quant_os.cli",
            "autonomy",
            "variant-public-forward-fills-and-marks",
        ],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "variant-public-forward-cycle"],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "variant-public-forward-batch-cycle"],
        [
            sys.executable,
            "-m",
            "quant_os.cli",
            "autonomy",
            "variant-public-forward-candidate-archive",
        ],
        [sys.executable, "-m", "quant_os.cli", "proving", "thousand-strategy-overfit-guard"],
        [sys.executable, "-m", "quant_os.cli", "proving", "thousand-strategy-public-forward-evidence"],
        [sys.executable, "-m", "quant_os.cli", "risk", "strategy-conflict-detector"],
        [sys.executable, "-m", "quant_os.cli", "proving", "thousand-strategy-repeatability"],
        [sys.executable, "-m", "quant_os.cli", "proving", "thousand-strategy-capacity"],
        [sys.executable, "-m", "quant_os.cli", "readiness", "thousand-strategy-fresh-repro"],
        [sys.executable, "-m", "quant_os.cli", "readiness", "money-worthy-strategy"],
        [sys.executable, "-m", "quant_os.cli", "readiness", "thousand-strategy-manual-canary-packet"],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "thousand-strategy-schedule"],
    ]

    for command in commands:
        result = subprocess.run(
            command,
            cwd=local_project,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert "ORDER_SENT" not in result.stdout
        assert "LIVE_READY" not in result.stdout
        assert "AUTONOMOUS_LIVE_READY" not in result.stdout
        assert "ORDER_READY_TO_SEND" not in result.stdout

    make_cmd = (repo_root / "make.cmd").read_text(encoding="utf-8")
    assert 'if "%TARGET%"=="thousand-strategy-campaign-smoke"' in make_cmd
    assert 'if "%TARGET%"=="thousand-strategy-public-run"' in make_cmd
    assert 'if "%TARGET%"=="sequence63-smoke"' in make_cmd
