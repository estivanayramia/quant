from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.autonomy.canary_grade_live_sim_common import ROOT, canary_safe_payload
from quant_os.autonomy.live_market_sim_common import load_json
from quant_os.readiness.canary_readiness_common import write_json_markdown_report
from quant_os.risk.strategy_conflict_detector import build_strategy_conflict_detector

REPORT_DIR = ROOT / "manual_canary_packet"


def build_canary_grade_manual_packet(*, output_root: str | Path = ".") -> dict[str, Any]:
    readiness = load_json(
        "reports/canary_grade_live_sim/final/latest_canary_grade_live_sim_readiness.json",
        output_root=output_root,
    ) or {}
    repeatability = load_json(
        "reports/canary_grade_live_sim/repeatability/latest_repeatability.json",
        output_root=output_root,
    ) or {}
    capacity = load_json("reports/canary_grade_live_sim/capacity/latest_capacity.json", output_root=output_root) or {}
    observer = load_json("reports/canary_grade_live_sim/crypto/latest_observer.json", output_root=output_root) or {}
    intents = load_json("reports/canary_grade_live_sim/crypto/latest_intents.json", output_root=output_root) or {}
    fills = load_json("reports/canary_grade_live_sim/crypto/latest_fills.json", output_root=output_root) or {}
    pnl = load_json("reports/canary_grade_live_sim/crypto/latest_pnl.json", output_root=output_root) or {}
    reconciliation = load_json(
        "reports/canary_grade_live_sim/crypto/latest_reconciliation.json",
        output_root=output_root,
    ) or {}
    fresh_repro = load_json(
        "reports/canary_grade_live_sim/fresh_repro/latest_fresh_repro.json",
        output_root=output_root,
    ) or {}
    conflict = _build_conflict_summary(readiness=readiness, capacity=capacity, pnl=pnl)
    gate = _build_manual_packet_gate(
        readiness=readiness,
        repeatability=repeatability,
        capacity=capacity,
        pnl=pnl,
        reconciliation=reconciliation,
        conflict=conflict,
        fresh_repro=fresh_repro,
        safety_reports={
            "readiness": readiness,
            "repeatability": repeatability,
            "capacity": capacity,
            "observer": observer,
            "intents": intents,
            "fills": fills,
            "pnl": pnl,
            "reconciliation": reconciliation,
            "fresh_repro": fresh_repro,
        },
    )
    final_review_pack = _build_final_review_pack(
        readiness=readiness,
        repeatability=repeatability,
        capacity=capacity,
        observer=observer,
        intents=intents,
        fills=fills,
        pnl=pnl,
        reconciliation=reconciliation,
        conflict=conflict,
        fresh_repro=fresh_repro,
    )
    return canary_safe_payload(
        schema_version="canary_grade_manual_packet_v1",
        status=gate["status"],
        allowed_statuses=[
            "FIRST_TINY_MANUAL_CANARY_PACKET_READY",
            "REVIEW_READY_NOT_CANARY_ARMABLE",
            "FIRST_TINY_MANUAL_CANARY_PACKET_BLOCKED",
        ],
        candidate_summary={
            "market_family": "crypto_spot",
            "assets_tested": readiness.get("assets_tested", []),
            "strategies_tested": readiness.get("strategy_families_tested", []),
            "fake_net_pnl": readiness.get("fake_net_pnl", 0.0),
            "sample_count": readiness.get("observations_count", 0),
        },
        repeatability_summary={
            "status": repeatability.get("status"),
            "one_trade_dominance": repeatability.get("one_trade_dominance"),
            "one_window_dominance": repeatability.get("one_window_dominance"),
        },
        conflict_summary=conflict,
        capacity_summary={
            "status": capacity.get("status"),
            "max_safe_notional": capacity.get("max_safe_notional"),
            "capacity_by_size": capacity.get("capacity_by_size", {}),
        },
        fresh_repro_summary={
            "status": fresh_repro.get("status", "FRESH_REPRO_MISSING"),
            "independent_clean_checkout_verified": fresh_repro.get("independent_clean_checkout_verified") is True,
            "attestation_scope": fresh_repro.get("attestation_scope"),
        },
        final_review_pack=final_review_pack,
        review_ready=gate["review_ready"],
        canary_armable=gate["canary_armable"],
        risk_envelope={
            "tiny_manual_canary_only": True,
            "margin": False,
            "portfolio_margin_allowed": False,
            "cross_collateral_allowed": False,
            "leverage": False,
            "shorting": False,
            "futures_perps_options": False,
            "portfolio_checks_must_remain_disabled": True,
        },
        no_transmit_preview={
            "fake_money": True,
            "no_transmit": True,
            "order_transmission_enabled": False,
            "human_approval_required_separately": True,
            "credentials_required_separately": True,
        },
        kill_switch="manual_canary_kill_switch_required_before_any_separate_human_action",
        post_canary_reconciliation_command=".\\make.cmd canary-grade-live-sim-public-run",
        blockers=gate["blockers"],
        exact_resume_command=".\\make.cmd canary-grade-live-sim-public-run",
        next_action="Human may review packet; no order is authorized or placed by this report."
        if gate["status"] == "FIRST_TINY_MANUAL_CANARY_PACKET_READY"
        else (
            "Run independent fresh-worktree proof before any canary arming."
            if gate["status"] == "REVIEW_READY_NOT_CANARY_ARMABLE"
            else "Continue canary-grade hardening before manual packet review."
        ),
    )


def write_canary_grade_manual_packet_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_canary_grade_manual_packet(output_root=output_root)
    report_paths = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_manual_canary_packet.json",
        md_name="latest_manual_canary_packet.md",
        title="Canary-Grade First Tiny Manual Canary Packet",
        summary="Manual-review packet only. It does not authorize, sign, transmit, route, or place any order.",
    )
    markdown_path = Path(output_root) / report_paths["markdown"]
    markdown_path.write_text(_manual_review_markdown(payload), encoding="utf-8")
    payload["report_paths"] = report_paths
    return payload


def _build_conflict_summary(
    *,
    readiness: dict[str, Any],
    capacity: dict[str, Any],
    pnl: dict[str, Any],
) -> dict[str, Any]:
    completed_marks = max(int(pnl.get("completed_mark_count") or readiness.get("completed_mark_count") or 0), 1)
    fake_net = float(pnl.get("fake_net_pnl") or readiness.get("fake_net_pnl") or 0.0)
    fake_gross = float(pnl.get("fake_gross_pnl") or readiness.get("fake_gross_pnl") or 0.0)
    execution_uncertainty_bps = max((fake_gross - fake_net) / completed_marks * 10000.0, 0.0)
    edge_bps = fake_net / completed_marks * 10000.0
    candidate = {
        "selected_strategy_id": readiness.get("active_strategy"),
        "strategy_signal": "buy" if fake_net > 0 else "none",
        "regime_signal": "buy" if readiness.get("baseline_beaten") is True else "none",
        "liquidity_filter": "pass" if capacity.get("status") == "CAPACITY_TINY_CANARY_PASSED" else "fail",
        "edge_bps": edge_bps,
        "execution_uncertainty_bps": execution_uncertainty_bps,
        "source_fresh": bool(readiness.get("completed_mark_count") and readiness.get("observations_count")),
    }
    payload = build_strategy_conflict_detector(candidate)
    return {
        "status": payload.get("status"),
        "veto_reasons": payload.get("veto_reasons", []),
        "candidate": {
            **candidate,
            "edge_bps": round(edge_bps, 8),
            "execution_uncertainty_bps": round(execution_uncertainty_bps, 8),
        },
    }


def _build_final_review_pack(
    *,
    readiness: dict[str, Any],
    repeatability: dict[str, Any],
    capacity: dict[str, Any],
    observer: dict[str, Any],
    intents: dict[str, Any],
    fills: dict[str, Any],
    pnl: dict[str, Any],
    reconciliation: dict[str, Any],
    conflict: dict[str, Any],
    fresh_repro: dict[str, Any],
) -> dict[str, Any]:
    return {
        "selected_strategy_lane": {
            "market_family": readiness.get("active_market_family", "crypto_spot"),
            "strategy": readiness.get("active_strategy", "multi_strategy_canary_grade_crypto_spot"),
            "venue": observer.get("venues_tested", readiness.get("venues_tested", [])),
            "source": observer.get("source"),
            "source_policy": observer.get("source_policy"),
        },
        "exact_assets": readiness.get("assets_tested", []),
        "sample_size": {
            "observations": readiness.get("observations_count", 0),
            "eligible_intents": readiness.get("eligible_intent_count", 0),
            "fake_fills": readiness.get("fake_fill_count", 0),
            "completed_marks": readiness.get("completed_mark_count", 0),
        },
        "fake_intents_fills_marks": {
            "intent_status": intents.get("status"),
            "fill_status": fills.get("status"),
            "pnl_status": pnl.get("status"),
            "no_transmit": True,
            "fake_money": True,
            "mark_source": "future_public_spot_price_after_entry_timestamp",
        },
        "fake_net_pnl_after_costs": {
            "fake_gross_pnl": pnl.get("fake_gross_pnl", readiness.get("fake_gross_pnl", 0.0)),
            "fake_net_pnl": pnl.get("fake_net_pnl", readiness.get("fake_net_pnl", 0.0)),
            "gross_profit": pnl.get("gross_profit"),
            "gross_loss": pnl.get("gross_loss"),
        },
        "baseline_placebo_comparison": {
            "baseline_beaten": readiness.get("baseline_beaten") is True,
            "baseline_pnl": repeatability.get("baseline_pnl", readiness.get("baseline_pnl")),
            "best_baseline_name": repeatability.get("best_baseline_name"),
            "placebo_beaten": readiness.get("placebo_beaten") is True,
            "placebo_pnl": repeatability.get("placebo_pnl", readiness.get("placebo_pnl")),
        },
        "gates": {
            "repeatability": repeatability.get("status"),
            "reconciliation": reconciliation.get("status"),
            "conflict": conflict.get("status"),
            "capacity": capacity.get("status"),
            "readiness": readiness.get("status"),
            "fresh_repro": fresh_repro.get("status", "FRESH_REPRO_MISSING"),
            "independent_fresh_worktree": fresh_repro.get("independent_clean_checkout_verified") is True,
        },
        "dominance_checks": {
            "one_trade_dominance": repeatability.get("one_trade_dominance"),
            "one_trade_dominance_cap": repeatability.get("one_trade_dominance_cap"),
            "one_window_dominance": repeatability.get("one_window_dominance"),
            "one_window_dominance_cap": repeatability.get("one_window_dominance_cap"),
            "by_window": repeatability.get("by_window", {}),
            "by_asset": repeatability.get("by_asset", {}),
        },
        "risk_envelope": {
            "tiny_manual_canary_only": True,
            "max_safe_notional": capacity.get("max_safe_notional"),
            "supported_size": "1_usd",
            "margin": False,
            "portfolio_margin_allowed": False,
            "cross_collateral_allowed": False,
            "leverage": False,
            "shorting": False,
            "futures_perps_options": False,
            "order_transmission_enabled": False,
            "portfolio_checks_must_remain_disabled": True,
        },
        "kill_switch_block_conditions": [
            "Block if any live/auth/order/signing/key/balance/portfolio flag becomes true or nonzero.",
            "Block if canary-grade readiness is not CANARY_GRADE_LIVE_SIM_PROFITABILITY_PROVEN.",
            "Block if fake net PnL is not positive after costs.",
            "Block if baseline or placebo is not beaten.",
            "Block if repeatability, reconciliation, conflict, or capacity status is not passed.",
            "Block if one-trade or one-window dominance reaches its cap.",
            "Block if any mark timestamp is not later than its entry timestamp.",
            "Block if the 1 USD tiny size is no longer capacity-supported by public data.",
            "Block if a human attempts to add credentials, signing, routing, or order transmission to this packet.",
        ],
        "what_could_still_fail_in_real_money": [
            "Public top-of-book liquidity can disappear before a human separately acts.",
            "Real venue fees, minimums, rejects, latency, and partial-fill behavior may differ from the fake model.",
            "Crypto prices can gap or mean-reversion can fail after the review packet is generated.",
            "Manual execution error can violate the tiny-only risk envelope.",
            "Operational controls can fail if a human bypasses the no-transmit boundary.",
        ],
        "human_only_arming_boundary": [
            "This repo packet is review-only and stops before credentials, signing, routing, or order creation.",
            "Any real-money action must be a separate human decision outside this no-transmit automation.",
            "QuantOS must remain live_trading_enabled=false and order_transmission_enabled=false.",
            "No automated process may convert this packet into an executable order.",
        ],
        "post_canary_reconciliation_checklist": [
            "Rerun .\\make.cmd canary-grade-live-sim-public-run after any separate human action.",
            "Confirm actual_order_count and actual_cancel_count remain zero inside QuantOS reports.",
            "Compare any separate human note against the packet timestamp, asset, tiny size, and kill conditions.",
            "Record realized/manual outcome separately; do not rewrite fake public-forward PnL as live PnL.",
            "Stop and investigate if reconciliation status is not CANARY_GRADE_RECONCILIATION_PASSED.",
        ],
        "rollback_abort_checklist": [
            "Abort immediately if any safety flag flips true or any counter becomes nonzero.",
            "Abort if public source, spread, depth, baseline, placebo, dominance, or capacity changes unfavorably.",
            "Abort if credentials, keys, signing, auth, portfolio, balance, or order endpoints enter the flow.",
            "Keep all live/order/auth flags false and rerun guard-live before any further review.",
            "Return to no-action monitoring with .\\make.cmd money-worthy-canary-grade-public-run.",
        ],
    }


def _build_manual_packet_gate(
    *,
    readiness: dict[str, Any],
    repeatability: dict[str, Any],
    capacity: dict[str, Any],
    pnl: dict[str, Any],
    reconciliation: dict[str, Any],
    conflict: dict[str, Any],
    fresh_repro: dict[str, Any],
    safety_reports: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    blockers: list[str] = []
    if readiness.get("status") != "CANARY_GRADE_LIVE_SIM_PROFITABILITY_PROVEN":
        blockers.append("CANARY_GRADE_READINESS_NOT_PROVEN")
    if repeatability.get("status") != "REPEATABILITY_PASSED":
        blockers.append("REPEATABILITY_NOT_PASSED")
    if capacity.get("status") != "CAPACITY_TINY_CANARY_PASSED":
        blockers.append("CAPACITY_TINY_CANARY_NOT_PASSED")
    if reconciliation.get("status") != "CANARY_GRADE_RECONCILIATION_PASSED":
        blockers.append("CANARY_GRADE_RECONCILIATION_NOT_PASSED")
    if int(reconciliation.get("reconciliation_failures") or 0) != 0:
        blockers.append("RECONCILIATION_FAILURES_PRESENT")
    if conflict.get("status") != "CONFLICT_DETECTOR_PASSED":
        blockers.append("CONFLICT_DETECTOR_NOT_PASSED")
    if float(readiness.get("fake_net_pnl") or 0.0) <= 0.0 or float(pnl.get("fake_net_pnl") or 0.0) <= 0.0:
        blockers.append("FAKE_NET_PNL_NOT_POSITIVE")
    if readiness.get("baseline_beaten") is not True:
        blockers.append("BASELINE_NOT_BEATEN")
    if readiness.get("placebo_beaten") is not True:
        blockers.append("PLACEBO_NOT_BEATEN")
    blockers.extend(_safety_blockers(safety_reports))

    fresh_repro_blocker = None
    independent_fresh_repro = (
        fresh_repro.get("status")
        in {"FRESH_REPRO_PASSED", "INDEPENDENT_FRESH_WORKTREE_PROOF_PASSED"}
        and fresh_repro.get("independent_clean_checkout_verified") is True
    )
    if not independent_fresh_repro:
        fresh_repro_blocker = "INDEPENDENT_FRESH_WORKTREE_PROOF_NOT_AVAILABLE"
        blockers.append(fresh_repro_blocker)

    blockers = list(dict.fromkeys(blockers))
    hard_blockers = [blocker for blocker in blockers if blocker != fresh_repro_blocker]
    if not blockers:
        status = "FIRST_TINY_MANUAL_CANARY_PACKET_READY"
    elif not hard_blockers and fresh_repro_blocker:
        status = "REVIEW_READY_NOT_CANARY_ARMABLE"
    else:
        status = "FIRST_TINY_MANUAL_CANARY_PACKET_BLOCKED"
    return {
        "status": status,
        "blockers": blockers,
        "review_ready": status in {"FIRST_TINY_MANUAL_CANARY_PACKET_READY", "REVIEW_READY_NOT_CANARY_ARMABLE"},
        "canary_armable": status == "FIRST_TINY_MANUAL_CANARY_PACKET_READY",
    }


def _safety_blockers(reports: dict[str, dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    expected_false = [
        "live_trading_enabled",
        "order_transmission_enabled",
        "authenticated_requests_enabled",
        "request_signing_enabled",
        "api_keys_loaded",
        "private_keys_loaded",
        "authenticated_endpoint_called",
        "checked_account_balance",
        "checked_portfolio",
    ]
    expected_zero = [
        "actual_order_count",
        "actual_cancel_count",
        "unsafe_action_attempts",
        "auth_key_order_attempts",
    ]
    for name, payload in reports.items():
        for key in expected_false:
            if payload.get(key) is True:
                blockers.append(f"UNSAFE_FLAG_TRUE:{name}:{key}")
        for key in expected_zero:
            if int(payload.get(key) or 0) != 0:
                blockers.append(f"UNSAFE_COUNTER_NONZERO:{name}:{key}")
        if payload.get("execution_authority") not in {None, "NONE"}:
            blockers.append(f"EXECUTION_AUTHORITY_NOT_NONE:{name}")
    return blockers


def _manual_review_markdown(payload: dict[str, Any]) -> str:
    pack = payload.get("final_review_pack", {})
    lines = [
        "# Canary-Grade First Tiny Manual Canary Review Pack",
        "",
        "Manual-review packet only. It does not authorize, sign, transmit, route, prepare, or place any order.",
        "",
        f"Status: {payload.get('status')}",
        f"Live trading enabled: {payload.get('live_trading_enabled')}",
        f"Execution authority: {payload.get('execution_authority')}",
        f"Order transmission enabled: {payload.get('order_transmission_enabled')}",
        f"Authenticated requests enabled: {payload.get('authenticated_requests_enabled')}",
        f"Request signing enabled: {payload.get('request_signing_enabled')}",
        "",
    ]
    section_map = [
        ("1. Selected Strategy/Lane", pack.get("selected_strategy_lane", {})),
        ("2. Exact Assets", pack.get("exact_assets", [])),
        ("3. Sample Size", pack.get("sample_size", {})),
        ("4. Fake Intents/Fills/Marks", pack.get("fake_intents_fills_marks", {})),
        ("5. Fake Net PnL After Costs", pack.get("fake_net_pnl_after_costs", {})),
        ("6. Baseline/Placebo Comparison", pack.get("baseline_placebo_comparison", {})),
        ("7. Repeatability/Reconciliation/Conflict/Capacity", pack.get("gates", {})),
        ("8. Dominance Checks", pack.get("dominance_checks", {})),
        ("9. Risk Envelope", pack.get("risk_envelope", {})),
        ("10. Exact Kill-Switch/Block Conditions", pack.get("kill_switch_block_conditions", [])),
        ("11. What Could Still Fail In Real Money", pack.get("what_could_still_fail_in_real_money", [])),
        ("12. Exact Human-Only Arming Boundary", pack.get("human_only_arming_boundary", [])),
        ("13. Post-Canary Reconciliation Checklist", pack.get("post_canary_reconciliation_checklist", [])),
        ("14. Rollback/Abort Checklist", pack.get("rollback_abort_checklist", [])),
    ]
    for title, value in section_map:
        lines.extend([f"## {title}", *_markdown_items(value), ""])
    lines.extend(["## Blockers", *_markdown_items(payload.get("blockers", []) or ["None"])])
    if payload.get("next_action"):
        lines.extend(["", "## Next Action", f"- {payload['next_action']}"])
    return "\n".join(lines).rstrip() + "\n"


def _markdown_items(value: Any) -> list[str]:
    if isinstance(value, dict):
        if not value:
            return ["- None"]
        return [f"- {key}: {item}" for key, item in value.items()]
    if isinstance(value, list):
        if not value:
            return ["- None"]
        return [f"- {item}" for item in value]
    return [f"- {value}"]
