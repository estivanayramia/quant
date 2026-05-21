from __future__ import annotations

import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path


def test_sequence64_generates_second_1000_without_reusing_variant_ids(
    local_project: Path,
) -> None:
    from quant_os.research.strategy_factory.strategy_variant_generator import (
        generate_strategy_variants,
        write_strategy_variants_report,
    )

    batch1 = generate_strategy_variants(target_count=1000, batch_index=1)
    batch2 = generate_strategy_variants(target_count=1000, batch_index=2)
    batch1_report = write_strategy_variants_report(
        output_root=local_project,
        target_count=1000,
        batch_index=1,
    )
    batch2_report = write_strategy_variants_report(
        output_root=local_project,
        target_count=1000,
        batch_index=2,
    )

    assert len(batch1) == 1000
    assert len(batch2) == 1000
    assert {variant["id"] for variant in batch1}.isdisjoint({variant["id"] for variant in batch2})
    assert batch1_report["batch_index"] == 1
    assert batch2_report["batch_index"] == 2
    assert batch2_report["variant_count"] == 1000
    assert batch2_report["cumulative_variant_count"] == 2000
    assert batch2_report["pre_registered_before_testing"] is True
    assert all(variant["batch_index"] == 2 for variant in batch2)
    assert all(variant["no_live_metadata"]["actual_order_count"] == 0 for variant in batch2)


def test_sequence64_batches_rotate_to_new_structural_variant_shapes() -> None:
    from quant_os.research.strategy_factory.strategy_variant_generator import (
        generate_strategy_variants,
    )

    batch1 = generate_strategy_variants(target_count=1000, batch_index=1)
    batch2 = generate_strategy_variants(target_count=1000, batch_index=2)

    assert _variant_shape_keys(batch1).isdisjoint(_variant_shape_keys(batch2))


def test_sequence64_wraparound_enters_new_structural_universe_cycle() -> None:
    from quant_os.research.strategy_factory.strategy_variant_generator import (
        generate_strategy_variants,
    )

    batch1 = generate_strategy_variants(target_count=1000, batch_index=1)
    batch42 = generate_strategy_variants(target_count=1000, batch_index=42)

    assert _variant_shape_keys(batch1).isdisjoint(_variant_shape_keys(batch42))
    assert {variant["universe_cycle"] for variant in batch42} == {0, 1}
    assert any(variant["thresholds"]["universe_cycle"] == 1.0 for variant in batch42)


def test_sequence64_next_tranche_tournament_updates_cumulative_checkpoint(
    local_project: Path,
) -> None:
    from quant_os.research.strategy_factory.strategy_tournament import (
        write_next_strategy_tranche_report,
        write_strategy_tournament_report,
    )

    first = write_strategy_tournament_report(output_root=local_project, batch_index=1)
    second = write_strategy_tournament_report(output_root=local_project, batch_index=2)
    state = json.loads(
        (
            local_project / "reports/thousand_strategy_campaign/state/latest_state.json"
        ).read_text(encoding="utf-8")
    )

    assert first["batch_index"] == 1
    assert second["batch_index"] == 2
    assert second["variants_generated"] == 1000
    assert second["cumulative_variants_generated"] == 2000
    assert second["variants_tested"] == 250
    assert second["cumulative_variants_tested"] == 500
    assert second["campaign_complete"] is False
    assert state["campaign_status"] == "THOUSAND_STRATEGY_CAMPAIGN_CHECKPOINTED_NOT_COMPLETE"
    assert state["variants_generated"] == 2000
    assert state["variants_tested"] == 500
    assert state["last_completed_batch_index"] == 2
    assert state["manual_canary_packet_status"] == "FIRST_TINY_MANUAL_CANARY_PACKET_BLOCKED"

    dynamic_third = write_next_strategy_tranche_report(output_root=local_project)
    state_after_dynamic = json.loads(
        (
            local_project / "reports/thousand_strategy_campaign/state/latest_state.json"
        ).read_text(encoding="utf-8")
    )
    assert dynamic_third["batch_index"] == 3
    assert dynamic_third["cumulative_variants_generated"] == 3000
    assert dynamic_third["cumulative_variants_tested"] == 750
    assert state_after_dynamic["last_completed_batch_index"] == 3
    assert state_after_dynamic["exact_resume_command"] == ".\\make.cmd thousand-strategy-next-tranche"


def test_sequence64_campaign_state_write_recovers_from_empty_state_file(
    local_project: Path,
) -> None:
    from quant_os.research.strategy_factory.campaign_common import write_campaign_state

    state_dir = local_project / "reports/thousand_strategy_campaign/state"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "latest_state.json").write_text("", encoding="utf-8")

    state = write_campaign_state(
        output_root=local_project,
        variants_generated=123,
        blockers=["RECOVERED_EMPTY_STATE_FILE"],
    )
    persisted = json.loads((state_dir / "latest_state.json").read_text(encoding="utf-8"))

    assert state["variants_generated"] == 123
    assert persisted["variants_generated"] == 123
    assert persisted["blockers"] == ["RECOVERED_EMPTY_STATE_FILE"]
    assert persisted["live_trading_enabled"] is False
    assert persisted["actual_order_count"] == 0


def test_sequence64_tournament_preserves_cumulative_leaderboard_across_tranches(
    local_project: Path,
) -> None:
    from quant_os.research.strategy_factory.strategy_tournament import (
        write_next_strategy_tranche_report,
        write_strategy_tournament_report,
    )

    first = write_strategy_tournament_report(output_root=local_project, batch_index=1)
    second = write_next_strategy_tranche_report(output_root=local_project)
    state = json.loads(
        (
            local_project / "reports/thousand_strategy_campaign/state/latest_state.json"
        ).read_text(encoding="utf-8")
    )

    cumulative_signatures = {
        candidate["structural_signature"] for candidate in second["cumulative_leaderboard_top_50"]
    }
    first_batch_signatures = {
        candidate["structural_signature"] for candidate in first["leaderboard_top_50"]
    }
    second_batch_signatures = {
        candidate["structural_signature"] for candidate in second["leaderboard_top_50"]
    }

    assert second["batch_index"] == 2
    assert first_batch_signatures & cumulative_signatures
    assert second_batch_signatures & cumulative_signatures
    assert len(second["cumulative_leaderboard_top_50"]) == 50
    assert second["cumulative_top_candidates"][0]["id"] == state["current_best_candidate"]["id"]
    assert state["cumulative_leaderboard_top_50"][0]["id"] == state["current_best_candidate"]["id"]


def test_sequence64_cumulative_leaderboard_dedupes_repeated_strategy_shapes(
    local_project: Path,
) -> None:
    from quant_os.research.strategy_factory.strategy_tournament import (
        write_next_strategy_tranche_report,
        write_strategy_tournament_report,
    )

    first = write_strategy_tournament_report(output_root=local_project, batch_index=1)
    second = write_next_strategy_tranche_report(output_root=local_project)

    first_signature = first["current_best_candidate"]["structural_signature"]
    second_signature = second["latest_batch_best_candidate"]["structural_signature"]
    cumulative_signatures = [
        candidate["structural_signature"]
        for candidate in second["cumulative_leaderboard_top_50"]
    ]

    assert first_signature != second_signature
    assert len(cumulative_signatures) == len(set(cumulative_signatures))
    assert cumulative_signatures.count(first_signature) == 1
    assert cumulative_signatures.count(second_signature) == 1


def test_sequence64_tournament_prefers_baseline_and_placebo_survivors() -> None:
    from quant_os.research.strategy_factory.strategy_tournament import run_strategy_tournament

    payload = run_strategy_tournament(batch_index=1)
    best = payload["current_best_candidate"]

    assert any(
        candidate["baseline_beaten"] and candidate["placebo_beaten"]
        for candidate in payload["leaderboard_top_50"]
    )
    assert best["baseline_beaten"] is True
    assert best["placebo_beaten"] is True
    assert best["fake_net_pnl"] > 0


def test_sequence64_tournament_scores_do_not_plateau_across_tranches() -> None:
    from quant_os.research.strategy_factory.strategy_tournament import run_strategy_tournament

    best_candidates = [
        run_strategy_tournament(batch_index=batch_index)["current_best_candidate"]
        for batch_index in (1, 2, 42, 100)
    ]

    assert len({(candidate["fake_net_pnl"], candidate["score"]) for candidate in best_candidates}) > 1


def test_sequence64_repeatability_removes_baseline_blocker_for_baseline_placebo_survivor() -> None:
    from quant_os.proving.thousand_strategy_repeatability import (
        build_thousand_strategy_repeatability,
    )

    repeatability = build_thousand_strategy_repeatability(
        candidate={"baseline_beaten": True, "placebo_beaten": True},
    )

    assert repeatability["status"] == "REPEATABILITY_BLOCKED"
    assert "BASELINE_NOT_BEATEN_IN_ALL_WINDOWS" not in repeatability["blockers"]
    assert "ONE_TRADE_DOMINANCE_TOO_HIGH" in repeatability["blockers"]
    assert repeatability["baseline_beaten"] is True
    assert repeatability["placebo_beaten"] is True


def test_sequence64_repeatability_can_pass_only_with_full_candidate_evidence() -> None:
    from quant_os.proving.thousand_strategy_repeatability import (
        build_thousand_strategy_repeatability,
    )

    repeatability = build_thousand_strategy_repeatability(
        candidate={
            "baseline_beaten": True,
            "placebo_beaten": True,
            "one_trade_dominance": 0.12,
            "one_window_dominance": 0.21,
            "one_asset_dominance": 0.3,
            "stress_tests": {
                "exclude_top_trade": "PASSED",
                "exclude_top_5_trades": "PASSED",
                "delayed_entry": "PASSED",
                "worse_fill": "PASSED",
                "higher_fee": "PASSED",
            },
        },
    )

    assert repeatability["status"] == "REPEATABILITY_PASSED"
    assert repeatability["blockers"] == []


def test_sequence64_overfit_guard_can_pass_with_multiple_testing_adjusted_evidence() -> None:
    from quant_os.proving.thousand_strategy_overfit_guard import (
        build_thousand_strategy_overfit_guard,
    )

    overfit = build_thousand_strategy_overfit_guard(
        attempted_variants=100000,
        top_candidate={
            "multiple_testing_adjusted": True,
            "holdout_passed": True,
            "purged_validation_passed": True,
            "neighbor_parameter_pass_rate": 0.72,
            "placebo_survives_similarly": False,
            "adjusted_performance_significant": True,
        },
    )

    assert overfit["status"] == "OVERFIT_GUARD_PASSED"
    assert overfit["blockers"] == []


def test_sequence64_capacity_distinguishes_tiny_canary_from_scalability() -> None:
    from quant_os.proving.thousand_strategy_capacity import build_thousand_strategy_capacity

    capacity = build_thousand_strategy_capacity()

    assert capacity["status"] == "CAPACITY_TINY_CANARY_PASSED"
    assert capacity["capacity_by_size"]["1_usd"]["supported"] is True
    assert capacity["capacity_by_size"]["5_usd"]["supported"] is False
    assert capacity["max_safe_notional_usd"] == 1.0
    assert capacity["scalability_claim_allowed"] is False
    assert "CAPACITY_ABOVE_1_USD_NOT_SUPPORTED" in capacity["scalability_blockers"]
    assert "CAPACITY_ABOVE_1_USD_NOT_SUPPORTED" not in capacity["blockers"]


def test_sequence64_readiness_refreshes_repeatability_report_for_selected_candidate(
    local_project: Path,
) -> None:
    from quant_os.readiness.money_worthy_strategy_readiness_report import (
        write_money_worthy_strategy_readiness_report,
    )
    from quant_os.readiness.thousand_strategy_fresh_repro import (
        write_thousand_strategy_fresh_repro_report,
    )
    from quant_os.research.strategy_factory.strategy_tournament import (
        write_strategy_tournament_report,
    )

    tournament = write_strategy_tournament_report(output_root=local_project, batch_index=1)
    assert tournament["current_best_candidate"]["baseline_beaten"] is True
    assert tournament["current_best_candidate"]["placebo_beaten"] is True
    write_thousand_strategy_fresh_repro_report(
        output_root=local_project,
        proof_command_passed=True,
    )
    write_money_worthy_strategy_readiness_report(output_root=local_project)
    repeatability = json.loads(
        (
            local_project / "reports/thousand_strategy_campaign/repeatability/latest_repeatability.json"
        ).read_text(encoding="utf-8")
    )

    assert repeatability["baseline_beaten"] is True
    assert repeatability["placebo_beaten"] is True
    assert "BASELINE_NOT_BEATEN_IN_ALL_WINDOWS" not in repeatability["blockers"]
    assert "PLACEBO_NOT_BEATEN_IN_ALL_WINDOWS" not in repeatability["blockers"]


def test_sequence64_readiness_refreshes_conflict_report_for_selected_candidate(
    local_project: Path,
) -> None:
    from quant_os.readiness.money_worthy_strategy_readiness_report import (
        write_money_worthy_strategy_readiness_report,
    )
    from quant_os.readiness.thousand_strategy_fresh_repro import (
        write_thousand_strategy_fresh_repro_report,
    )
    from quant_os.research.strategy_factory.strategy_tournament import (
        write_strategy_tournament_report,
    )

    tournament = write_strategy_tournament_report(output_root=local_project, batch_index=1)
    best = tournament["current_best_candidate"]
    assert best["baseline_beaten"] is True
    assert best["placebo_beaten"] is True
    write_thousand_strategy_fresh_repro_report(
        output_root=local_project,
        proof_command_passed=True,
    )
    readiness = write_money_worthy_strategy_readiness_report(output_root=local_project)
    conflict = json.loads(
        (
            local_project
            / "reports/thousand_strategy_campaign/conflict_detector/latest_conflict_detector.json"
        ).read_text(encoding="utf-8")
    )

    assert conflict["candidate"]["selected_strategy_id"] == best["id"]
    assert conflict["status"] == "CONFLICT_DETECTOR_PASSED"
    assert conflict["veto_reasons"] == []
    assert "CONFLICT_DETECTOR_NOT_PASSED" not in readiness["blockers"]


def test_sequence64_readiness_uses_persisted_cumulative_tournament_candidate(
    local_project: Path,
) -> None:
    from quant_os.readiness.money_worthy_strategy_readiness_report import (
        write_money_worthy_strategy_readiness_report,
    )
    from quant_os.readiness.thousand_strategy_fresh_repro import (
        write_thousand_strategy_fresh_repro_report,
    )
    from quant_os.research.strategy_factory.strategy_tournament import (
        write_next_strategy_tranche_report,
        write_strategy_tournament_report,
    )

    write_strategy_tournament_report(output_root=local_project, batch_index=1)
    persisted_tournament = write_next_strategy_tranche_report(output_root=local_project)
    persisted_best = persisted_tournament["current_best_candidate"]
    latest_batch_best = persisted_tournament["latest_batch_best_candidate"]
    assert persisted_best["id"] != latest_batch_best["id"]

    write_thousand_strategy_fresh_repro_report(
        output_root=local_project,
        proof_command_passed=True,
    )
    readiness = write_money_worthy_strategy_readiness_report(output_root=local_project)
    state = json.loads(
        (
            local_project / "reports/thousand_strategy_campaign/state/latest_state.json"
        ).read_text(encoding="utf-8")
    )

    assert readiness["current_best_candidate"]["id"] == persisted_best["id"]
    assert state["current_best_candidate"]["id"] == persisted_best["id"]


def test_sequence64_readiness_feeds_candidate_evidence_to_overfit_and_repeatability(
    local_project: Path,
) -> None:
    from quant_os.readiness.money_worthy_strategy_readiness_report import (
        write_money_worthy_strategy_readiness_report,
    )
    from quant_os.readiness.thousand_strategy_fresh_repro import (
        write_thousand_strategy_fresh_repro_report,
    )
    from quant_os.research.strategy_factory.strategy_tournament import (
        write_strategy_tournament_report,
    )

    tournament = write_strategy_tournament_report(output_root=local_project, batch_index=1)
    candidate = tournament["current_best_candidate"]
    candidate.update(
        {
            "multiple_testing_adjusted": True,
            "holdout_passed": True,
            "purged_validation_passed": True,
            "neighbor_parameter_pass_rate": 0.72,
            "placebo_survives_similarly": False,
            "adjusted_performance_significant": True,
            "one_trade_dominance": 0.12,
            "one_window_dominance": 0.21,
            "one_asset_dominance": 0.3,
            "stress_tests": {
                "exclude_top_trade": "PASSED",
                "exclude_top_5_trades": "PASSED",
                "delayed_entry": "PASSED",
                "worse_fill": "PASSED",
                "higher_fee": "PASSED",
            },
        },
    )
    tournament["current_best_candidate"] = candidate
    tournament["cumulative_top_candidates"] = [candidate]
    tournament["cumulative_leaderboard_top_50"][0] = candidate
    tournament_path = (
        local_project
        / "reports/thousand_strategy_campaign/tournament/latest_tournament.json"
    )
    tournament_path.write_text(json.dumps(tournament, indent=2, sort_keys=True), encoding="utf-8")
    write_thousand_strategy_fresh_repro_report(
        output_root=local_project,
        proof_command_passed=True,
    )

    readiness = write_money_worthy_strategy_readiness_report(output_root=local_project)

    assert readiness["overfit_status"] == "OVERFIT_GUARD_PASSED"
    assert readiness["repeatability_status"] == "REPEATABILITY_PASSED"
    assert "OVERFIT_GUARD_NOT_PASSED" not in readiness["blockers"]
    assert "REPEATABILITY_NOT_PASSED" not in readiness["blockers"]
    assert readiness["status"] == "MONEY_WORTHY_NOT_PROVEN"
    assert "PUBLIC_FORWARD_EVIDENCE_NOT_PROVEN" in readiness["blockers"]


def test_sequence64_readiness_requires_public_forward_evidence_for_success() -> None:
    from quant_os.readiness.money_worthy_strategy_readiness import (
        SUCCESS,
        build_money_worthy_strategy_readiness,
    )

    base_candidate = {
        "id": "tsv_public_candidate",
        "fake_net_pnl": 10.0,
        "public_forward_evidence_proven": True,
        "evidence_source": "public_forward_live_sim",
    }
    common_gates = {
        "overfit": {"status": "OVERFIT_GUARD_PASSED"},
        "conflict": {"status": "CONFLICT_DETECTOR_PASSED"},
        "repeatability": {"status": "REPEATABILITY_PASSED"},
        "capacity": {"status": "CAPACITY_TINY_CANARY_PASSED"},
        "fresh_repro": {"status": "FRESH_REPRO_PASSED"},
    }

    public_readiness = build_money_worthy_strategy_readiness(
        tournament={"current_best_candidate": base_candidate},
        **common_gates,
    )
    synthetic_readiness = build_money_worthy_strategy_readiness(
        tournament={
            "current_best_candidate": {
                **base_candidate,
                "public_forward_evidence_proven": False,
                "evidence_source": "synthetic_strategy_factory_fixture",
            },
        },
        **common_gates,
    )

    assert public_readiness["status"] == SUCCESS
    assert synthetic_readiness["status"] == "MONEY_WORTHY_NOT_PROVEN"
    assert "PUBLIC_FORWARD_EVIDENCE_NOT_PROVEN" in synthetic_readiness["blockers"]


def test_sequence64_public_forward_evidence_blocks_fixture_or_unmatched_data(
    local_project: Path,
) -> None:
    from quant_os.proving.thousand_strategy_public_forward_evidence import (
        build_thousand_strategy_public_forward_evidence,
    )

    candidate = {"id": "tsv_real_candidate", "fake_net_pnl": 10.0}
    fixture_evidence = build_thousand_strategy_public_forward_evidence(
        candidate=candidate,
        live_sim_summary={
            "selected_strategy_id": "tsv_real_candidate",
            "status": "VARIANT_LIVE_SIM_SUMMARY_READY",
            "data_sources": ["public_fixture_safe_market_data"],
            "observation_count": 5000,
            "eligible_intent_count": 500,
            "completed_mark_count": 300,
            "fake_net_pnl": 10.0,
            "public_forward_evidence_proven": True,
            "evidence_source": "public_forward_live_sim",
        },
        reconciliation={"status": "VARIANT_LIVE_SIM_RECONCILIATION_PASSED"},
    )
    mismatch_evidence = build_thousand_strategy_public_forward_evidence(
        candidate=candidate,
        live_sim_summary={
            "selected_strategy_id": "other_candidate",
            "status": "VARIANT_LIVE_SIM_SUMMARY_READY",
            "data_sources": ["kraken_public_rest_unauthenticated_forward"],
            "observation_count": 5000,
            "eligible_intent_count": 500,
            "completed_mark_count": 300,
            "fake_net_pnl": 10.0,
            "public_forward_evidence_proven": True,
            "evidence_source": "public_forward_live_sim",
        },
        reconciliation={"status": "VARIANT_LIVE_SIM_RECONCILIATION_PASSED"},
    )

    assert fixture_evidence["status"] == "PUBLIC_FORWARD_EVIDENCE_BLOCKED"
    assert "FIXTURE_DATA_NOT_PUBLIC_FORWARD_EVIDENCE" in fixture_evidence["blockers"]
    assert mismatch_evidence["status"] == "PUBLIC_FORWARD_EVIDENCE_BLOCKED"
    assert "SELECTED_STRATEGY_ID_MISMATCH" in mismatch_evidence["blockers"]


def test_sequence64_public_forward_evidence_can_pass_with_strict_public_candidate_match() -> None:
    from quant_os.proving.thousand_strategy_public_forward_evidence import (
        build_thousand_strategy_public_forward_evidence,
    )

    evidence = build_thousand_strategy_public_forward_evidence(
        candidate={"id": "tsv_real_candidate", "fake_net_pnl": 10.0},
        live_sim_summary={
            "selected_strategy_id": "tsv_real_candidate",
            "status": "VARIANT_LIVE_SIM_SUMMARY_READY",
            "data_sources": ["kraken_public_rest_unauthenticated_forward"],
            "observation_count": 5000,
            "eligible_intent_count": 500,
            "completed_mark_count": 300,
            "fake_net_pnl": 10.0,
            "public_forward_evidence_proven": True,
            "evidence_source": "public_forward_live_sim",
        },
        reconciliation={"status": "VARIANT_LIVE_SIM_RECONCILIATION_PASSED"},
    )

    assert evidence["status"] == "PUBLIC_FORWARD_EVIDENCE_PASSED"
    assert evidence["blockers"] == []
    assert evidence["candidate_evidence"]["public_forward_evidence_proven"] is True
    assert evidence["candidate_evidence"]["evidence_source"] == "public_forward_live_sim"


def test_sequence64_candidate_public_forward_live_sim_is_selected_and_pending(
    local_project: Path,
) -> None:
    from quant_os.autonomy.variant_public_forward_live_sim import (
        write_variant_public_forward_live_sim_summary,
    )
    from quant_os.proving.thousand_strategy_public_forward_evidence import (
        write_thousand_strategy_public_forward_evidence_report,
    )
    from quant_os.research.strategy_factory.strategy_tournament import (
        write_strategy_tournament_report,
    )

    tournament = write_strategy_tournament_report(output_root=local_project, batch_index=1)
    candidate_id = tournament["current_best_candidate"]["id"]
    summary = write_variant_public_forward_live_sim_summary(output_root=local_project)
    evidence = write_thousand_strategy_public_forward_evidence_report(output_root=local_project)

    assert summary["selected_strategy_id"] == candidate_id
    assert summary["status"] == "VARIANT_PUBLIC_FORWARD_LIVE_SIM_PENDING"
    assert summary["public_forward_evidence_proven"] is False
    assert summary["evidence_source"] == "public_forward_live_sim_pending"
    assert summary["live_trading_enabled"] is False
    assert summary["execution_authority"] == "NONE"
    assert "SELECTED_STRATEGY_ID_MISMATCH" not in evidence["blockers"]
    assert "FIXTURE_DATA_NOT_PUBLIC_FORWARD_EVIDENCE" not in evidence["blockers"]
    assert "PUBLIC_FORWARD_EVIDENCE_NOT_PROVEN" in evidence["blockers"]


def test_sequence64_candidate_public_forward_observations_accumulate_without_proof(
    local_project: Path,
) -> None:
    from quant_os.autonomy.variant_public_forward_live_sim import (
        append_variant_public_forward_observations,
    )
    from quant_os.research.strategy_factory.strategy_tournament import (
        write_strategy_tournament_report,
    )

    tournament = write_strategy_tournament_report(output_root=local_project, batch_index=1)
    candidate_id = tournament["current_best_candidate"]["id"]
    first = append_variant_public_forward_observations(
        output_root=local_project,
        observations=[
            {
                "asset": "BTC/USD",
                "bid": 100.0,
                "ask": 100.1,
                "source": "kraken_public_rest_unauthenticated_forward",
                "timestamp": "2026-05-18T10:00:00Z",
            }
        ],
    )
    second = append_variant_public_forward_observations(
        output_root=local_project,
        observations=[
            {
                "asset": "ETH/USD",
                "bid": 50.0,
                "ask": 50.1,
                "source": "kraken_public_rest_unauthenticated_forward",
                "timestamp": "2026-05-18T10:01:00Z",
            }
        ],
    )

    assert first["selected_strategy_id"] == candidate_id
    assert second["selected_strategy_id"] == candidate_id
    assert first["observation_count"] == 1
    assert second["observation_count"] == 2
    assert second["public_forward_evidence_proven"] is False
    assert second["status"] == "VARIANT_PUBLIC_FORWARD_LIVE_SIM_PENDING"
    assert second["data_sources"] == ["kraken_public_rest_unauthenticated_forward"]
    assert second["actual_order_count"] == 0
    assert second["actual_cancel_count"] == 0


def test_sequence64_candidate_public_forward_snapshot_appends_selected_assets_only(
    local_project: Path,
) -> None:
    from quant_os.autonomy.variant_public_forward_live_sim import (
        append_variant_public_forward_snapshot,
    )
    from quant_os.research.strategy_factory.strategy_tournament import (
        write_strategy_tournament_report,
    )

    tournament = write_strategy_tournament_report(output_root=local_project, batch_index=1)
    candidate = tournament["current_best_candidate"]
    assert candidate["assets"] == ["BTC/USD", "ETH/USD"]

    summary = append_variant_public_forward_snapshot(
        output_root=local_project,
        public_snapshot={
            "source": "kraken_public_rest_unauthenticated_forward",
            "fetched_at": "2026-05-18T11:00:00Z",
            "symbols": {
                "BTC/USD": {"book": {"bid": 100.0, "ask": 100.1}},
                "ETH/USD": {"book": {"bid": 50.0, "ask": 50.1}},
                "SOL/USD": {"book": {"bid": 20.0, "ask": 20.1}},
            },
        },
    )

    assert summary["selected_strategy_id"] == candidate["id"]
    assert summary["observation_count"] == 2
    assert {row["asset"] for row in summary["public_forward_observations"]} == {
        "BTC/USD",
        "ETH/USD",
    }
    assert summary["data_sources"] == ["kraken_public_rest_unauthenticated_forward"]
    assert summary["public_forward_evidence_proven"] is False
    assert summary["actual_order_count"] == 0
    assert summary["actual_cancel_count"] == 0


def test_sequence64_public_forward_snapshot_evicts_pending_fixture_placeholder(
    local_project: Path,
) -> None:
    from quant_os.autonomy.variant_public_forward_live_sim import (
        append_variant_public_forward_observations,
        append_variant_public_forward_snapshot,
    )
    from quant_os.research.strategy_factory.strategy_tournament import (
        write_strategy_tournament_report,
    )

    write_strategy_tournament_report(output_root=local_project, batch_index=1)
    append_variant_public_forward_observations(
        output_root=local_project,
        observations=[
            {
                "asset": "BTC/USD",
                "bid": 0.0,
                "ask": 0.0,
                "source": "kraken_public_rest_unauthenticated_forward_pending",
                "timestamp": "pending",
            }
        ],
    )

    summary = append_variant_public_forward_snapshot(
        output_root=local_project,
        public_snapshot={
            "source": "kraken_public_rest_unauthenticated_forward",
            "fetched_at": "2026-05-18T11:00:00Z",
            "symbols": {
                "BTC/USD": {"book": {"bid": 100.0, "ask": 100.1}},
                "ETH/USD": {"book": {"bid": 50.0, "ask": 50.1}},
            },
        },
    )

    assert summary["observation_count"] == 2
    assert summary["data_sources"] == ["kraken_public_rest_unauthenticated_forward"]
    assert all(
        row["source"] == "kraken_public_rest_unauthenticated_forward"
        for row in summary["public_forward_observations"]
    )
    assert all(row["timestamp"] != "pending" for row in summary["public_forward_observations"])
    assert summary["actual_order_count"] == 0
    assert summary["actual_cancel_count"] == 0


def test_sequence64_candidate_public_forward_fetch_defaults_to_no_network(
    local_project: Path,
) -> None:
    from quant_os.autonomy.variant_public_forward_live_sim import (
        append_variant_public_forward_public_snapshot,
    )
    from quant_os.research.strategy_factory.strategy_tournament import (
        write_strategy_tournament_report,
    )

    write_strategy_tournament_report(output_root=local_project, batch_index=1)

    summary = append_variant_public_forward_public_snapshot(
        output_root=local_project,
        public_network_ok=False,
    )

    assert summary["observation_count"] == 0
    assert summary["public_forward_evidence_proven"] is False
    assert "PUBLIC_NETWORK_NOT_ENABLED" in summary["collection_blockers"]
    assert summary["authenticated_requests_enabled"] is False
    assert summary["request_signing_enabled"] is False


def test_sequence64_candidate_public_forward_fetch_appends_public_snapshot_when_enabled(
    local_project: Path,
) -> None:
    from quant_os.autonomy.variant_public_forward_live_sim import (
        append_variant_public_forward_public_snapshot,
    )
    from quant_os.research.strategy_factory.strategy_tournament import (
        write_strategy_tournament_report,
    )

    write_strategy_tournament_report(output_root=local_project, batch_index=1)

    summary = append_variant_public_forward_public_snapshot(
        output_root=local_project,
        public_network_ok=True,
        public_snapshot={
            "source": "kraken_public_rest_unauthenticated_forward",
            "fetched_at": "2026-05-18T11:00:00Z",
            "symbols": {
                "BTC/USD": {"book": {"bid": 100.0, "ask": 100.1}},
                "ETH/USD": {"book": {"bid": 50.0, "ask": 50.1}},
            },
        },
    )

    assert summary["observation_count"] == 2
    assert summary["data_sources"] == ["kraken_public_rest_unauthenticated_forward"]
    assert summary["collection_blockers"] == []
    assert summary["api_keys_loaded"] is False
    assert summary["private_keys_loaded"] is False


def test_sequence64_candidate_public_forward_intents_are_candidate_matched_no_transmit(
    local_project: Path,
) -> None:
    from quant_os.autonomy.variant_public_forward_live_sim import (
        append_variant_public_forward_observations,
        write_variant_public_forward_intents_report,
    )

    candidate = {
        "id": "tsv_candidate_matched_signal",
        "family": "crypto_public_data_quality_filtered_momentum",
        "assets": ["BTC/USD", "ETH/USD"],
        "variant_configuration": {"thresholds": {"no_trade_edge_bps": 1.0}},
    }
    append_variant_public_forward_observations(
        output_root=local_project,
        observations=[
            {
                "asset": "BTC/USD",
                "bid": 100.0,
                "ask": 100.1,
                "source": "kraken_public_rest_unauthenticated_forward",
                "timestamp": "2026-05-18T12:00:00Z",
            },
            {
                "asset": "BTC/USD",
                "bid": 100.5,
                "ask": 100.6,
                "source": "kraken_public_rest_unauthenticated_forward",
                "timestamp": "2026-05-18T12:01:00Z",
            },
            {
                "asset": "ETH/USD",
                "bid": 50.0,
                "ask": 50.1,
                "source": "kraken_public_rest_unauthenticated_forward",
                "timestamp": "2026-05-18T12:00:00Z",
            },
            {
                "asset": "ETH/USD",
                "bid": 50.4,
                "ask": 50.5,
                "source": "kraken_public_rest_unauthenticated_forward",
                "timestamp": "2026-05-18T12:01:00Z",
            },
        ],
    )

    intents = write_variant_public_forward_intents_report(
        output_root=local_project,
        candidate=candidate,
    )
    summary = json.loads(
        (
            local_project
            / "reports/thousand_strategy_campaign/live_sim/latest_live_sim_summary.json"
        ).read_text(encoding="utf-8")
    )

    assert intents["status"] == "VARIANT_PUBLIC_FORWARD_INTENTS_READY"
    assert intents["selected_strategy_id"] == candidate["id"]
    assert intents["eligible_intent_count"] == 2
    assert summary["eligible_intent_count"] == 2
    assert summary["public_forward_evidence_proven"] is False
    assert summary["evidence_source"] == "public_forward_live_sim_pending"
    assert all(intent["variant_id"] == candidate["id"] for intent in intents["intents"])
    assert all(intent["candidate_signal_model"] == "public_forward_no_lookahead_mid_change" for intent in intents["intents"])
    assert all(intent["uses_lookahead"] is False for intent in intents["intents"])
    assert all(intent["fake_money"] is True for intent in intents["intents"])
    assert all(intent["no_transmit"] is True for intent in intents["intents"])
    assert all("signed_headers" not in intent for intent in intents["intents"])
    assert all(intent["contains_signed_headers"] is False for intent in intents["intents"])
    assert all("order" not in intent["endpoint"].lower() for intent in intents["intents"])
    assert intents["order_transmission_enabled"] is False
    assert intents["authenticated_requests_enabled"] is False
    assert intents["request_signing_enabled"] is False
    assert intents["actual_order_count"] == 0
    assert intents["actual_cancel_count"] == 0


def test_sequence64_public_forward_intents_use_candidate_signal_not_row_parity(
    local_project: Path,
) -> None:
    from quant_os.autonomy.variant_public_forward_live_sim import (
        append_variant_public_forward_observations,
        write_variant_public_forward_intents_report,
    )

    candidate = {
        "id": "tsv_signal_aware_momentum",
        "family": "crypto_public_data_quality_filtered_momentum",
        "assets": ["BTC/USD"],
        "variant_configuration": {
            "thresholds": {
                "no_trade_edge_bps": 1.0,
            }
        },
    }
    append_variant_public_forward_observations(
        output_root=local_project,
        observations=[
            {
                "asset": "BTC/USD",
                "bid": 100.00,
                "ask": 100.10,
                "source": "kraken_public_rest_unauthenticated_forward",
                "timestamp": "2026-05-20T12:00:00Z",
            },
            {
                "asset": "BTC/USD",
                "bid": 100.50,
                "ask": 100.60,
                "source": "kraken_public_rest_unauthenticated_forward",
                "timestamp": "2026-05-20T12:01:00Z",
            },
            {
                "asset": "BTC/USD",
                "bid": 101.00,
                "ask": 101.10,
                "source": "kraken_public_rest_unauthenticated_forward",
                "timestamp": "2026-05-20T12:02:00Z",
            },
        ],
    )

    intents = write_variant_public_forward_intents_report(
        output_root=local_project,
        candidate=candidate,
    )

    assert intents["eligible_intent_count"] == 2
    assert [intent["side"] for intent in intents["intents"]] == ["buy", "buy"]
    assert all(intent["candidate_signal_model"] == "public_forward_no_lookahead_mid_change" for intent in intents["intents"])
    assert all(intent["uses_lookahead"] is False for intent in intents["intents"])
    assert all(intent["signal_change_bps"] > 0 for intent in intents["intents"])
    assert all(intent["signal_direction"] == "momentum_up" for intent in intents["intents"])
    assert all(intent["fake_money"] is True for intent in intents["intents"])
    assert all(intent["no_transmit"] is True for intent in intents["intents"])
    assert all("order" not in intent["endpoint"].lower() for intent in intents["intents"])


def test_sequence64_public_forward_intents_veto_signals_below_execution_uncertainty(
    local_project: Path,
) -> None:
    from quant_os.autonomy.variant_public_forward_live_sim import (
        append_variant_public_forward_observations,
        write_variant_public_forward_intents_report,
    )

    candidate = {
        "id": "tsv_execution_uncertainty_veto",
        "family": "crypto_public_data_quality_filtered_momentum",
        "assets": ["BTC/USD"],
        "variant_configuration": {
            "thresholds": {
                "no_trade_edge_bps": 1.0,
            }
        },
    }
    append_variant_public_forward_observations(
        output_root=local_project,
        observations=[
            {
                "asset": "BTC/USD",
                "bid": 100.00,
                "ask": 100.10,
                "source": "kraken_public_rest_unauthenticated_forward",
                "timestamp": "2026-05-20T13:00:00Z",
            },
            {
                "asset": "BTC/USD",
                "bid": 100.05,
                "ask": 100.15,
                "source": "kraken_public_rest_unauthenticated_forward",
                "timestamp": "2026-05-20T13:01:00Z",
            },
            {
                "asset": "BTC/USD",
                "bid": 100.35,
                "ask": 100.45,
                "source": "kraken_public_rest_unauthenticated_forward",
                "timestamp": "2026-05-20T13:02:00Z",
            },
        ],
    )

    intents = write_variant_public_forward_intents_report(
        output_root=local_project,
        candidate=candidate,
    )

    assert intents["eligible_intent_count"] == 1
    intent = intents["intents"][0]
    assert intent["timestamp"] == "2026-05-20T13:02:00Z"
    assert intent["signal_change_bps"] > intent["execution_uncertainty_bps"]
    assert intent["signal_threshold_bps"] == intent["execution_uncertainty_bps"]
    assert intent["execution_uncertainty_reason"] == "fee_spread_slippage_and_observed_spread"


def test_sequence64_public_forward_intents_use_candidate_lookback_not_only_last_tick(
    local_project: Path,
) -> None:
    from quant_os.autonomy.variant_public_forward_live_sim import (
        append_variant_public_forward_observations,
        write_variant_public_forward_intents_report,
    )

    candidate = {
        "id": "tsv_lookback_signal",
        "family": "crypto_public_data_quality_filtered_momentum",
        "assets": ["BTC/USD"],
        "variant_configuration": {
            "lookback": 3,
            "thresholds": {
                "no_trade_edge_bps": 1.0,
            },
        },
    }
    append_variant_public_forward_observations(
        output_root=local_project,
        observations=[
            {
                "asset": "BTC/USD",
                "bid": 100.00,
                "ask": 100.10,
                "source": "kraken_public_rest_unauthenticated_forward",
                "timestamp": "2026-05-20T13:10:00Z",
            },
            {
                "asset": "BTC/USD",
                "bid": 100.10,
                "ask": 100.20,
                "source": "kraken_public_rest_unauthenticated_forward",
                "timestamp": "2026-05-20T13:11:00Z",
            },
            {
                "asset": "BTC/USD",
                "bid": 100.20,
                "ask": 100.30,
                "source": "kraken_public_rest_unauthenticated_forward",
                "timestamp": "2026-05-20T13:12:00Z",
            },
            {
                "asset": "BTC/USD",
                "bid": 100.35,
                "ask": 100.45,
                "source": "kraken_public_rest_unauthenticated_forward",
                "timestamp": "2026-05-20T13:13:00Z",
            },
        ],
    )

    intents = write_variant_public_forward_intents_report(
        output_root=local_project,
        candidate=candidate,
    )

    assert intents["eligible_intent_count"] == 1
    intent = intents["intents"][0]
    assert intent["timestamp"] == "2026-05-20T13:13:00Z"
    assert intent["side"] == "buy"
    assert intent["signal_lookback_observations"] == 3
    assert intent["signal_change_bps"] > intent["execution_uncertainty_bps"]


def test_sequence64_candidate_public_forward_fills_and_marks_use_later_observations_only(
    local_project: Path,
) -> None:
    from quant_os.autonomy.variant_public_forward_live_sim import (
        append_variant_public_forward_observations,
        write_variant_public_forward_fills_and_marks_report,
        write_variant_public_forward_intents_report,
    )
    from quant_os.proving.thousand_strategy_public_forward_evidence import (
        write_thousand_strategy_public_forward_evidence_report,
    )

    candidate = {
        "id": "tsv_future_mark_signal",
        "family": "crypto_public_data_quality_filtered_momentum",
        "assets": ["BTC/USD", "ETH/USD"],
        "variant_configuration": {"thresholds": {"no_trade_edge_bps": 1.0}},
    }
    append_variant_public_forward_observations(
        output_root=local_project,
        observations=[
            {
                "asset": "BTC/USD",
                "bid": 100.0,
                "ask": 100.1,
                "source": "kraken_public_rest_unauthenticated_forward",
                "timestamp": "2026-05-19T12:00:00Z",
            },
            {
                "asset": "ETH/USD",
                "bid": 50.0,
                "ask": 50.1,
                "source": "kraken_public_rest_unauthenticated_forward",
                "timestamp": "2026-05-19T12:00:00Z",
            },
            {
                "asset": "BTC/USD",
                "bid": 100.5,
                "ask": 100.6,
                "source": "kraken_public_rest_unauthenticated_forward",
                "timestamp": "2026-05-19T12:05:00Z",
            },
            {
                "asset": "ETH/USD",
                "bid": 49.5,
                "ask": 49.6,
                "source": "kraken_public_rest_unauthenticated_forward",
                "timestamp": "2026-05-19T12:05:00Z",
            },
            {
                "asset": "BTC/USD",
                "bid": 101.0,
                "ask": 101.1,
                "source": "kraken_public_rest_unauthenticated_forward",
                "timestamp": "2026-05-19T12:10:00Z",
            },
            {
                "asset": "ETH/USD",
                "bid": 49.0,
                "ask": 49.1,
                "source": "kraken_public_rest_unauthenticated_forward",
                "timestamp": "2026-05-19T12:10:00Z",
            },
        ],
    )
    write_variant_public_forward_intents_report(output_root=local_project, candidate=candidate)

    fills_marks = write_variant_public_forward_fills_and_marks_report(
        output_root=local_project,
        candidate=candidate,
    )
    evidence = write_thousand_strategy_public_forward_evidence_report(output_root=local_project)
    summary = json.loads(
        (
            local_project
            / "reports/thousand_strategy_campaign/live_sim/latest_live_sim_summary.json"
        ).read_text(encoding="utf-8")
    )

    assert fills_marks["status"] == "VARIANT_PUBLIC_FORWARD_FILLS_AND_MARKS_READY"
    assert fills_marks["selected_strategy_id"] == candidate["id"]
    assert fills_marks["fake_fill_count"] == 2
    assert fills_marks["completed_mark_count"] == 2
    assert summary["fake_fill_count"] == 2
    assert summary["completed_mark_count"] == 2
    assert summary["fake_net_pnl"] == fills_marks["fake_net_pnl"]
    assert summary["public_forward_evidence_proven"] is False
    assert all(row["fake_money"] is True for row in fills_marks["fake_fills"])
    assert all(row["no_transmit"] is True for row in fills_marks["fake_fills"])
    assert all(row["guaranteed_fill"] is False for row in fills_marks["fake_fills"])
    assert all(row["mark_timestamp"] > row["entry_timestamp"] for row in fills_marks["mark_rows"])
    assert all(row["mark_source"] == "future_public_observation" for row in fills_marks["mark_rows"])
    assert fills_marks["lookahead_detected"] is False
    assert fills_marks["order_transmission_enabled"] is False
    assert fills_marks["request_signing_enabled"] is False
    assert evidence["status"] == "PUBLIC_FORWARD_EVIDENCE_BLOCKED"
    assert "PUBLIC_FORWARD_EVIDENCE_NOT_PROVEN" in evidence["blockers"]


def test_sequence64_public_forward_collection_cycle_preserves_and_extends_observations(
    local_project: Path,
) -> None:
    from quant_os.autonomy.variant_public_forward_live_sim import (
        append_variant_public_forward_observations,
        write_variant_public_forward_collection_cycle,
    )
    from quant_os.research.strategy_factory.strategy_tournament import (
        write_strategy_tournament_report,
    )

    tournament = write_strategy_tournament_report(output_root=local_project, batch_index=1)
    candidate = tournament["current_best_candidate"]
    append_variant_public_forward_observations(
        output_root=local_project,
        observations=[
            {
                "asset": "BTC/USD",
                "bid": 100.0,
                "ask": 100.1,
                "source": "kraken_public_rest_unauthenticated_forward",
                "timestamp": "2026-05-19T13:00:00Z",
            },
            {
                "asset": "ETH/USD",
                "bid": 50.0,
                "ask": 50.1,
                "source": "kraken_public_rest_unauthenticated_forward",
                "timestamp": "2026-05-19T13:00:00Z",
            },
        ],
    )

    cycle = write_variant_public_forward_collection_cycle(
        output_root=local_project,
        public_network_ok=True,
        public_snapshot={
            "source": "kraken_public_rest_unauthenticated_forward",
            "fetched_at": "2026-05-19T13:05:00Z",
            "symbols": {
                "BTC/USD": {"book": {"bid": 100.2, "ask": 100.3}},
                "ETH/USD": {"book": {"bid": 49.8, "ask": 49.9}},
                "SOL/USD": {"book": {"bid": 20.0, "ask": 20.1}},
            },
        },
    )
    summary = json.loads(
        (
            local_project
            / "reports/thousand_strategy_campaign/live_sim/latest_live_sim_summary.json"
        ).read_text(encoding="utf-8")
    )

    assert cycle["status"] == "VARIANT_PUBLIC_FORWARD_COLLECTION_CYCLE_CHECKPOINTED"
    assert cycle["selected_strategy_id"] == candidate["id"]
    assert cycle["observation_count"] == 4
    assert cycle["eligible_intent_count"] == 0
    assert cycle["fake_fill_count"] == 0
    assert cycle["completed_mark_count"] == 0
    assert cycle["public_forward_evidence_status"] == "PUBLIC_FORWARD_EVIDENCE_BLOCKED"
    assert cycle["public_forward_evidence_proven"] is False
    assert cycle["collection_blockers"] == []
    assert summary["observation_count"] == 4
    assert summary["fake_fill_count"] == 0
    assert summary["completed_mark_count"] == 0
    assert {row["asset"] for row in summary["public_forward_observations"]} == {
        "BTC/USD",
        "ETH/USD",
    }
    assert cycle["order_transmission_enabled"] is False
    assert cycle["authenticated_requests_enabled"] is False
    assert cycle["request_signing_enabled"] is False


def test_sequence64_public_forward_batch_cycle_runs_bounded_append_only_cycles(
    local_project: Path,
) -> None:
    from quant_os.autonomy.variant_public_forward_live_sim import (
        append_variant_public_forward_observations,
        write_variant_public_forward_batch_cycle,
    )
    from quant_os.research.strategy_factory.strategy_tournament import (
        write_strategy_tournament_report,
    )

    tournament = write_strategy_tournament_report(output_root=local_project, batch_index=1)
    candidate = tournament["current_best_candidate"]
    append_variant_public_forward_observations(
        output_root=local_project,
        observations=[
            {
                "asset": "BTC/USD",
                "bid": 100.0,
                "ask": 100.1,
                "source": "kraken_public_rest_unauthenticated_forward",
                "timestamp": "2026-05-19T14:00:00Z",
            },
            {
                "asset": "ETH/USD",
                "bid": 50.0,
                "ask": 50.1,
                "source": "kraken_public_rest_unauthenticated_forward",
                "timestamp": "2026-05-19T14:00:00Z",
            },
        ],
    )

    batch = write_variant_public_forward_batch_cycle(
        output_root=local_project,
        public_network_ok=True,
        public_snapshots=[
            {
                "source": "kraken_public_rest_unauthenticated_forward",
                "fetched_at": "2026-05-19T14:05:00Z",
                "symbols": {
                    "BTC/USD": {"book": {"bid": 100.2, "ask": 100.3}},
                    "ETH/USD": {"book": {"bid": 49.8, "ask": 49.9}},
                    "SOL/USD": {"book": {"bid": 20.0, "ask": 20.1}},
                },
            },
            {
                "source": "kraken_public_rest_unauthenticated_forward",
                "fetched_at": "2026-05-19T14:10:00Z",
                "symbols": {
                    "BTC/USD": {"book": {"bid": 100.4, "ask": 100.5}},
                    "ETH/USD": {"book": {"bid": 49.6, "ask": 49.7}},
                    "SOL/USD": {"book": {"bid": 20.2, "ask": 20.3}},
                },
            },
        ],
        cycle_count=2,
        sleep_seconds=0,
    )
    summary = json.loads(
        (
            local_project
            / "reports/thousand_strategy_campaign/live_sim/latest_live_sim_summary.json"
        ).read_text(encoding="utf-8")
    )

    assert batch["status"] == "VARIANT_PUBLIC_FORWARD_BATCH_CYCLE_CHECKPOINTED"
    assert batch["selected_strategy_id"] == candidate["id"]
    assert batch["cycle_count_requested"] == 2
    assert batch["cycle_count_completed"] == 2
    assert [row["observation_count"] for row in batch["cycle_summaries"]] == [4, 6]
    assert batch["observation_count"] == 6
    assert batch["eligible_intent_count"] == 0
    assert batch["fake_fill_count"] == 0
    assert batch["completed_mark_count"] == 0
    assert batch["public_forward_evidence_status"] == "PUBLIC_FORWARD_EVIDENCE_BLOCKED"
    assert batch["public_forward_evidence_proven"] is False
    assert summary["observation_count"] == 6
    assert summary["fake_fill_count"] == 0
    assert summary["completed_mark_count"] == 0
    assert {row["asset"] for row in summary["public_forward_observations"]} == {
        "BTC/USD",
        "ETH/USD",
    }
    assert batch["order_transmission_enabled"] is False
    assert batch["authenticated_requests_enabled"] is False
    assert batch["request_signing_enabled"] is False


def test_sequence64_public_forward_batch_uses_rotated_collectable_candidate(
    local_project: Path,
) -> None:
    from quant_os.autonomy.variant_public_forward_live_sim import (
        write_variant_public_forward_batch_cycle,
        write_variant_public_forward_live_sim_summary,
    )
    from quant_os.research.strategy_factory.campaign_common import write_json_md

    weather_candidate = {
        "id": "tsv_weather_not_collectable",
        "family": "temperature_tail_mispricing",
        "assets": ["KXHIGHNY", "KXHIGHLAX"],
    }
    crypto_candidate = {
        "id": "tsv_crypto_collectable",
        "family": "crypto_public_data_quality_filtered_momentum",
        "assets": ["BTC/USD", "ETH/USD"],
    }
    write_json_md(
        {
            "status": "THOUSAND_STRATEGY_CAMPAIGN_CHECKPOINTED_NOT_COMPLETE",
            "current_best_candidate": weather_candidate,
            "cumulative_leaderboard_top_50": [weather_candidate, crypto_candidate],
        },
        output_root=local_project,
        report_dir="tournament",
        json_name="latest_tournament.json",
        md_name="latest_tournament.md",
        title="Tournament",
        lines=["fixture"],
    )
    write_variant_public_forward_live_sim_summary(
        output_root=local_project,
        candidate=crypto_candidate,
    )

    batch = write_variant_public_forward_batch_cycle(
        output_root=local_project,
        public_network_ok=True,
        public_snapshots=[
            {
                "source": "kraken_public_rest_unauthenticated_forward",
                "fetched_at": "2026-05-19T14:05:00Z",
                "symbols": {
                    "BTC/USD": {"book": {"bid": 100.2, "ask": 100.3}},
                    "ETH/USD": {"book": {"bid": 49.8, "ask": 49.9}},
                },
            }
        ],
        cycle_count=1,
        sleep_seconds=0,
    )

    assert batch["selected_strategy_id"] == crypto_candidate["id"]
    assert batch["observation_count"] == 2
    assert batch["collection_blockers"] == []


def test_sequence64_public_forward_candidate_archive_separates_rotated_candidates(
    local_project: Path,
) -> None:
    from quant_os.autonomy.variant_public_forward_live_sim import (
        append_variant_public_forward_observations,
        write_variant_public_forward_candidate_archive,
        write_variant_public_forward_collection_cycle,
        write_variant_public_forward_live_sim_summary,
    )
    from quant_os.research.strategy_factory.strategy_tournament import (
        write_strategy_tournament_report,
    )

    tournament = write_strategy_tournament_report(output_root=local_project, batch_index=1)
    first_candidate = tournament["current_best_candidate"]
    append_variant_public_forward_observations(
        output_root=local_project,
        observations=[
            {
                "asset": "BTC/USD",
                "bid": 100.0,
                "ask": 100.1,
                "source": "kraken_public_rest_unauthenticated_forward",
                "timestamp": "2026-05-19T15:00:00Z",
            },
            {
                "asset": "BTC/USD",
                "bid": 100.2,
                "ask": 100.3,
                "source": "kraken_public_rest_unauthenticated_forward",
                "timestamp": "2026-05-19T15:05:00Z",
            },
        ],
    )
    write_variant_public_forward_collection_cycle(
        output_root=local_project,
        public_network_ok=True,
        public_snapshot={
            "source": "kraken_public_rest_unauthenticated_forward",
            "fetched_at": "2026-05-19T15:10:00Z",
            "symbols": {
                "BTC/USD": {"book": {"bid": 100.4, "ask": 100.5}},
                "ETH/USD": {"book": {"bid": 50.0, "ask": 50.1}},
            },
        },
    )
    first_archive = write_variant_public_forward_candidate_archive(output_root=local_project)

    second_candidate = {
        "id": "tsv_rotated_candidate",
        "family": "cross_asset_lead_lag",
        "assets": ["SOL/USD"],
    }
    write_variant_public_forward_live_sim_summary(
        output_root=local_project,
        candidate=second_candidate,
    )
    second_archive = write_variant_public_forward_candidate_archive(output_root=local_project)

    assert first_archive["status"] == "VARIANT_PUBLIC_FORWARD_CANDIDATE_ARCHIVE_READY"
    assert second_archive["status"] == "VARIANT_PUBLIC_FORWARD_CANDIDATE_ARCHIVE_READY"
    assert first_candidate["id"] in second_archive["candidate_evidence"]
    assert "tsv_rotated_candidate" in second_archive["candidate_evidence"]
    assert second_archive["candidate_evidence"][first_candidate["id"]]["observation_count"] == 4
    assert second_archive["candidate_evidence"][first_candidate["id"]]["fake_fill_count"] == 0
    assert second_archive["candidate_evidence"]["tsv_rotated_candidate"]["observation_count"] == 0
    assert second_archive["candidate_evidence"]["tsv_rotated_candidate"]["fake_fill_count"] == 0
    assert second_archive["candidate_evidence"][first_candidate["id"]]["selected_strategy_assets"] == [
        "BTC/USD",
        "ETH/USD",
    ]
    assert second_archive["candidate_evidence"]["tsv_rotated_candidate"][
        "selected_strategy_assets"
    ] == ["SOL/USD"]
    assert second_archive["public_forward_evidence_proven"] is False
    assert second_archive["order_transmission_enabled"] is False
    assert second_archive["authenticated_requests_enabled"] is False
    assert second_archive["request_signing_enabled"] is False


def test_sequence64_public_forward_rotation_retires_negative_pnl_candidate(
    local_project: Path,
) -> None:
    from quant_os.autonomy.variant_public_forward_live_sim import (
        write_variant_public_forward_candidate_rotation,
    )
    from quant_os.research.strategy_factory.strategy_tournament import (
        write_strategy_tournament_report,
    )

    tournament = write_strategy_tournament_report(output_root=local_project, batch_index=1)
    first_candidate = tournament["current_best_candidate"]
    live_sim_dir = local_project / "reports/thousand_strategy_campaign/live_sim"
    live_sim_dir.mkdir(parents=True, exist_ok=True)
    (live_sim_dir / "latest_live_sim_summary.json").write_text(
        json.dumps(
            {
                "status": "VARIANT_PUBLIC_FORWARD_LIVE_SIM_PENDING",
                "selected_strategy_id": first_candidate["id"],
                "selected_strategy_family": first_candidate["family"],
                "selected_strategy_assets": first_candidate["assets"],
                "observation_count": 540,
                "eligible_intent_count": 540,
                "fake_fill_count": 538,
                "completed_mark_count": 538,
                "fake_net_pnl": -1.09,
                "data_sources": ["kraken_public_rest_unauthenticated_forward"],
                "public_forward_evidence_proven": False,
                "live_trading_enabled": False,
                "execution_authority": "NONE",
                "order_transmission_enabled": False,
                "authenticated_requests_enabled": False,
                "request_signing_enabled": False,
                "api_keys_loaded": False,
                "private_keys_loaded": False,
                "actual_order_count": 0,
                "actual_cancel_count": 0,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    rotation = write_variant_public_forward_candidate_rotation(output_root=local_project)
    rotated_tournament = json.loads(
        (
            local_project / "reports/thousand_strategy_campaign/tournament/latest_tournament.json"
        ).read_text(encoding="utf-8")
    )
    rotated_summary = json.loads(
        (live_sim_dir / "latest_live_sim_summary.json").read_text(encoding="utf-8")
    )

    assert rotation["status"] == "VARIANT_PUBLIC_FORWARD_CANDIDATE_ROTATED"
    assert rotation["retired_candidate_id"] == first_candidate["id"]
    assert rotation["selected_strategy_id"] != first_candidate["id"]
    assert "PUBLIC_FORWARD_FAKE_NET_PNL_NEGATIVE" in rotation["retirement_reasons"]
    assert rotated_tournament["current_best_candidate"]["id"] == rotation["selected_strategy_id"]
    assert rotated_summary["selected_strategy_id"] == rotation["selected_strategy_id"]
    assert rotated_summary["observation_count"] == 0
    assert rotated_summary["actual_order_count"] == 0
    assert rotated_summary["actual_cancel_count"] == 0


def test_sequence64_public_forward_rotation_skips_uncollectable_candidates(
    local_project: Path,
) -> None:
    from quant_os.autonomy.variant_public_forward_live_sim import (
        write_variant_public_forward_candidate_rotation,
    )
    from quant_os.research.strategy_factory.strategy_tournament import (
        write_strategy_tournament_report,
    )

    tournament = write_strategy_tournament_report(output_root=local_project, batch_index=1)
    first_candidate = tournament["current_best_candidate"]
    weather_candidate = {
        "id": "tsv_weather_uncollectable",
        "family": "temperature_tail_mispricing",
        "assets": ["KXHIGHNY"],
        "fake_net_pnl": 99.0,
        "baseline_beaten": True,
        "placebo_beaten": True,
        "score": 9.0,
    }
    crypto_candidate = {
        "id": "tsv_crypto_collectable",
        "family": "range_breakout_cost_filtered",
        "assets": ["BTC/USD", "ETH/USD"],
        "fake_net_pnl": 20.0,
        "baseline_beaten": True,
        "placebo_beaten": True,
        "score": 2.0,
    }
    tournament["cumulative_leaderboard_top_50"] = [
        first_candidate,
        weather_candidate,
        crypto_candidate,
    ]
    tournament_path = (
        local_project / "reports/thousand_strategy_campaign/tournament/latest_tournament.json"
    )
    tournament_path.write_text(json.dumps(tournament, indent=2, sort_keys=True), encoding="utf-8")
    live_sim_dir = local_project / "reports/thousand_strategy_campaign/live_sim"
    live_sim_dir.mkdir(parents=True, exist_ok=True)
    (live_sim_dir / "latest_live_sim_summary.json").write_text(
        json.dumps(
            {
                "selected_strategy_id": first_candidate["id"],
                "selected_strategy_family": first_candidate["family"],
                "selected_strategy_assets": first_candidate["assets"],
                "completed_mark_count": 10,
                "fake_net_pnl": -0.1,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    rotation = write_variant_public_forward_candidate_rotation(output_root=local_project)

    assert rotation["status"] == "VARIANT_PUBLIC_FORWARD_CANDIDATE_ROTATED"
    assert rotation["selected_strategy_id"] == "tsv_crypto_collectable"
    assert rotation["skipped_uncollectable_candidate_ids"] == ["tsv_weather_uncollectable"]


def test_sequence64_public_forward_rotation_skips_validation_only_crypto_candidates(
    local_project: Path,
) -> None:
    from quant_os.autonomy.variant_public_forward_live_sim import (
        write_variant_public_forward_candidate_rotation,
    )
    from quant_os.research.strategy_factory.strategy_tournament import (
        write_strategy_tournament_report,
    )

    tournament = write_strategy_tournament_report(output_root=local_project, batch_index=1)
    first_candidate = tournament["current_best_candidate"]
    validation_only_candidate = {
        "id": "tsv_validation_only",
        "family": "calibration_holdout_walk_forward_protocol",
        "assets": ["BTC/USD", "ETH/USD"],
        "fake_net_pnl": 50.0,
        "baseline_beaten": True,
        "placebo_beaten": True,
        "score": 9.0,
    }
    signal_candidate = {
        "id": "tsv_signal_collectable",
        "family": "crypto_public_data_quality_filtered_momentum",
        "assets": ["BTC/USD", "ETH/USD"],
        "fake_net_pnl": 20.0,
        "baseline_beaten": True,
        "placebo_beaten": True,
        "score": 2.0,
    }
    tournament["cumulative_leaderboard_top_50"] = [
        first_candidate,
        validation_only_candidate,
        signal_candidate,
    ]
    tournament_path = (
        local_project / "reports/thousand_strategy_campaign/tournament/latest_tournament.json"
    )
    tournament_path.write_text(json.dumps(tournament, indent=2, sort_keys=True), encoding="utf-8")
    live_sim_dir = local_project / "reports/thousand_strategy_campaign/live_sim"
    live_sim_dir.mkdir(parents=True, exist_ok=True)
    (live_sim_dir / "latest_live_sim_summary.json").write_text(
        json.dumps(
            {
                "selected_strategy_id": first_candidate["id"],
                "selected_strategy_family": first_candidate["family"],
                "selected_strategy_assets": first_candidate["assets"],
                "completed_mark_count": 10,
                "fake_net_pnl": -0.1,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    rotation = write_variant_public_forward_candidate_rotation(output_root=local_project)

    assert rotation["status"] == "VARIANT_PUBLIC_FORWARD_CANDIDATE_ROTATED"
    assert rotation["selected_strategy_id"] == "tsv_signal_collectable"
    assert "tsv_validation_only" in rotation["skipped_uncollectable_candidate_ids"]


def test_sequence64_public_forward_rotation_retires_zero_intent_candidate_after_min_observations(
    local_project: Path,
) -> None:
    from quant_os.autonomy.variant_public_forward_live_sim import (
        write_variant_public_forward_candidate_rotation,
    )
    from quant_os.research.strategy_factory.strategy_tournament import (
        write_strategy_tournament_report,
    )

    tournament = write_strategy_tournament_report(output_root=local_project, batch_index=1)
    first_candidate = tournament["current_best_candidate"]
    next_candidate = {
        "id": "tsv_next_signal_candidate",
        "family": "crypto_public_data_quality_filtered_momentum",
        "assets": ["BTC/USD", "ETH/USD"],
        "fake_net_pnl": 20.0,
        "baseline_beaten": True,
        "placebo_beaten": True,
        "score": 2.0,
    }
    tournament["cumulative_leaderboard_top_50"] = [first_candidate, next_candidate]
    tournament_path = (
        local_project / "reports/thousand_strategy_campaign/tournament/latest_tournament.json"
    )
    tournament_path.write_text(json.dumps(tournament, indent=2, sort_keys=True), encoding="utf-8")
    live_sim_dir = local_project / "reports/thousand_strategy_campaign/live_sim"
    live_sim_dir.mkdir(parents=True, exist_ok=True)
    (live_sim_dir / "latest_live_sim_summary.json").write_text(
        json.dumps(
            {
                "selected_strategy_id": first_candidate["id"],
                "selected_strategy_family": first_candidate["family"],
                "selected_strategy_assets": first_candidate["assets"],
                "observation_count": 120,
                "eligible_intent_count": 0,
                "completed_mark_count": 0,
                "fake_net_pnl": 0.0,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    rotation = write_variant_public_forward_candidate_rotation(output_root=local_project)

    assert rotation["status"] == "VARIANT_PUBLIC_FORWARD_CANDIDATE_ROTATED"
    assert rotation["retired_candidate_id"] == first_candidate["id"]
    assert rotation["selected_strategy_id"] == "tsv_next_signal_candidate"
    assert "PUBLIC_FORWARD_NO_SIGNAL_AFTER_MIN_OBSERVATIONS" in rotation["retirement_reasons"]


def test_sequence64_public_forward_rotation_retires_low_intent_rate_candidate(
    local_project: Path,
) -> None:
    from quant_os.autonomy.variant_public_forward_live_sim import (
        write_variant_public_forward_candidate_rotation,
    )
    from quant_os.research.strategy_factory.strategy_tournament import (
        write_strategy_tournament_report,
    )

    tournament = write_strategy_tournament_report(output_root=local_project, batch_index=1)
    first_candidate = tournament["current_best_candidate"]
    next_candidate = {
        "id": "tsv_next_frequent_signal_candidate",
        "family": "crypto_public_data_quality_filtered_momentum",
        "assets": ["BTC/USD", "ETH/USD"],
        "fake_net_pnl": 20.0,
        "baseline_beaten": True,
        "placebo_beaten": True,
        "score": 2.0,
    }
    tournament["cumulative_leaderboard_top_50"] = [first_candidate, next_candidate]
    tournament_path = (
        local_project / "reports/thousand_strategy_campaign/tournament/latest_tournament.json"
    )
    tournament_path.write_text(json.dumps(tournament, indent=2, sort_keys=True), encoding="utf-8")
    live_sim_dir = local_project / "reports/thousand_strategy_campaign/live_sim"
    live_sim_dir.mkdir(parents=True, exist_ok=True)
    (live_sim_dir / "latest_live_sim_summary.json").write_text(
        json.dumps(
            {
                "selected_strategy_id": first_candidate["id"],
                "selected_strategy_family": first_candidate["family"],
                "selected_strategy_assets": first_candidate["assets"],
                "observation_count": 160,
                "eligible_intent_count": 1,
                "completed_mark_count": 0,
                "fake_net_pnl": 0.0,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    rotation = write_variant_public_forward_candidate_rotation(output_root=local_project)

    assert rotation["status"] == "VARIANT_PUBLIC_FORWARD_CANDIDATE_ROTATED"
    assert rotation["retired_candidate_id"] == first_candidate["id"]
    assert rotation["selected_strategy_id"] == "tsv_next_frequent_signal_candidate"
    assert "PUBLIC_FORWARD_INTENT_RATE_TOO_LOW" in rotation["retirement_reasons"]


def test_sequence64_public_forward_rotation_retires_low_mark_completion_candidate(
    local_project: Path,
) -> None:
    from quant_os.autonomy.variant_public_forward_live_sim import (
        write_variant_public_forward_candidate_rotation,
    )
    from quant_os.research.strategy_factory.strategy_tournament import (
        write_strategy_tournament_report,
    )

    tournament = write_strategy_tournament_report(output_root=local_project, batch_index=1)
    first_candidate = tournament["current_best_candidate"]
    next_candidate = {
        "id": "tsv_next_marking_candidate",
        "family": "crypto_public_data_quality_filtered_momentum",
        "assets": ["BTC/USD", "ETH/USD"],
        "fake_net_pnl": 20.0,
        "baseline_beaten": True,
        "placebo_beaten": True,
        "score": 2.0,
    }
    tournament["cumulative_leaderboard_top_50"] = [first_candidate, next_candidate]
    tournament_path = (
        local_project / "reports/thousand_strategy_campaign/tournament/latest_tournament.json"
    )
    tournament_path.write_text(json.dumps(tournament, indent=2, sort_keys=True), encoding="utf-8")
    live_sim_dir = local_project / "reports/thousand_strategy_campaign/live_sim"
    live_sim_dir.mkdir(parents=True, exist_ok=True)
    (live_sim_dir / "latest_live_sim_summary.json").write_text(
        json.dumps(
            {
                "selected_strategy_id": first_candidate["id"],
                "selected_strategy_family": first_candidate["family"],
                "selected_strategy_assets": first_candidate["assets"],
                "observation_count": 180,
                "eligible_intent_count": 24,
                "completed_mark_count": 0,
                "fake_net_pnl": 0.0,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    rotation = write_variant_public_forward_candidate_rotation(output_root=local_project)

    assert rotation["status"] == "VARIANT_PUBLIC_FORWARD_CANDIDATE_ROTATED"
    assert rotation["retired_candidate_id"] == first_candidate["id"]
    assert rotation["selected_strategy_id"] == "tsv_next_marking_candidate"
    assert "PUBLIC_FORWARD_MARK_COMPLETION_RATE_TOO_LOW" in rotation["retirement_reasons"]


def test_sequence64_public_forward_proof_finalizer_blocks_until_strict_thresholds(
    local_project: Path,
) -> None:
    from quant_os.autonomy.variant_public_forward_live_sim import (
        append_variant_public_forward_observations,
        write_variant_public_forward_proof_finalizer,
    )
    from quant_os.proving.thousand_strategy_public_forward_evidence import (
        write_thousand_strategy_public_forward_evidence_report,
    )
    from quant_os.research.strategy_factory.strategy_tournament import (
        write_strategy_tournament_report,
    )

    write_strategy_tournament_report(output_root=local_project, batch_index=1)
    append_variant_public_forward_observations(
        output_root=local_project,
        observations=[
            {
                "asset": "BTC/USD",
                "bid": 100.0,
                "ask": 100.1,
                "source": "kraken_public_rest_unauthenticated_forward",
                "timestamp": "2026-05-19T16:00:00Z",
            }
        ],
    )

    finalizer = write_variant_public_forward_proof_finalizer(output_root=local_project)
    evidence = write_thousand_strategy_public_forward_evidence_report(output_root=local_project)
    summary = json.loads(
        (
            local_project
            / "reports/thousand_strategy_campaign/live_sim/latest_live_sim_summary.json"
        ).read_text(encoding="utf-8")
    )

    assert finalizer["status"] == "VARIANT_PUBLIC_FORWARD_PROOF_BLOCKED"
    assert "PUBLIC_FORWARD_OBSERVATION_COUNT_TOO_LOW" in finalizer["blockers"]
    assert "PUBLIC_FORWARD_FAKE_NET_PNL_NOT_POSITIVE" in finalizer["blockers"]
    assert summary["status"] == "VARIANT_PUBLIC_FORWARD_LIVE_SIM_PENDING"
    assert summary["public_forward_evidence_proven"] is False
    assert summary["evidence_source"] == "public_forward_live_sim_pending"
    assert evidence["status"] == "PUBLIC_FORWARD_EVIDENCE_BLOCKED"
    assert finalizer["order_transmission_enabled"] is False
    assert finalizer["authenticated_requests_enabled"] is False
    assert finalizer["request_signing_enabled"] is False


def test_sequence64_public_forward_proof_finalizer_can_make_strict_ready_summary(
    local_project: Path,
) -> None:
    from quant_os.autonomy.variant_public_forward_live_sim import (
        write_variant_public_forward_proof_finalizer,
    )
    from quant_os.proving.thousand_strategy_public_forward_evidence import (
        write_thousand_strategy_public_forward_evidence_report,
    )
    from quant_os.research.strategy_factory.strategy_tournament import (
        write_strategy_tournament_report,
    )

    tournament = write_strategy_tournament_report(output_root=local_project, batch_index=1)
    candidate = tournament["current_best_candidate"]
    live_sim_dir = local_project / "reports/thousand_strategy_campaign/live_sim"
    live_sim_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "status": "VARIANT_PUBLIC_FORWARD_LIVE_SIM_PENDING",
        "selected_strategy_id": candidate["id"],
        "selected_strategy_family": candidate["family"],
        "selected_strategy_assets": candidate["assets"],
        "observation_count": 1200,
        "eligible_intent_count": 400,
        "fake_fill_count": 250,
        "completed_mark_count": 220,
        "fake_net_pnl": 12.5,
        "data_sources": ["kraken_public_rest_unauthenticated_forward"],
        "evidence_source": "public_forward_live_sim_pending",
        "public_forward_evidence_proven": False,
        "public_forward_observations": [],
        "live_trading_enabled": False,
        "execution_authority": "NONE",
        "order_transmission_enabled": False,
        "authenticated_requests_enabled": False,
        "request_signing_enabled": False,
        "api_keys_loaded": False,
        "private_keys_loaded": False,
        "actual_order_count": 0,
        "actual_cancel_count": 0,
    }
    (live_sim_dir / "latest_live_sim_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (live_sim_dir / "latest_public_forward_fills_and_marks.json").write_text(
        json.dumps(
            {
                "status": "VARIANT_PUBLIC_FORWARD_FILLS_AND_MARKS_READY",
                "lookahead_detected": False,
                "fake_fill_count": 250,
                "completed_mark_count": 220,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    finalizer = write_variant_public_forward_proof_finalizer(output_root=local_project)
    evidence = write_thousand_strategy_public_forward_evidence_report(output_root=local_project)
    ready_summary = json.loads((live_sim_dir / "latest_live_sim_summary.json").read_text())
    reconciliation = json.loads((live_sim_dir / "latest_reconciliation.json").read_text())

    assert finalizer["status"] == "VARIANT_PUBLIC_FORWARD_PROOF_READY"
    assert finalizer["blockers"] == []
    assert ready_summary["status"] == "VARIANT_LIVE_SIM_SUMMARY_READY"
    assert ready_summary["evidence_source"] == "public_forward_live_sim"
    assert ready_summary["public_forward_evidence_proven"] is True
    assert reconciliation["status"] == "VARIANT_LIVE_SIM_RECONCILIATION_PASSED"
    assert evidence["status"] == "PUBLIC_FORWARD_EVIDENCE_PASSED"
    assert evidence["candidate_evidence"]["public_forward_evidence_proven"] is True
    assert finalizer["order_transmission_enabled"] is False
    assert finalizer["actual_order_count"] == 0
    assert finalizer["actual_cancel_count"] == 0


def test_sequence64_readiness_uses_public_forward_evidence_report_for_provenance(
    local_project: Path,
) -> None:
    from quant_os.readiness.money_worthy_strategy_readiness import SUCCESS
    from quant_os.readiness.money_worthy_strategy_readiness_report import (
        write_money_worthy_strategy_readiness_report,
    )
    from quant_os.readiness.thousand_strategy_fresh_repro import (
        write_thousand_strategy_fresh_repro_report,
    )
    from quant_os.research.strategy_factory.strategy_tournament import (
        write_strategy_tournament_report,
    )

    tournament = write_strategy_tournament_report(output_root=local_project, batch_index=1)
    candidate = tournament["current_best_candidate"]
    candidate.update(
        {
            "multiple_testing_adjusted": True,
            "holdout_passed": True,
            "purged_validation_passed": True,
            "neighbor_parameter_pass_rate": 0.72,
            "placebo_survives_similarly": False,
            "adjusted_performance_significant": True,
            "one_trade_dominance": 0.12,
            "one_window_dominance": 0.21,
            "one_asset_dominance": 0.3,
            "stress_tests": {
                "exclude_top_trade": "PASSED",
                "exclude_top_5_trades": "PASSED",
                "delayed_entry": "PASSED",
                "worse_fill": "PASSED",
                "higher_fee": "PASSED",
            },
        },
    )
    tournament["current_best_candidate"] = candidate
    tournament["cumulative_top_candidates"] = [candidate]
    tournament["cumulative_leaderboard_top_50"][0] = candidate
    tournament_path = (
        local_project
        / "reports/thousand_strategy_campaign/tournament/latest_tournament.json"
    )
    tournament_path.write_text(json.dumps(tournament, indent=2, sort_keys=True), encoding="utf-8")
    live_sim_dir = local_project / "reports/thousand_strategy_campaign/live_sim"
    live_sim_dir.mkdir(parents=True, exist_ok=True)
    (live_sim_dir / "latest_live_sim_summary.json").write_text(
        json.dumps(
            {
                "selected_strategy_id": candidate["id"],
                "status": "VARIANT_LIVE_SIM_SUMMARY_READY",
                "data_sources": ["kraken_public_rest_unauthenticated_forward"],
                "observation_count": 5000,
                "eligible_intent_count": 500,
                "completed_mark_count": 300,
                "fake_net_pnl": 10.0,
                "public_forward_evidence_proven": True,
                "evidence_source": "public_forward_live_sim",
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    (live_sim_dir / "latest_reconciliation.json").write_text(
        json.dumps(
            {"status": "VARIANT_LIVE_SIM_RECONCILIATION_PASSED"},
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    write_thousand_strategy_fresh_repro_report(
        output_root=local_project,
        proof_command_passed=True,
    )

    readiness = write_money_worthy_strategy_readiness_report(output_root=local_project)

    assert readiness["public_forward_evidence_status"] == "PUBLIC_FORWARD_EVIDENCE_PASSED"
    assert readiness["status"] == SUCCESS
    assert readiness["current_best_candidate"]["public_forward_evidence_proven"] is True


def test_sequence64_readiness_replaces_stale_candidate_blockers_after_fresh_repro_passes(
    local_project: Path,
) -> None:
    from quant_os.readiness.money_worthy_strategy_readiness_report import (
        write_money_worthy_strategy_readiness_report,
    )
    from quant_os.readiness.thousand_strategy_fresh_repro import (
        write_thousand_strategy_fresh_repro_report,
    )
    from quant_os.research.strategy_factory.strategy_tournament import (
        write_strategy_tournament_report,
    )

    write_strategy_tournament_report(output_root=local_project, batch_index=1)
    write_thousand_strategy_fresh_repro_report(
        output_root=local_project,
        proof_command_passed=True,
    )
    readiness = write_money_worthy_strategy_readiness_report(output_root=local_project)
    state = json.loads(
        (
            local_project / "reports/thousand_strategy_campaign/state/latest_state.json"
        ).read_text(encoding="utf-8")
    )

    assert readiness["fresh_repro_status"] == "FRESH_REPRO_PASSED"
    assert "FRESH_WORKTREE_REPRO_NOT_PASSED" not in readiness["blockers"]
    assert "FRESH_WORKTREE_REPRO_NOT_PASSED" not in readiness["current_best_candidate"]["blockers"]
    assert "FRESH_WORKTREE_REPRO_NOT_PASSED" not in state["current_best_candidate"]["blockers"]
    assert state["current_best_candidate"]["blockers"] == readiness["blockers"]


def test_sequence64_next_tranche_cli_and_make_target_are_data_only(local_project: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = {**os.environ, "PYTHONPATH": str(repo_root / "src")}
    commands = [
        [
            sys.executable,
            "-m",
            "quant_os.cli",
            "research",
            "generate-strategy-variants",
            "--batch-index",
            "2",
        ],
        [
            sys.executable,
            "-m",
            "quant_os.cli",
            "research",
            "strategy-tournament",
            "--batch-index",
            "2",
        ],
        [sys.executable, "-m", "quant_os.cli", "research", "strategy-next-tranche"],
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

    make_cmd = (repo_root / "make.cmd").read_text(encoding="utf-8")
    assert 'if "%TARGET%"=="thousand-strategy-next-tranche"' in make_cmd
    assert 'if "%TARGET%"=="sequence64-smoke"' in make_cmd


def test_sequence64_source_pack_intake_extracts_useful_repo_knowledge_without_proof(
    local_project: Path,
) -> None:
    from quant_os.research.strategy_factory.source_pack_intake import (
        write_source_pack_intake_report,
    )

    v4_zip = local_project / "v4_source_pack.zip"
    with zipfile.ZipFile(v4_zip, "w") as archive:
        archive.writestr(
            "github_repo_research/priority_repo_decisions.md",
            "\n".join(
                [
                    "# Priority Repo Decisions",
                    "### Polymarket/py-clob-client-v2",
                    "- URL: https://github.com/Polymarket/py-clob-client-v2",
                    "- Why: Direct prediction-market venue/data/replay relevance; keep as persistent reference, but do not promote to live execution.",
                    "- Use for: src/quant_os/research/prediction_markets/; src/quant_os/data/; src/quant_os/replay/",
                    "### warproxxx/poly_data",
                    "- URL: https://github.com/warproxxx/poly_data",
                    "- Why: Public Polymarket data pipeline; keep as persistent reference, but do not promote to live execution.",
                    "- Use for: src/quant_os/research/prediction_markets/; src/quant_os/data/; src/quant_os/replay/",
                    "## Archive / research-only repos",
                    "- `TopTrenDev/polymarket-kalshi-arbitrage-bot` - inspect only for data/replay/risk patterns.",
                ]
            ),
        )
        archive.writestr(
            "github_repo_research/repo_research_backlog.md",
            "\n".join(
                [
                    "# Repo-Derived Research Backlog",
                    "1. Add Polymarket read-only data lane design doc",
                    "- Source repos: `warproxxx/poly_data`, `Polymarket/py-clob-client-v2`, `PolyBench/PolyBench`",
                    "- Hypothesis: prediction-market research should start with market metadata, order-filled events, trades, and CLOB snapshots, not trading.",
                    "- Failure modes: stale snapshots, on-chain/feed mismatch, missing resolution labels.",
                    "2. Improve replay realism from external benchmarks",
                    "- Source repos: `evan-kolberg/prediction-market-backtesting`, `nautechsystems/nautilus_trader`, `PolyBench/PolyBench`",
                    "- Test: add stale book, adverse selection, partial-fill, spread, and latency scenarios.",
                ]
            ),
        )

    payload = write_source_pack_intake_report(
        output_root=local_project,
        primary_source_pack=v4_zip,
    )

    assert payload["status"] == "SOURCE_PACK_INTAKE_READY"
    assert payload["social_or_repo_claims_are_proof"] is False
    assert payload["proof_status_changed"] is False
    assert payload["money_worthy_readiness_status"] != "MONEY_WORTHY_CANARY_GRADE_PROFITABILITY_PROVEN"
    assert payload["accepted_idea_count"] >= 2
    assert any(idea["strategy_family"] == "prediction_market_read_only_clob_replay" for idea in payload["ideas"])
    assert any(idea["strategy_family"] == "replay_realism_veto_layer" for idea in payload["ideas"])
    assert any(idea["decision"] == "REJECT" for idea in payload["ideas"])
    assert any(
        lead["repo"] == "Polymarket/py-clob-client-v2"
        and lead["adoption_decision"] == "REFERENCE_READ_ONLY_FIRST"
        for lead in payload["priority_repo_leads"]
    )
    assert any(
        lead["repo"] == "warproxxx/poly_data"
        and lead["market_lane"] == "prediction_market_read_only_clob"
        for lead in payload["priority_repo_leads"]
    )
    assert any(
        lead["repo"] == "TopTrenDev/polymarket-kalshi-arbitrage-bot"
        and lead["adoption_decision"] == "ARCHIVE_FAILURE_MODES_ONLY"
        for lead in payload["priority_repo_leads"]
    )
    assert all(idea["accept_reject_defer_decision"] in {"ACCEPT", "REJECT", "DEFER"} for idea in payload["ideas"])
    assert payload["live_trading_enabled"] is False
    assert payload["request_signing_enabled"] is False


def test_sequence64_source_backed_tranche_plan_narrows_future_generation(
    local_project: Path,
) -> None:
    from quant_os.research.strategy_factory.source_backed_tranche_plan import (
        write_source_backed_tranche_plan_report,
    )
    from quant_os.research.strategy_factory.source_pack_intake import (
        write_source_pack_intake_report,
    )

    v4_zip = local_project / "v4_source_pack.zip"
    with zipfile.ZipFile(v4_zip, "w") as archive:
        archive.writestr(
            "github_repo_research/priority_repo_decisions.md",
            "Polymarket/py-clob-client-v2\nwarproxxx/poly_data\n"
            "binance/binance-public-data\nccxt/ccxt\nfreqtrade/freq\n"
            "TopTrenDev/polymarket-kalshi-arbitrage-bot copy trade wallet mirror\n",
        )
        archive.writestr(
            "github_repo_research/repo_research_backlog.md",
            "Add Polymarket read-only data lane design doc\n"
            "Improve replay realism from external benchmarks\n"
            "Keep crypto-first data tooling practical\n",
        )
    write_source_pack_intake_report(output_root=local_project, primary_source_pack=v4_zip)

    plan = write_source_backed_tranche_plan_report(output_root=local_project)

    assert plan["status"] == "SOURCE_BACKED_TRANCHE_PLAN_READY"
    assert plan["proof_status_changed"] is False
    assert plan["target_next_variants"] < 1000
    assert "prediction_market_read_only_clob_replay" in plan["families_added"]
    assert "copy_trading_wallet_mirroring" in plan["families_removed_or_deprioritized"]
    assert "coinflip_open_hour_bias" in plan["families_removed_or_deprioritized"]
    assert plan["parameter_range_changes"]["spread_cap_bps"]["after"] == [5.0, 10.0]
    assert plan["live_public_market_priority_order"][:2] == [
        "crypto_public_forward_spot",
        "prediction_market_read_only_clob",
    ]
    assert any(
        lead["repo"] == "binance/binance-public-data"
        and lead["market_lane"] == "crypto_public_forward_spot"
        for lead in plan["priority_repo_leads"]
    )
    assert any(
        lead["repo"] == "Polymarket/py-clob-client-v2"
        and lead["adoption_decision"] == "REFERENCE_READ_ONLY_FIRST"
        for lead in plan["priority_repo_leads"]
    )
    assert any(path["requires_auth"] is False for path in plan["required_public_data_paths"])
    assert "PUBLIC_FORWARD_EVIDENCE_NOT_PROVEN" in plan["blockers_addressed"]
    assert plan["next_resume_command"] == ".\\make.cmd thousand-strategy-next-tranche"
    assert plan["order_transmission_enabled"] is False


def test_sequence64_next_tranche_uses_source_backed_plan_when_available(
    local_project: Path,
) -> None:
    from quant_os.research.strategy_factory.campaign_common import write_campaign_state
    from quant_os.research.strategy_factory.source_backed_tranche_plan import (
        write_source_backed_tranche_plan_report,
    )
    from quant_os.research.strategy_factory.source_pack_intake import (
        write_source_pack_intake_report,
    )
    from quant_os.research.strategy_factory.strategy_tournament import (
        write_next_strategy_tranche_report,
    )

    v4_zip = local_project / "v4_source_pack.zip"
    with zipfile.ZipFile(v4_zip, "w") as archive:
        archive.writestr(
            "github_repo_research/priority_repo_decisions.md",
            "Polymarket/py-clob-client-v2\nwarproxxx/poly_data\n"
            "binance/binance-public-data\nccxt/ccxt\nfreqtrade/freq\n",
        )
        archive.writestr(
            "github_repo_research/repo_research_backlog.md",
            "Add Polymarket read-only data lane design doc\n"
            "Improve replay realism from external benchmarks\n"
            "Keep crypto-first data tooling practical\n",
        )
    write_campaign_state(
        output_root=local_project,
        variants_generated=4000,
        variants_tested=1000,
        variants_rejected=996,
        last_completed_batch_index=4,
    )
    write_source_pack_intake_report(output_root=local_project, primary_source_pack=v4_zip)
    plan = write_source_backed_tranche_plan_report(output_root=local_project)

    tranche = write_next_strategy_tranche_report(output_root=local_project)
    variants = json.loads(
        (
            local_project
            / "reports/thousand_strategy_campaign/variants/latest_strategy_variants.json"
        ).read_text(encoding="utf-8")
    )
    state = json.loads(
        (
            local_project / "reports/thousand_strategy_campaign/state/latest_state.json"
        ).read_text(encoding="utf-8")
    )

    assert tranche["source_backed_plan_applied"] is True
    assert tranche["variants_generated"] == plan["target_next_variants"]
    assert tranche["cumulative_variants_generated"] == 4360
    assert tranche["cumulative_variants_tested"] == 1250
    assert variants["variant_count"] == plan["target_next_variants"]
    assert set(variants["source_backed_families"]).issubset(set(plan["families_added"]))
    assert all(
        variant["source"] == "source_backed_public_strategy_factory_v1"
        for variant in variants["variants"]
    )
    assert state["variants_generated"] == 4360
    assert state["source_backed_tranche_plan_status"] == "SOURCE_BACKED_TRANCHE_PLAN_APPLIED"


def test_sequence64_next_tranche_does_not_resurrect_public_forward_retired_candidates(
    local_project: Path,
) -> None:
    from quant_os.research.strategy_factory.campaign_common import write_json_md
    from quant_os.research.strategy_factory.strategy_tournament import (
        write_next_strategy_tranche_report,
        write_strategy_tournament_report,
    )

    first = write_strategy_tournament_report(output_root=local_project, batch_index=1)
    retired_id = first["current_best_candidate"]["id"]
    write_json_md(
        {
            "status": "VARIANT_PUBLIC_FORWARD_CANDIDATE_ROTATED",
            "retired_candidate_id": retired_id,
            "retired_candidates": [
                {
                    "candidate_id": retired_id,
                    "fake_net_pnl": -1.0,
                    "retirement_reasons": ["PUBLIC_FORWARD_FAKE_NET_PNL_NEGATIVE"],
                }
            ],
            "selected_strategy_id": "next_candidate",
        },
        output_root=local_project,
        report_dir="live_sim",
        json_name="latest_public_forward_candidate_rotation.json",
        md_name="latest_public_forward_candidate_rotation.md",
        title="Rotation",
        lines=["Retired candidate fixture"],
    )

    second = write_next_strategy_tranche_report(output_root=local_project)
    state = json.loads(
        (
            local_project / "reports/thousand_strategy_campaign/state/latest_state.json"
        ).read_text(encoding="utf-8")
    )

    assert second["current_best_candidate"]["id"] != retired_id
    assert retired_id not in {candidate["id"] for candidate in second["cumulative_top_candidates"]}
    assert retired_id not in {candidate["id"] for candidate in second["cumulative_leaderboard_top_50"]}
    assert state["current_best_candidate"]["id"] != retired_id


def test_sequence64_tournament_normalizes_cumulative_candidate_without_blockers(
    local_project: Path,
) -> None:
    from quant_os.research.strategy_factory.campaign_common import write_json_md
    from quant_os.research.strategy_factory.strategy_tournament import (
        write_strategy_tournament_report,
    )

    prior_candidate = {
        "id": "tsv_prior_without_blockers",
        "family": "momentum_reversion_intraday",
        "assets": ["BTC/USD", "ETH/USD"],
        "baseline_beaten": True,
        "placebo_beaten": True,
        "fake_net_pnl": 999.0,
        "score": 99.0,
        "observations": 9999,
        "structural_signature": "tss_prior_without_blockers",
    }
    write_json_md(
        {
            "status": "THOUSAND_STRATEGY_CAMPAIGN_CHECKPOINTED_NOT_COMPLETE",
            "batch_index": 1,
            "current_best_candidate": prior_candidate,
            "cumulative_leaderboard_top_50": [prior_candidate],
            "cumulative_top_candidates": [prior_candidate],
            "leaderboard_top_50": [prior_candidate],
            "top_candidates": [prior_candidate],
        },
        output_root=local_project,
        report_dir="tournament",
        json_name="latest_tournament.json",
        md_name="latest_tournament.md",
        title="Tournament",
        lines=["fixture"],
    )

    tournament = write_strategy_tournament_report(output_root=local_project, batch_index=2)
    state = json.loads(
        (
            local_project / "reports/thousand_strategy_campaign/state/latest_state.json"
        ).read_text(encoding="utf-8")
    )

    assert tournament["current_best_candidate"]["id"] == prior_candidate["id"]
    assert "blockers" in tournament["current_best_candidate"]
    assert "HOLDOUT_OR_FORWARD_WINDOW_NOT_PROVEN" in tournament["current_best_candidate"]["blockers"]
    assert state["blockers"] == tournament["current_best_candidate"]["blockers"]


def _variant_shape_keys(variants: list[dict[str, object]]) -> set[tuple[object, ...]]:
    return {
        (
            variant["family"],
            tuple(variant["assets"]),
            variant["lookback"],
            variant["holding_window"],
            tuple(sorted(variant["thresholds"].items())),
            variant["spread_cap_bps"],
            variant["liquidity_cap_usd"],
            variant["universe_cycle"],
        )
        for variant in variants
    }
