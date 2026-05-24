from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _write_report(root: Path, relative_path: str, payload: dict) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _manual_packet_source_reports() -> dict[str, dict]:
    safe = {
        "actual_cancel_count": 0,
        "actual_order_count": 0,
        "api_keys_loaded": False,
        "auth_key_order_attempts": 0,
        "authenticated_endpoint_called": False,
        "authenticated_requests_enabled": False,
        "checked_account_balance": False,
        "checked_portfolio": False,
        "execution_authority": "NONE",
        "live_trading_enabled": False,
        "order_transmission_enabled": False,
        "private_keys_loaded": False,
        "request_signing_enabled": False,
        "unsafe_action_attempts": 0,
    }
    readiness = {
        **safe,
        "status": "CANARY_GRADE_LIVE_SIM_PROFITABILITY_PROVEN",
        "active_market_family": "crypto_spot",
        "active_strategy": "multi_strategy_canary_grade_crypto_spot",
        "assets_tested": ["BTC/USD", "ETH/USD", "SOL/USD"],
        "strategy_families_tested": ["momentum", "reversion"],
        "venues_tested": ["kraken_public"],
        "observations_count": 1200,
        "eligible_intent_count": 400,
        "fake_fill_count": 200,
        "completed_mark_count": 200,
        "fake_gross_pnl": 0.30,
        "fake_net_pnl": 0.20,
        "baseline_beaten": True,
        "placebo_beaten": True,
        "reconciliation_failures": 0,
    }
    return {
        "readiness": readiness,
        "repeatability": {
            **safe,
            "status": "REPEATABILITY_PASSED",
            "baseline_pnl": 0.10,
            "placebo_pnl": 0.01,
            "best_baseline_name": "same_cost_mean_reversion",
            "one_trade_dominance": 0.01,
            "one_trade_dominance_cap": 0.25,
            "one_window_dominance": 0.02,
            "one_window_dominance_cap": 0.35,
            "by_window": {"window_1": 0.05, "window_2": 0.06, "window_3": 0.09},
            "by_asset": {"BTC/USD": 0.08, "ETH/USD": 0.07, "SOL/USD": 0.05},
        },
        "capacity": {
            **safe,
            "status": "CAPACITY_TINY_CANARY_PASSED",
            "max_safe_notional": 4.0,
            "capacity_by_size": {"1_usd": {"supported": True}},
        },
        "observer": {
            **safe,
            "status": "CANARY_GRADE_OBSERVER_READY",
            "source": "kraken_public_rest_unauthenticated_recent_ohlc",
            "source_policy": "public_read_only_unauthenticated",
            "venues_tested": ["kraken_public"],
        },
        "intents": {**safe, "status": "CANARY_GRADE_INTENTS_READY", "eligible_intent_count": 400},
        "fills": {**safe, "status": "CANARY_GRADE_FILLS_APPLIED", "fake_fill_count": 200},
        "pnl": {
            **safe,
            "status": "CANARY_GRADE_PNL_READY",
            "completed_mark_count": 200,
            "fake_gross_pnl": 0.30,
            "fake_net_pnl": 0.20,
            "gross_profit": 0.25,
            "gross_loss": 0.05,
        },
        "reconciliation": {
            **safe,
            "status": "CANARY_GRADE_RECONCILIATION_PASSED",
            "reconciliation_failures": 0,
        },
        "fresh_repro": {
            **safe,
            "status": "FRESH_REPRO_PASSED",
            "independent_clean_checkout_verified": True,
            "attestation_scope": "fresh_worktree_command_completion",
        },
    }


def _write_manual_packet_source_reports(root: Path, reports: dict[str, dict]) -> None:
    paths = {
        "readiness": "reports/canary_grade_live_sim/final/latest_canary_grade_live_sim_readiness.json",
        "repeatability": "reports/canary_grade_live_sim/repeatability/latest_repeatability.json",
        "capacity": "reports/canary_grade_live_sim/capacity/latest_capacity.json",
        "observer": "reports/canary_grade_live_sim/crypto/latest_observer.json",
        "intents": "reports/canary_grade_live_sim/crypto/latest_intents.json",
        "fills": "reports/canary_grade_live_sim/crypto/latest_fills.json",
        "pnl": "reports/canary_grade_live_sim/crypto/latest_pnl.json",
        "reconciliation": "reports/canary_grade_live_sim/crypto/latest_reconciliation.json",
        "fresh_repro": "reports/canary_grade_live_sim/fresh_repro/latest_fresh_repro.json",
    }
    for name, path in paths.items():
        _write_report(root, path, reports[name])


def test_sequence62_previous_10_intent_result_is_not_canary_grade() -> None:
    from quant_os.readiness.canary_grade_live_sim_readiness import (
        build_canary_grade_live_sim_readiness,
    )

    payload = build_canary_grade_live_sim_readiness(
        state={
            "observations_count": 30,
            "eligible_intent_count": 10,
            "fake_fill_count": 10,
            "completed_mark_count": 10,
            "assets_tested": ["BTC/USD"],
            "strategy_families_tested": ["btc_eth_relative_strength_rotation"],
            "walk_forward_windows": ["w1"],
            "regime_buckets": ["medium_vol"],
            "fake_net_pnl": 129.40,
            "baseline_beaten": True,
            "placebo_beaten": True,
            "reconciliation_failures": 0,
        },
        repeatability={"status": "REPEATABILITY_PASSED"},
        capacity={"status": "CAPACITY_TINY_CANARY_PASSED"},
        fresh_repro={"status": "FRESH_REPRO_PASSED"},
    )

    assert payload["status"] == "CANARY_GRADE_LIVE_SIM_NEEDS_MORE_OBSERVATIONS"
    assert "MIN_OBSERVATIONS_NOT_MET" in payload["blockers"]
    assert "MIN_ASSETS_NOT_MET" in payload["blockers"]


def test_sequence62_canary_grade_pipeline_proves_large_fixture(local_project: Path) -> None:
    from quant_os.autonomy.crypto_canary_grade_fill import write_crypto_canary_grade_fill_report
    from quant_os.autonomy.crypto_canary_grade_intents import (
        write_crypto_canary_grade_intents_report,
    )
    from quant_os.autonomy.crypto_canary_grade_ledger import write_crypto_canary_grade_ledger_report
    from quant_os.autonomy.crypto_canary_grade_observer import (
        write_crypto_canary_grade_observer_report,
    )
    from quant_os.autonomy.crypto_canary_grade_pnl import write_crypto_canary_grade_pnl_report
    from quant_os.autonomy.crypto_canary_grade_reconciliation import (
        write_crypto_canary_grade_reconciliation_report,
    )
    from quant_os.proving.crypto_live_sim_capacity import write_crypto_live_sim_capacity_report
    from quant_os.proving.crypto_live_sim_repeatability import (
        write_crypto_live_sim_repeatability_report,
    )
    from quant_os.readiness.canary_grade_fresh_repro import (
        write_canary_grade_fresh_repro_report,
    )
    from quant_os.readiness.canary_grade_live_sim_readiness import (
        write_canary_grade_live_sim_readiness_report,
    )
    from quant_os.readiness.canary_grade_manual_packet import (
        write_canary_grade_manual_packet_report,
    )

    observer = write_crypto_canary_grade_observer_report(output_root=local_project)
    intents = write_crypto_canary_grade_intents_report(output_root=local_project)
    fills = write_crypto_canary_grade_fill_report(output_root=local_project)
    ledger = write_crypto_canary_grade_ledger_report(output_root=local_project)
    pnl = write_crypto_canary_grade_pnl_report(output_root=local_project)
    reconciliation = write_crypto_canary_grade_reconciliation_report(output_root=local_project)
    repeatability = write_crypto_live_sim_repeatability_report(output_root=local_project)
    capacity = write_crypto_live_sim_capacity_report(output_root=local_project)
    fresh_repro = write_canary_grade_fresh_repro_report(
        output_root=local_project,
        proof_command_passed=True,
    )
    fresh_repro["attestation_scope"] = "fresh_worktree_command_completion"
    fresh_repro["independent_clean_checkout_verified"] = True
    _write_report(
        local_project,
        "reports/canary_grade_live_sim/fresh_repro/latest_fresh_repro.json",
        fresh_repro,
    )
    readiness = write_canary_grade_live_sim_readiness_report(output_root=local_project)
    packet = write_canary_grade_manual_packet_report(output_root=local_project)

    assert observer["observation_count"] >= 1000
    assert len(observer["assets_tested"]) >= 3
    assert len(observer["regime_buckets"]) >= 2
    assert intents["eligible_intent_count"] >= 300
    assert all(intent["fake_money"] and intent["no_transmit"] for intent in intents["intents"])
    assert fills["fake_fill_count"] >= 150
    assert fills["guaranteed_fill"] is False
    assert ledger["hidden_local_state_dependency"] is False
    assert pnl["completed_mark_count"] >= 150
    assert all(row["mark_timestamp"] > row["entry_timestamp"] for row in pnl["pnl_rows"])
    assert pnl["fake_net_pnl"] > 0
    assert reconciliation["status"] == "CANARY_GRADE_RECONCILIATION_PASSED"
    assert repeatability["status"] == "REPEATABILITY_PASSED"
    assert repeatability["one_trade_dominance"] < repeatability["one_trade_dominance_cap"]
    assert repeatability["one_window_dominance"] < repeatability["one_window_dominance_cap"]
    assert repeatability["baseline_beaten"] is True
    assert repeatability["placebo_beaten"] is True
    assert capacity["status"] == "CAPACITY_TINY_CANARY_PASSED"
    assert fresh_repro["status"] == "FRESH_REPRO_PASSED"
    assert fresh_repro["attestation_scope"] == "fresh_worktree_command_completion"
    assert fresh_repro["independent_clean_checkout_verified"] is True
    assert readiness["status"] == "CANARY_GRADE_LIVE_SIM_PROFITABILITY_PROVEN"
    assert readiness["validation_status"] == readiness["status"]
    assert readiness["venues_tested"] == observer["venues_tested"]
    assert packet["status"] == "FIRST_TINY_MANUAL_CANARY_PACKET_READY"
    assert packet["post_canary_reconciliation_command"] == ".\\make.cmd canary-grade-live-sim-public-run"
    assert packet["order_transmission_enabled"] is False
    assert packet["actual_order_count"] == 0
    assert packet["conflict_summary"]["status"] == "CONFLICT_DETECTOR_PASSED"
    assert packet["conflict_summary"]["veto_reasons"] == []
    review_pack = packet["final_review_pack"]
    assert review_pack["sample_size"]["observations"] == observer["observation_count"]
    assert review_pack["sample_size"]["eligible_intents"] == intents["eligible_intent_count"]
    assert review_pack["sample_size"]["fake_fills"] == fills["fake_fill_count"]
    assert review_pack["sample_size"]["completed_marks"] == pnl["completed_mark_count"]
    assert review_pack["fake_net_pnl_after_costs"]["fake_net_pnl"] == pnl["fake_net_pnl"]
    assert review_pack["baseline_placebo_comparison"]["baseline_beaten"] is True
    assert review_pack["baseline_placebo_comparison"]["placebo_beaten"] is True
    assert review_pack["gates"] == {
        "repeatability": "REPEATABILITY_PASSED",
        "reconciliation": "CANARY_GRADE_RECONCILIATION_PASSED",
        "conflict": "CONFLICT_DETECTOR_PASSED",
        "capacity": "CAPACITY_TINY_CANARY_PASSED",
        "readiness": "CANARY_GRADE_LIVE_SIM_PROFITABILITY_PROVEN",
        "fresh_repro": "FRESH_REPRO_PASSED",
        "independent_fresh_worktree": True,
    }
    packet_md = (
        local_project
        / "reports/canary_grade_live_sim/manual_canary_packet/latest_manual_canary_packet.md"
    ).read_text(encoding="utf-8")
    for heading in [
        "## 1. Selected Strategy/Lane",
        "## 2. Exact Assets",
        "## 3. Sample Size",
        "## 4. Fake Intents/Fills/Marks",
        "## 5. Fake Net PnL After Costs",
        "## 6. Baseline/Placebo Comparison",
        "## 7. Repeatability/Reconciliation/Conflict/Capacity",
        "## 8. Dominance Checks",
        "## 9. Risk Envelope",
        "## 10. Exact Kill-Switch/Block Conditions",
        "## 11. What Could Still Fail In Real Money",
        "## 12. Exact Human-Only Arming Boundary",
        "## 13. Post-Canary Reconciliation Checklist",
        "## 14. Rollback/Abort Checklist",
    ]:
        assert heading in packet_md
    forbidden_packet_terms = [
        "POST /portfolio/orders",
        "DELETE /portfolio/orders",
        "Authorization:",
        "Bearer ",
        "ORDER_READY_TO_SEND",
        "ORDER_SENT",
    ]
    assert not any(term in packet_md for term in forbidden_packet_terms)


def test_sequence62_fresh_repro_verifies_independent_public_worktree_reports(
    local_project: Path,
) -> None:
    from quant_os.readiness.canary_grade_fresh_repro import (
        write_canary_grade_fresh_repro_report,
    )

    proof_root = local_project / "independent-proof"
    reports = _manual_packet_source_reports()
    reports["observer"]["source"] = "kraken_public_rest_unauthenticated_recent_ohlc"
    reports["observer"]["source_policy"] = "public_read_only_unauthenticated"
    reports["readiness"]["status"] = "CANARY_GRADE_LIVE_SIM_PROFITABILITY_PROVEN"
    reports["pnl"]["pnl_rows"] = [
        {
            "entry_timestamp": "2026-05-24T01:00:00Z",
            "mark_timestamp": "2026-05-24T01:01:00Z",
        }
    ]
    _write_manual_packet_source_reports(proof_root, reports)
    _write_report(
        proof_root,
        "reports/canary_grade_live_sim/crypto/latest_ledger.json",
        {**reports["fills"], "status": "CANARY_GRADE_LEDGER_UPDATED"},
    )

    fresh = write_canary_grade_fresh_repro_report(
        output_root=local_project,
        proof_command_passed=True,
        proof_command=".\\make.cmd money-worthy-canary-grade-public-run",
        proof_output_root=str(proof_root),
        independent_clean_checkout_verified=True,
        proof_head_oid="abc123",
    )

    assert fresh["status"] == "INDEPENDENT_FRESH_WORKTREE_PROOF_PASSED"
    assert fresh["independent_fresh_worktree_proof_status"] == (
        "INDEPENDENT_FRESH_WORKTREE_PROOF_PASSED"
    )
    assert fresh["independent_clean_checkout_verified"] is True
    assert fresh["proof_output_root"] == str(proof_root)
    assert fresh["public_data_source"] == "kraken_public_rest_unauthenticated_recent_ohlc"
    assert fresh["blockers"] == []


def test_sequence62_fresh_repro_blocks_independent_fixture_or_losing_proof(
    local_project: Path,
) -> None:
    from quant_os.readiness.canary_grade_fresh_repro import (
        write_canary_grade_fresh_repro_report,
    )

    proof_root = local_project / "losing-proof"
    reports = _manual_packet_source_reports()
    reports["observer"]["source"] = "fixture_public_canary_grade_kraken_shape"
    reports["readiness"]["status"] = "CANARY_GRADE_LIVE_SIM_NOT_PROVEN"
    reports["readiness"]["fake_net_pnl"] = -0.1
    reports["pnl"]["fake_net_pnl"] = -0.1
    _write_manual_packet_source_reports(proof_root, reports)
    _write_report(
        proof_root,
        "reports/canary_grade_live_sim/crypto/latest_ledger.json",
        {**reports["fills"], "status": "CANARY_GRADE_LEDGER_UPDATED"},
    )

    fresh = write_canary_grade_fresh_repro_report(
        output_root=local_project,
        proof_command_passed=True,
        proof_command=".\\make.cmd money-worthy-canary-grade-public-run",
        proof_output_root=str(proof_root),
        independent_clean_checkout_verified=True,
    )

    assert fresh["status"] == "FRESH_REPRO_BLOCKED"
    assert fresh["independent_fresh_worktree_proof_status"] == (
        "INDEPENDENT_FRESH_WORKTREE_PROOF_BLOCKED"
    )
    assert "INDEPENDENT_PROOF_READINESS_NOT_PROVEN" in fresh["blockers"]
    assert "INDEPENDENT_PROOF_NOT_REAL_PUBLIC_KRAKEN" in fresh["blockers"]


def test_sequence62_manual_packet_requires_direct_gate_statuses(local_project: Path) -> None:
    from quant_os.readiness.canary_grade_manual_packet import build_canary_grade_manual_packet

    cases = [
        (
            "stale_readiness",
            ("readiness", "status", "CANARY_GRADE_LIVE_SIM_NOT_PROVEN"),
            "CANARY_GRADE_READINESS_NOT_PROVEN",
        ),
        (
            "capacity_fail",
            ("capacity", "status", "CAPACITY_BLOCKED_BY_LIQUIDITY"),
            "CAPACITY_TINY_CANARY_NOT_PASSED",
        ),
        (
            "repeatability_fail",
            ("repeatability", "status", "REPEATABILITY_BLOCKED"),
            "REPEATABILITY_NOT_PASSED",
        ),
        (
            "reconciliation_fail",
            ("reconciliation", "status", "CANARY_GRADE_RECONCILIATION_FAILED"),
            "CANARY_GRADE_RECONCILIATION_NOT_PASSED",
        ),
        (
            "nonpositive_pnl",
            ("readiness", "fake_net_pnl", 0.0),
            "FAKE_NET_PNL_NOT_POSITIVE",
        ),
        (
            "baseline_fail",
            ("readiness", "baseline_beaten", False),
            "BASELINE_NOT_BEATEN",
        ),
        (
            "placebo_fail",
            ("readiness", "placebo_beaten", False),
            "PLACEBO_NOT_BEATEN",
        ),
        (
            "safety_flag_drift",
            ("readiness", "live_trading_enabled", True),
            "UNSAFE_FLAG_TRUE:readiness:live_trading_enabled",
        ),
        (
            "signing_flag_drift",
            ("pnl", "request_signing_enabled", True),
            "UNSAFE_FLAG_TRUE:pnl:request_signing_enabled",
        ),
        (
            "order_counter_drift",
            ("fills", "actual_order_count", 1),
            "UNSAFE_COUNTER_NONZERO:fills:actual_order_count",
        ),
    ]
    for case_name, mutation, expected_blocker in cases:
        case_root = local_project / case_name
        reports = _manual_packet_source_reports()
        report_name, key, value = mutation
        reports[report_name][key] = value
        _write_manual_packet_source_reports(case_root, reports)

        packet = build_canary_grade_manual_packet(output_root=case_root)

        assert packet["status"] == "FIRST_TINY_MANUAL_CANARY_PACKET_BLOCKED"
        assert expected_blocker in packet["blockers"]
        assert packet["order_transmission_enabled"] is False
        assert packet["actual_order_count"] == 0


def test_sequence62_manual_packet_blocks_conflict_veto(local_project: Path) -> None:
    from quant_os.readiness.canary_grade_manual_packet import build_canary_grade_manual_packet

    reports = _manual_packet_source_reports()
    reports["pnl"]["fake_gross_pnl"] = 5.0
    reports["pnl"]["fake_net_pnl"] = 0.10
    reports["readiness"]["fake_gross_pnl"] = 5.0
    reports["readiness"]["fake_net_pnl"] = 0.10
    _write_manual_packet_source_reports(local_project, reports)

    packet = build_canary_grade_manual_packet(output_root=local_project)

    assert packet["conflict_summary"]["status"] == "CONFLICT_DETECTOR_VETOED"
    assert "EDGE_SMALLER_THAN_EXECUTION_UNCERTAINTY" in packet["conflict_summary"]["veto_reasons"]
    assert packet["status"] == "FIRST_TINY_MANUAL_CANARY_PACKET_BLOCKED"
    assert "CONFLICT_DETECTOR_NOT_PASSED" in packet["blockers"]


def test_sequence62_manual_packet_reports_review_ready_not_armable_without_independent_repro(
    local_project: Path,
) -> None:
    from quant_os.readiness.canary_grade_manual_packet import build_canary_grade_manual_packet

    reports = _manual_packet_source_reports()
    reports["fresh_repro"]["independent_clean_checkout_verified"] = False
    reports["fresh_repro"]["attestation_scope"] = "same_worktree_command_completion"
    _write_manual_packet_source_reports(local_project, reports)

    packet = build_canary_grade_manual_packet(output_root=local_project)

    assert packet["status"] == "REVIEW_READY_NOT_CANARY_ARMABLE"
    assert packet["review_ready"] is True
    assert packet["canary_armable"] is False
    assert "INDEPENDENT_FRESH_WORKTREE_PROOF_NOT_AVAILABLE" in packet["blockers"]


def test_sequence62_readiness_blocks_baseline_placebo_dominance_stress_and_repro() -> None:
    from quant_os.readiness.canary_grade_live_sim_readiness import (
        build_canary_grade_live_sim_readiness,
    )

    state = {
        "observations_count": 1200,
        "eligible_intent_count": 400,
        "fake_fill_count": 200,
        "completed_mark_count": 200,
        "assets_tested": ["BTC/USD", "ETH/USD", "SOL/USD"],
        "strategy_families_tested": ["s1", "s2"],
        "walk_forward_windows": ["w1", "w2", "w3"],
        "regime_buckets": ["low_vol", "high_vol"],
        "fake_net_pnl": 100.0,
        "baseline_beaten": False,
        "placebo_beaten": False,
        "reconciliation_failures": 0,
    }
    repeatability = {
        "status": "REPEATABILITY_BLOCKED",
        "one_trade_dominance": 0.60,
        "one_trade_dominance_cap": 0.25,
        "one_window_dominance": 0.70,
        "one_window_dominance_cap": 0.35,
        "worse_fill_status": "BLOCKED",
        "higher_fee_status": "BLOCKED",
        "delayed_entry_status": "BLOCKED",
        "baseline_beaten": False,
        "placebo_beaten": False,
    }

    payload = build_canary_grade_live_sim_readiness(
        state=state,
        repeatability=repeatability,
        capacity={"status": "CAPACITY_BLOCKED_BY_LIQUIDITY"},
        fresh_repro={"status": "LOCAL_ONLY_DEPENDENCY_BLOCKED"},
    )

    assert payload["status"] == "CANARY_GRADE_LIVE_SIM_BLOCKED_BY_BASELINE"
    assert "BASELINE_NOT_BEATEN" in payload["blockers"]
    assert "PLACEBO_NOT_BEATEN" in payload["blockers"]
    assert "ONE_TRADE_DOMINANCE_TOO_HIGH" in payload["blockers"]
    assert "ONE_WINDOW_DOMINANCE_TOO_HIGH" in payload["blockers"]
    assert "WORSE_FILL_STRESS_FAILED" in payload["blockers"]
    assert "HIGHER_FEE_STRESS_FAILED" in payload["blockers"]
    assert "DELAYED_ENTRY_STRESS_FAILED" in payload["blockers"]
    assert "CAPACITY_TINY_CANARY_NOT_PASSED" in payload["blockers"]
    assert "FRESH_WORKTREE_REPRO_NOT_PASSED" in payload["blockers"]


def test_sequence62_readiness_does_not_call_repeatability_or_capacity_reconciliation() -> None:
    from quant_os.readiness.canary_grade_live_sim_readiness import (
        build_canary_grade_live_sim_readiness,
    )

    state = {
        "observations_count": 2000,
        "eligible_intent_count": 400,
        "fake_fill_count": 200,
        "completed_mark_count": 200,
        "assets_tested": ["BTC/USD", "ETH/USD", "SOL/USD"],
        "strategy_families_tested": ["reversion", "snapback"],
        "walk_forward_windows": ["window_1", "window_2", "window_3"],
        "regime_buckets": ["low_vol", "high_vol"],
        "fake_net_pnl": 100.0,
        "baseline_beaten": True,
        "placebo_beaten": True,
        "reconciliation_failures": 0,
    }

    payload = build_canary_grade_live_sim_readiness(
        state=state,
        repeatability={
            "status": "REPEATABILITY_BLOCKED",
            "one_trade_dominance": 0.01,
            "one_trade_dominance_cap": 0.25,
            "one_window_dominance": 0.01,
            "one_window_dominance_cap": 0.35,
            "worse_fill_status": "PASSED",
            "higher_fee_status": "PASSED",
            "delayed_entry_status": "PASSED",
        },
        capacity={"status": "CAPACITY_LIMITED"},
        fresh_repro={"status": "FRESH_REPRO_PASSED"},
    )

    assert payload["status"] == "CANARY_GRADE_LIVE_SIM_NOT_PROVEN"
    assert "RECONCILIATION_FAILURES_PRESENT" not in payload["blockers"]
    assert "REPEATABILITY_NOT_PASSED" in payload["blockers"]
    assert "CAPACITY_TINY_CANARY_NOT_PASSED" in payload["blockers"]


def test_sequence62_readiness_requires_explicit_fresh_repro_report(local_project: Path) -> None:
    from quant_os.autonomy.crypto_canary_grade_fill import write_crypto_canary_grade_fill_report
    from quant_os.autonomy.crypto_canary_grade_intents import (
        write_crypto_canary_grade_intents_report,
    )
    from quant_os.autonomy.crypto_canary_grade_ledger import write_crypto_canary_grade_ledger_report
    from quant_os.autonomy.crypto_canary_grade_observer import (
        write_crypto_canary_grade_observer_report,
    )
    from quant_os.autonomy.crypto_canary_grade_pnl import write_crypto_canary_grade_pnl_report
    from quant_os.autonomy.crypto_canary_grade_reconciliation import (
        write_crypto_canary_grade_reconciliation_report,
    )
    from quant_os.proving.crypto_live_sim_capacity import write_crypto_live_sim_capacity_report
    from quant_os.proving.crypto_live_sim_repeatability import (
        write_crypto_live_sim_repeatability_report,
    )
    from quant_os.readiness.canary_grade_live_sim_readiness import (
        write_canary_grade_live_sim_readiness_report,
    )

    observer = write_crypto_canary_grade_observer_report(output_root=local_project)
    write_crypto_canary_grade_intents_report(output_root=local_project)
    write_crypto_canary_grade_fill_report(output_root=local_project)
    write_crypto_canary_grade_ledger_report(output_root=local_project)
    write_crypto_canary_grade_pnl_report(output_root=local_project)
    write_crypto_canary_grade_reconciliation_report(output_root=local_project)
    write_crypto_live_sim_repeatability_report(output_root=local_project)
    write_crypto_live_sim_capacity_report(output_root=local_project)

    readiness = write_canary_grade_live_sim_readiness_report(output_root=local_project)

    assert observer["venues_tested"]
    assert readiness["status"] == "CANARY_GRADE_LIVE_SIM_NOT_PROVEN"
    assert readiness["fresh_repro_status"] == "FRESH_REPRO_BLOCKED"
    assert "FRESH_WORKTREE_REPRO_NOT_PASSED" in readiness["blockers"]
    assert readiness["venues_tested"] == observer["venues_tested"]


def test_sequence62_repeatability_stress_scales_with_fake_notional() -> None:
    from quant_os.proving.crypto_live_sim_repeatability import build_crypto_live_sim_repeatability

    rows = [
        {
            "fake_net_pnl": 0.001,
            "fake_gross_pnl": 0.0012,
            "total_cost": 0.0002,
            "notional_usd": 1.0,
            "return_1m": 0.0,
            "symbol": "BTC/USD",
            "strategy": "crypto_volatility_compression_breakout_spot_only",
            "regime": "low_vol",
            "session_bucket": "session_1",
            "walk_forward_window": f"window_{idx % 3}",
            "entry_price": 100.0,
            "mark_price": 100.1,
        }
        for idx in range(200)
    ]

    payload = build_crypto_live_sim_repeatability(
        pnl={
            "pnl_rows": rows,
            "fake_net_pnl": 0.2,
            "gross_profit": 0.24,
            "gross_loss": 0.04,
        }
    )

    assert payload["worse_fill_status"] == "PASSED"
    assert payload["higher_fee_status"] == "PASSED"
    assert "WORSE_FILL_STRESS_FAILED" not in payload["blockers"]
    assert "HIGHER_FEE_STRESS_FAILED" not in payload["blockers"]


def test_sequence62_repeatability_reports_same_cost_baseline_winner() -> None:
    from quant_os.proving.crypto_live_sim_repeatability import build_crypto_live_sim_repeatability

    rows = [
        {
            "symbol": "BTC/USD",
            "entry_price": 100.0,
            "mark_price": 101.0,
            "return_1m": 0.01,
            "fake_net_pnl": 0.10,
            "walk_forward_window": "window_1",
            "strategy": "crypto_spot_momentum_reversion_intraday",
            "regime": "high_vol",
            "session_bucket": "session_0",
            "notional_usd": 1.0,
        },
        {
            "symbol": "ETH/USD",
            "entry_price": 50.0,
            "mark_price": 49.5,
            "return_1m": -0.01,
            "fake_net_pnl": 0.04,
            "walk_forward_window": "window_2",
            "strategy": "crypto_spot_liquidity_shock_reversion_long_only",
            "regime": "low_vol",
            "session_bucket": "session_1",
            "notional_usd": 1.0,
        },
    ]

    payload = build_crypto_live_sim_repeatability(
        pnl={"pnl_rows": rows, "fake_net_pnl": 0.14, "gross_profit": 0.2, "gross_loss": 0.06}
    )

    assert payload["baseline_pnls"]["same_cost_momentum"] == 0.1
    assert payload["baseline_pnls"]["same_cost_mean_reversion"] == 0.04
    assert payload["best_baseline_name"] in payload["baseline_pnls"]


def test_sequence62_canary_intents_use_strategy_direction_and_tiny_notional() -> None:
    from quant_os.autonomy.crypto_canary_grade_fill import apply_crypto_canary_grade_fill_model
    from quant_os.autonomy.crypto_canary_grade_intents import build_crypto_canary_grade_intents

    observer = {
        "observations": [
            {
                "observation_id": "obs_momentum_down",
                "symbol": "VVV/USD",
                "strategy": "crypto_spot_momentum_reversion_intraday",
                "venue": "kraken_public",
                "entry_timestamp": "2026-05-23T10:00:00Z",
                "entry_price": 100.0,
                "mark_timestamp": "2026-05-23T10:15:00Z",
                "mark_horizon_minutes": 15,
                "mark_price": 101.0,
                "return_1m": -0.01,
                "spread": 0.02,
                "ask_size": 10.0,
                "regime": "low_vol",
                "walk_forward_window": "window_1",
                "session_bucket": "session_0",
                "eligible": True,
            },
            {
                "observation_id": "obs_momentum_up",
                "symbol": "VVV/USD",
                "strategy": "crypto_spot_momentum_reversion_intraday",
                "venue": "kraken_public",
                "entry_timestamp": "2026-05-23T10:01:00Z",
                "entry_price": 100.0,
                "mark_timestamp": "2026-05-23T10:16:00Z",
                "mark_horizon_minutes": 15,
                "mark_price": 99.0,
                "return_1m": 0.01,
                "spread": 0.02,
                "ask_size": 10.0,
                "regime": "low_vol",
                "walk_forward_window": "window_1",
                "session_bucket": "session_0",
                "eligible": True,
            },
            {
                "observation_id": "obs_momentum_up_other_session",
                "symbol": "VVV/USD",
                "strategy": "crypto_spot_momentum_reversion_intraday",
                "venue": "kraken_public",
                "entry_timestamp": "2026-05-23T10:01:30Z",
                "entry_price": 100.0,
                "mark_timestamp": "2026-05-23T10:16:30Z",
                "mark_horizon_minutes": 15,
                "mark_price": 99.0,
                "return_1m": 0.0005,
                "spread": 0.02,
                "ask_size": 10.0,
                "regime": "low_vol",
                "walk_forward_window": "window_1",
                "session_bucket": "session_1",
                "eligible": True,
            },
            {
                "observation_id": "obs_breakout_down",
                "symbol": "HYPE/USD",
                "strategy": "crypto_spot_liquidity_shock_reversion_long_only",
                "venue": "kraken_public",
                "entry_timestamp": "2026-05-23T10:02:00Z",
                "entry_price": 50.0,
                "mark_timestamp": "2026-05-23T11:02:00Z",
                "mark_horizon_minutes": 60,
                "mark_price": 49.0,
                "return_1m": -0.01,
                "spread": 0.02,
                "ask_size": 10.0,
                "regime": "low_vol",
                "walk_forward_window": "window_1",
                "session_bucket": "session_3",
                "eligible": True,
            },
        ]
    }

    intents = build_crypto_canary_grade_intents(observer=observer)
    fills = apply_crypto_canary_grade_fill_model(
        intents=intents["intents"],
        observations=observer["observations"],
    )

    sides = {intent["observation_id"]: intent["side"] for intent in intents["intents"]}
    assert sides == {
        "obs_momentum_down": "buy",
        "obs_momentum_up": "buy",
        "obs_momentum_up_other_session": "buy",
        "obs_breakout_down": "buy",
    }
    assert all("return_1m" in intent for intent in intents["intents"])
    assert all("mark_horizon_minutes" in intent for intent in intents["intents"])
    assert all(intent["notional_usd"] == 1.0 for intent in intents["intents"])
    assert all("return_1m" in fill for fill in fills["fake_fills"])
    assert all("mark_horizon_minutes" in fill for fill in fills["fake_fills"])
    assert fills["fake_fills"][0]["quantity"] == 0.01
    assert fills["fake_fills"][1]["quantity"] == 0.01
    assert fills["fake_fills"][2]["quantity"] == 0.01
    assert fills["fake_fills"][3]["quantity"] == 0.02
    assert fills["fake_fill_count"] == 4
    assert fills["fake_no_fill_count"] == 0


def test_sequence62_canary_intents_require_signal_quality_gate() -> None:
    from quant_os.autonomy.crypto_canary_grade_intents import build_crypto_canary_grade_intents

    gate = "public_positive_depth_safe_kraken_60m_reversion_15m_momentum_dip_v4"
    base = {
        "symbol": "VVV/USD",
        "strategy": "crypto_spot_momentum_reversion_intraday",
        "venue": "kraken_public",
        "entry_price": 100.0,
        "mark_price": 101.0,
        "spread": 0.02,
        "ask_size": 10.0,
        "regime": "low_vol",
        "walk_forward_window": "window_1",
        "session_bucket": "session_0",
        "eligible": True,
    }
    observer = {
        "observations": [
            {
                **base,
                "observation_id": "obs_trade",
                "entry_timestamp": "2026-05-23T10:00:00Z",
                "mark_timestamp": "2026-05-23T10:15:00Z",
                "mark_horizon_minutes": 15,
                "return_1m": 0.01,
            },
            {
                **base,
                "observation_id": "obs_tiny_move",
                "entry_timestamp": "2026-05-23T10:02:00Z",
                "mark_timestamp": "2026-05-23T10:17:00Z",
                "mark_horizon_minutes": 15,
                "return_1m": 0.0,
            },
            {
                **base,
                "observation_id": "obs_other_session",
                "entry_timestamp": "2026-05-23T10:03:00Z",
                "mark_timestamp": "2026-05-23T10:18:00Z",
                "mark_horizon_minutes": 15,
                "return_1m": 0.0005,
                "session_bucket": "session_1",
            },
            {
                **base,
                "observation_id": "obs_fast_mark",
                "entry_timestamp": "2026-05-23T10:04:00Z",
                "mark_timestamp": "2026-05-23T10:05:00Z",
                "mark_horizon_minutes": 1,
                "return_1m": 0.01,
            },
            {
                **base,
                "observation_id": "obs_session_5",
                "entry_timestamp": "2026-05-23T10:05:00Z",
                "mark_timestamp": "2026-05-23T11:05:00Z",
                "mark_horizon_minutes": 60,
                "return_1m": 0.01,
                "session_bucket": "session_5",
            },
        ]
    }

    payload = build_crypto_canary_grade_intents(observer=observer)

    assert [intent["observation_id"] for intent in payload["intents"]] == [
        "obs_trade",
        "obs_other_session",
    ]
    assert (
        payload["intents"][0]["signal_quality_gate"]
        == gate
    )


def test_sequence62_canary_intents_reject_signals_below_conservative_cost_hurdle() -> None:
    from quant_os.autonomy.crypto_canary_grade_intents import build_crypto_canary_grade_intents

    gate = "public_positive_depth_safe_kraken_60m_reversion_15m_momentum_dip_v4"
    base = {
        "symbol": "VVV/USD",
        "strategy": "crypto_spot_momentum_reversion_intraday",
        "venue": "kraken_public",
        "entry_price": 100.0,
        "mark_price": 101.0,
        "spread": 0.02,
        "ask_size": 10.0,
        "regime": "low_vol",
        "walk_forward_window": "window_1",
        "session_bucket": "session_0",
        "mark_horizon_minutes": 15,
        "eligible": True,
    }
    observer = {
        "observations": [
            {
                **base,
                "observation_id": "obs_too_small_for_costs",
                "entry_timestamp": "2026-05-23T10:00:00Z",
                "mark_timestamp": "2026-05-23T10:15:00Z",
                "return_1m": 0.00001,
            },
            {
                **base,
                "observation_id": "obs_cost_hurdled",
                "entry_timestamp": "2026-05-23T10:02:00Z",
                "mark_timestamp": "2026-05-23T10:17:00Z",
                "return_1m": 0.01,
            },
        ]
    }

    payload = build_crypto_canary_grade_intents(observer=observer)

    assert [intent["observation_id"] for intent in payload["intents"]] == ["obs_cost_hurdled"]
    assert (
        payload["intents"][0]["signal_quality_gate"]
        == gate
    )


def test_sequence62_pnl_blocks_lookahead() -> None:
    from quant_os.autonomy.crypto_canary_grade_pnl import build_crypto_canary_grade_pnl

    payload = build_crypto_canary_grade_pnl(
        ledger={
            "ledger_entries": [
                {
                    "entry_timestamp": "2026-05-18T10:05:00Z",
                    "mark_timestamp": "2026-05-18T10:04:00Z",
                    "entry_price": 100.0,
                    "mark_price": 101.0,
                    "quantity": 1.0,
                    "side": "buy",
                    "spread_cost": 0.01,
                    "slippage_cost": 0.01,
                    "fee_cost": 0.01,
                }
            ]
        }
    )

    assert payload["status"] == "CANARY_GRADE_PNL_BLOCKED"
    assert "LOOKAHEAD_MARK_NOT_AFTER_ENTRY" in payload["blockers"]


def test_sequence62_capacity_blocks_unsupported_size() -> None:
    from quant_os.proving.crypto_live_sim_capacity import build_crypto_live_sim_capacity

    payload = build_crypto_live_sim_capacity(
        fills={
            "fake_fills": [
                {
                    "symbol": "BTC/USD",
                    "entry_price": 100.0,
                    "quantity": 0.001,
                    "public_depth_notional": 0.50,
                    "spread": 0.02,
                }
            ]
        }
    )

    assert payload["status"] == "CAPACITY_BLOCKED_BY_LIQUIDITY"
    assert payload["capacity_by_size"]["1_usd"]["supported"] is False


def test_sequence62_capacity_passes_when_tiny_canary_size_is_supported() -> None:
    from quant_os.proving.crypto_live_sim_capacity import build_crypto_live_sim_capacity

    payload = build_crypto_live_sim_capacity(
        fills={
            "fake_fills": [
                {
                    "symbol": "BTC/USD",
                    "entry_price": 100.0,
                    "quantity": 0.01,
                    "public_depth_notional": 6.0,
                    "spread": 0.02,
                }
            ]
        }
    )

    assert payload["status"] == "CAPACITY_TINY_CANARY_PASSED"
    assert payload["capacity_by_size"]["1_usd"]["supported"] is True
    assert payload["capacity_by_size"]["5_usd"]["supported"] is True
    assert payload["capacity_by_size"]["10_usd"]["supported"] is False


def test_sequence62_scheduler_and_cli_are_data_only(local_project: Path) -> None:
    from quant_os.autonomy.canary_grade_live_sim_schedule import (
        write_canary_grade_live_sim_schedule_report,
    )

    payload = write_canary_grade_live_sim_schedule_report(output_root=local_project)

    assert payload["status"] == "CANARY_GRADE_LIVE_SIM_SCHEDULE_READY"
    assert payload["data_only"] is True
    assert payload["live_trading_enabled"] is False
    assert payload["execution_authority"] == "NONE"
    assert "no credentials" in payload["powershell_command"].lower()
    assert "no orders" in payload["powershell_command"].lower()
    make_cmd = (Path(__file__).resolve().parents[1] / "make.cmd").read_text(encoding="utf-8")
    assert "sequence62-smoke" in make_cmd
    assert "canary-grade-live-sim-smoke" in make_cmd

    commands = [
        [sys.executable, "-m", "quant_os.cli", "autonomy", "crypto-canary-grade-observer"],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "crypto-canary-grade-intents"],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "crypto-canary-grade-fill"],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "crypto-canary-grade-ledger"],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "crypto-canary-grade-pnl"],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "crypto-canary-grade-reconciliation"],
        [sys.executable, "-m", "quant_os.cli", "proving", "crypto-live-sim-repeatability"],
        [sys.executable, "-m", "quant_os.cli", "proving", "crypto-live-sim-capacity"],
        [
            sys.executable,
            "-m",
            "quant_os.cli",
            "readiness",
            "canary-grade-fresh-repro",
            "--proof-command-passed",
        ],
        [sys.executable, "-m", "quant_os.cli", "readiness", "canary-grade-live-sim"],
        [sys.executable, "-m", "quant_os.cli", "readiness", "canary-grade-manual-packet"],
        [sys.executable, "-m", "quant_os.cli", "autonomy", "canary-grade-live-sim-schedule"],
    ]
    for command in commands:
        result = subprocess.run(command, cwd=local_project, capture_output=True, text=True, check=False)
        assert result.returncode == 0, result.stderr
        assert "ORDER_SENT" not in result.stdout
        assert "LIVE_READY" not in result.stdout
