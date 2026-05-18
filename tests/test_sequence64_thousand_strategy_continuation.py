from __future__ import annotations

import json
import os
import subprocess
import sys
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
