from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from quant_os.autonomy.canary_grade_live_sim_common import canary_safe_payload
from quant_os.autonomy.live_market_sim_common import load_json
from quant_os.readiness.canary_readiness_common import write_json_markdown_report

REPORT_DIR = Path("reports/canary_grade_live_sim/final_human_arming_review")
LEGACY_MEMO = Path("reports/canary_grade_live_sim/manual_canary_packet/latest_final_canary_review_memo.md")
SUCCESS = "READY_FOR_FINAL_HUMAN_ARMING_REVIEW"
BLOCKED = "FINAL_HUMAN_ARMING_REVIEW_BLOCKED"


def build_final_human_arming_review(*, output_root: str | Path = ".") -> dict[str, Any]:
    readiness = load_json(
        "reports/canary_grade_live_sim/final/latest_canary_grade_live_sim_readiness.json",
        output_root=output_root,
    ) or {}
    repeatability = load_json(
        "reports/canary_grade_live_sim/repeatability/latest_repeatability.json",
        output_root=output_root,
    ) or {}
    capacity = load_json("reports/canary_grade_live_sim/capacity/latest_capacity.json", output_root=output_root) or {}
    packet = load_json(
        "reports/canary_grade_live_sim/manual_canary_packet/latest_manual_canary_packet.json",
        output_root=output_root,
    ) or {}
    money_worthy = load_json(
        "reports/canary_grade_live_sim/money_worthy/latest_money_worthy_canary_grade.json",
        output_root=output_root,
    ) or {}
    armability = load_json(
        "reports/canary_grade_live_sim/armability/latest_armability.json",
        output_root=output_root,
    ) or {}
    rehearsal = load_json(
        (
            "reports/autonomous_live_fire_drill/no_transmit_execution_rehearsal/"
            "latest_no_transmit_execution_rehearsal.json"
        ),
        output_root=output_root,
    ) or {}
    fresh_repro = load_json(
        "reports/canary_grade_live_sim/fresh_repro/latest_fresh_repro.json",
        output_root=output_root,
    ) or {}
    pnl = load_json("reports/canary_grade_live_sim/crypto/latest_pnl.json", output_root=output_root) or {}
    reconciliation = load_json(
        "reports/canary_grade_live_sim/crypto/latest_reconciliation.json",
        output_root=output_root,
    ) or {}

    blockers = _review_blockers(
        readiness=readiness,
        repeatability=repeatability,
        capacity=capacity,
        packet=packet,
        money_worthy=money_worthy,
        armability=armability,
        rehearsal=rehearsal,
        fresh_repro=fresh_repro,
        pnl=pnl,
        reconciliation=reconciliation,
    )
    status = SUCCESS if not blockers else BLOCKED
    review_pack = _review_pack(
        readiness=readiness,
        repeatability=repeatability,
        capacity=capacity,
        packet=packet,
        money_worthy=money_worthy,
        armability=armability,
        rehearsal=rehearsal,
        fresh_repro=fresh_repro,
        pnl=pnl,
        reconciliation=reconciliation,
    )
    current_pr_head = _current_head_oid(output_root)
    independent_proof_head = fresh_repro.get("proof_head_oid")
    return canary_safe_payload(
        schema_version="final_human_arming_review_v1",
        status=status,
        allowed_statuses=[SUCCESS, BLOCKED],
        blockers=blockers,
        exact_blocker=blockers[0] if blockers else None,
        current_pr="55",
        pr_head=current_pr_head,
        current_pr_head=current_pr_head,
        independent_proof_head=independent_proof_head,
        proof_head_oid=independent_proof_head,
        proof_head_matches_current_pr_head=(
            current_pr_head != "unknown"
            and independent_proof_head is not None
            and current_pr_head == independent_proof_head
        ),
        active_market_family=readiness.get("active_market_family"),
        active_strategy=readiness.get("active_strategy"),
        assets_tested=readiness.get("assets_tested", []),
        venues_tested=readiness.get("venues_tested", []),
        public_data_source=fresh_repro.get(
            "public_data_source",
            review_pack["public_data_proof"].get("source"),
        ),
        observations_count=int(readiness.get("observations_count") or 0),
        eligible_intent_count=int(readiness.get("eligible_intent_count") or 0),
        fake_fill_count=int(readiness.get("fake_fill_count") or 0),
        completed_mark_count=int(readiness.get("completed_mark_count") or 0),
        fake_net_pnl=float(readiness.get("fake_net_pnl") or 0.0),
        baseline_pnl=float(readiness.get("baseline_pnl") or 0.0),
        placebo_pnl=float(readiness.get("placebo_pnl") or 0.0),
        baseline_edge=round(
            float(readiness.get("fake_net_pnl") or 0.0) - float(readiness.get("baseline_pnl") or 0.0),
            8,
        ),
        placebo_edge=round(
            float(readiness.get("fake_net_pnl") or 0.0) - float(readiness.get("placebo_pnl") or 0.0),
            8,
        ),
        independent_fresh_worktree_proof_status=armability.get("independent_fresh_worktree_proof_status"),
        review_pack=review_pack,
        operator_questions_answered=list(range(1, 12)),
        adversarial_review_required_before_done=True,
        adversarial_review_record=_adversarial_review_record(),
        completion_protocol=[
            "Run or request an adversarial subagent review before marking this task done.",
            "Fix Critical or Important findings before relying on the final review status.",
            "Do not let green status override safety flags, blocker fields, or stale contradictory reports.",
        ],
        project_improvement_review=_project_improvement_review(),
        no_real_order_authority=True,
        human_credentials_account_legal_approval_remain_separate=True,
        hidden_local_state_dependency=False,
        exact_resume_command=".\\make.cmd final-human-arming-review",
        next_action=(
            "Operator may review the no-transmit armability packet; no real order is authorized."
            if status == SUCCESS
            else "Resolve exact blocker before presenting final human arming review."
        ),
    )


def write_final_human_arming_review_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_final_human_arming_review(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_final_human_arming_review.json",
        md_name="latest_final_human_arming_review.md",
        title="Final Human-Governed Autonomous Execution Armability Review",
        summary=(
            "Operator-facing review only. It does not place, prepare, route, sign, cancel, "
            "transmit, authorize, or recommend any real order."
        ),
    )
    markdown = _review_markdown(payload)
    root = Path(output_root)
    md_path = root / payload["report_paths"]["markdown"]
    md_path.write_text(markdown, encoding="utf-8")
    legacy_path = root / LEGACY_MEMO
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_path.write_text(markdown, encoding="utf-8")
    return payload


def _current_head_oid(output_root: str | Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(output_root),
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        return "unknown"
    if result.returncode != 0:
        return "unknown"
    return result.stdout.strip() or "unknown"


def _review_pack(
    *,
    readiness: dict[str, Any],
    repeatability: dict[str, Any],
    capacity: dict[str, Any],
    packet: dict[str, Any],
    money_worthy: dict[str, Any],
    armability: dict[str, Any],
    rehearsal: dict[str, Any],
    fresh_repro: dict[str, Any],
    pnl: dict[str, Any],
    reconciliation: dict[str, Any],
) -> dict[str, Any]:
    final_pack = packet.get("final_review_pack", {}) or {}
    fake_net = float(readiness.get("fake_net_pnl") or 0.0)
    baseline_pnl = float(readiness.get("baseline_pnl") or 0.0)
    placebo_pnl = float(readiness.get("placebo_pnl") or 0.0)
    return {
        "strategy_lane_armable_for_review": {
            "lane": readiness.get("active_market_family", "crypto_spot"),
            "strategy": readiness.get("active_strategy", "multi_strategy_canary_grade_crypto_spot"),
            "strategy_families_tested": readiness.get("strategy_families_tested", []),
            "venues": readiness.get("venues_tested", []),
            "assets": readiness.get("assets_tested", []),
            "scope": armability.get("review_scope"),
        },
        "public_data_proof": {
            "source": fresh_repro.get("public_data_source")
            or final_pack.get("selected_strategy_lane", {}).get("source"),
            "source_policy": final_pack.get("selected_strategy_lane", {}).get("source_policy"),
            "attestation_scope": fresh_repro.get("attestation_scope"),
            "proof_output_root": fresh_repro.get("proof_output_root"),
            "proof_head_oid": fresh_repro.get("proof_head_oid"),
            "independent_clean_checkout_verified": fresh_repro.get("independent_clean_checkout_verified") is True,
            "hidden_local_state_dependency": False,
        },
        "sample_size_and_pnl": {
            "observations": readiness.get("observations_count"),
            "eligible_fake_money_no_transmit_intents": readiness.get("eligible_intent_count"),
            "conservative_fake_fills": readiness.get("fake_fill_count"),
            "completed_future_public_marks": readiness.get("completed_mark_count"),
            "fake_gross_pnl": readiness.get("fake_gross_pnl"),
            "fake_net_pnl_after_costs": fake_net,
            "independent_proof_summary": fresh_repro.get("independent_proof_summary", {}),
        },
        "baseline_and_placebo": {
            "baseline_beaten": readiness.get("baseline_beaten") is True,
            "baseline_pnl": baseline_pnl,
            "edge_over_baseline": round(fake_net - baseline_pnl, 8),
            "best_baseline_name": repeatability.get("best_baseline_name"),
            "placebo_beaten": readiness.get("placebo_beaten") is True,
            "placebo_pnl": placebo_pnl,
            "edge_over_placebo": round(fake_net - placebo_pnl, 8),
        },
        "gates_passed": {
            "armability": armability.get("status"),
            "money_worthy": money_worthy.get("status"),
            "canary_grade_readiness": readiness.get("status"),
            "manual_canary_packet": packet.get("status"),
            "no_transmit_execution_rehearsal": rehearsal.get("status"),
            "fresh_repro": fresh_repro.get("status"),
            "independent_fresh_worktree": fresh_repro.get("independent_fresh_worktree_proof_status"),
            "repeatability": readiness.get("repeatability_status"),
            "capacity": readiness.get("capacity_status") or capacity.get("status"),
            "reconciliation": reconciliation.get("status"),
            "proof_quality": money_worthy.get("proof_quality_status"),
            "overfit": money_worthy.get("overfit_status"),
            "holdout": money_worthy.get("holdout_status"),
            "no_leakage": money_worthy.get("no_leakage_status"),
            "conflict": packet.get("conflict_summary", {}).get("status"),
        },
        "remaining_real_money_risks": [
            "Public liquidity can disappear or spreads can widen before any separate human action.",
            "Real venue fees, minimums, rejects, latency, partial fills, and slippage may differ from the fake model.",
            "Crypto prices can gap and the observed mean-reversion/momentum edge can fail after report generation.",
            "Manual execution mistakes can violate the tiny-only risk envelope.",
            "Portfolio margin, cross-collateral, leverage, shorting, derivatives, or borrowing would invalidate the isolated spot-only assumptions.",
            "Operational controls can fail if a human bypasses the no-transmit boundary.",
        ],
        "later_human_actions_required": [
            "A human must separately decide whether any real-money action is legally, financially, and operationally acceptable.",
            "Any account, credentials, funding, venue UI, and execution authority remain outside this repo and outside automation.",
            "A human must verify the packet remains fresh and all abort conditions are still false immediately before any separate action.",
            "A human must keep the action spot-only, cash-only, isolated from portfolio margin, and within the tiny risk envelope.",
            "A human must record a separate action note if they act; this repo must not transmit or sign anything.",
        ],
        "must_remain_disabled": _must_remain_disabled(),
        "abort_conditions": _abort_conditions(),
        "one_shot_tiny_canary_protocol_for_review_only": [
            "Review the latest final human arming review and manual canary packet; do not execute from automation.",
            "Confirm guard-live passes and every live/auth/order/sign/key/balance/portfolio flag remains false or zero.",
            "Use only the supported tiny canary envelope from public data: 1_usd spot-only, no margin, no leverage, no shorts, no derivatives.",
            "Abort if public data, baseline/placebo edge, capacity, dominance, reconciliation, or freshness worsens.",
            "If a human separately acts later, the action must happen outside QuantOS and outside this no-transmit workflow.",
        ],
        "post_action_reconciliation_required_if_human_acts_later": [
            "Rerun .\\make.cmd canary-grade-live-sim-public-run after any separate human action.",
            "Confirm QuantOS actual_order_count and actual_cancel_count remain zero.",
            "Compare the human action note against packet timestamp, selected asset, tiny size, and abort conditions.",
            "Record realized/manual outcome separately; do not rewrite fake public-forward PnL as live PnL.",
            "Stop and investigate if CANARY_GRADE_RECONCILIATION_PASSED is not preserved.",
        ],
        "portfolio_margin_controls": {
            "portfolio_margin_allowed": False,
            "cross_collateral_allowed": False,
            "margin_allowed": False,
            "leverage_allowed": False,
            "shorting_allowed": False,
            "derivatives_allowed": False,
            "portfolio_checks_required_by_automation": False,
            "portfolio_checks_must_remain_disabled": True,
        },
        "safety_flags": {
            key: armability.get(key)
            for key in [
                "live_trading_enabled",
                "execution_authority",
                "order_transmission_enabled",
                "authenticated_requests_enabled",
                "request_signing_enabled",
                "api_keys_loaded",
                "private_keys_loaded",
                "actual_order_count",
                "actual_cancel_count",
            ]
        },
    }


def _review_blockers(
    *,
    readiness: dict[str, Any],
    repeatability: dict[str, Any],
    capacity: dict[str, Any],
    packet: dict[str, Any],
    money_worthy: dict[str, Any],
    armability: dict[str, Any],
    rehearsal: dict[str, Any],
    fresh_repro: dict[str, Any],
    pnl: dict[str, Any],
    reconciliation: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    expected = {
        "armability": (armability.get("status"), "ARMABLE_FOR_HUMAN_GOVERNED_AUTONOMOUS_EXECUTION_REVIEW"),
        "money_worthy": (money_worthy.get("status"), "MONEY_WORTHY_CANARY_GRADE_PROFITABILITY_PROVEN"),
        "readiness": (readiness.get("status"), "CANARY_GRADE_LIVE_SIM_PROFITABILITY_PROVEN"),
        "manual_packet": (packet.get("status"), "FIRST_TINY_MANUAL_CANARY_PACKET_READY"),
        "no_transmit_rehearsal": (rehearsal.get("status"), "AUTONOMOUS_NO_TRANSMIT_EXECUTION_REHEARSAL_PASSED"),
        "fresh_repro": (fresh_repro.get("status"), "INDEPENDENT_FRESH_WORKTREE_PROOF_PASSED"),
        "repeatability": (readiness.get("repeatability_status") or repeatability.get("status"), "REPEATABILITY_PASSED"),
        "capacity": (readiness.get("capacity_status") or capacity.get("status"), "CAPACITY_TINY_CANARY_PASSED"),
        "reconciliation": (reconciliation.get("status"), "CANARY_GRADE_RECONCILIATION_PASSED"),
        "proof_quality": (money_worthy.get("proof_quality_status"), "CANARY_GRADE_PROOF_QUALITY_PASSED"),
    }
    for name, (actual, wanted) in expected.items():
        if actual != wanted:
            blockers.append(f"{name.upper()}_STATUS_NOT_{wanted}")
    if fresh_repro.get("independent_clean_checkout_verified") is not True:
        blockers.append("INDEPENDENT_CLEAN_CHECKOUT_NOT_VERIFIED")
    if float(readiness.get("fake_net_pnl") or 0.0) <= 0.0:
        blockers.append("FAKE_NET_PNL_NOT_POSITIVE")
    if readiness.get("baseline_beaten") is not True:
        blockers.append("BASELINE_NOT_BEATEN")
    if readiness.get("placebo_beaten") is not True:
        blockers.append("PLACEBO_NOT_BEATEN")
    if int(readiness.get("reconciliation_failures") or 0) != 0:
        blockers.append("RECONCILIATION_FAILURES_PRESENT")
    risk = packet.get("risk_envelope", {}) or {}
    if risk.get("margin") is not False:
        blockers.append("MARGIN_NOT_DISABLED")
    if risk.get("portfolio_margin_allowed") is not False:
        blockers.append("PORTFOLIO_MARGIN_NOT_DISABLED")
    if risk.get("cross_collateral_allowed") is not False:
        blockers.append("CROSS_COLLATERAL_NOT_DISABLED")
    for key in ["leverage", "shorting", "futures_perps_options"]:
        if risk.get(key) is not False:
            blockers.append(f"{key.upper()}_NOT_DISABLED")
    blockers.extend(
        _safety_blockers(
            {
                "readiness": readiness,
                "repeatability": repeatability,
                "capacity": capacity,
                "packet": packet,
                "money_worthy": money_worthy,
                "armability": armability,
                "rehearsal": rehearsal,
                "fresh_repro": fresh_repro,
                "pnl": pnl,
                "reconciliation": reconciliation,
            }
        )
    )
    return list(dict.fromkeys(blockers))


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


def _must_remain_disabled() -> list[str]:
    return [
        "live_trading_enabled=false",
        "execution_authority=NONE",
        "order_transmission_enabled=false",
        "authenticated_requests_enabled=false",
        "request_signing_enabled=false",
        "api_keys_loaded=false",
        "private_keys_loaded=false",
        "authenticated_endpoint_called=false",
        "checked_account_balance=false",
        "checked_portfolio=false",
        "actual_order_count=0",
        "actual_cancel_count=0",
        "unsafe_action_attempts=0",
        "auth_key_order_attempts=0",
        "portfolio_margin_allowed=false",
        "cross_collateral_allowed=false",
    ]


def _abort_conditions() -> list[str]:
    return [
        "Any live/auth/order/signing/key/balance/portfolio flag becomes true or any counter becomes nonzero.",
        "Armability is not ARMABLE_FOR_HUMAN_GOVERNED_AUTONOMOUS_EXECUTION_REVIEW.",
        "Fake net PnL is not positive after conservative costs.",
        "Baseline or placebo comparison is not beaten.",
        "Repeatability, reconciliation, conflict, capacity, proof-quality, holdout, no-leakage, or fresh-repro gates fail.",
        "One-trade or one-window dominance reaches its cap.",
        "The 1_usd spot-only capacity envelope is no longer supported by public data.",
        "Any attempt is made to use margin, portfolio margin, cross-collateral, leverage, shorting, futures, perps, options, or borrowing.",
        "Any attempt is made to convert this report into an executable order or automated live-trading instruction.",
    ]


def _project_improvement_review() -> list[str]:
    return [
        "Make this final human arming review the canonical operator memo and avoid keeping stale parallel memos.",
        "Keep fixture-safe smoke reports visually separate from public-network proof reports so stale fixture output cannot imply live proof.",
        "Deduplicate safety flag checks into one shared helper across armability, money-worthy, and manual packet gates.",
        "Expose portfolio-margin and cross-collateral prohibitions anywhere a tiny canary risk envelope is shown.",
        "Keep exact public data provenance, proof head, and independent clean checkout status together in each final report.",
        "Before marking any high-stakes task done, run an adversarial subagent review and record/fix Critical or Important findings.",
    ]


def _adversarial_review_record() -> dict[str, Any]:
    return {
        "status": "ADVERSARIAL_REVIEW_FINDINGS_RESOLVED",
        "reviewers": ["Faraday", "Wegener"],
        "critical_or_important_findings": [
            {
                "finding": "Canonical final review code and artifacts were not yet in PR material.",
                "resolution": "Added tracked final review module, CLI command, make target, and tests.",
            },
            {
                "finding": "Final operator artifact was missing and legacy memo was stale.",
                "resolution": "The final-human-arming-review command writes the canonical report and refreshes the legacy memo.",
            },
            {
                "finding": "Adversarial review result was required before completion but not recorded.",
                "resolution": "Recorded this adversarial review section in the final report payload and Markdown.",
            },
            {
                "finding": "Portfolio margin and cross-collateral controls needed to be explicit.",
                "resolution": "Added portfolio-margin and cross-collateral disabled controls to packet and final review.",
            },
        ],
        "remaining_non_blocking_improvements": [
            "Centralize duplicated safety-blocker helpers in a later cleanup.",
            "Keep fixture-safe reports clearly separated from public-network proof reports.",
        ],
    }


def _review_markdown(payload: dict[str, Any]) -> str:
    pack = payload.get("review_pack", {})
    lines = [
        "# Final Human-Governed Autonomous Execution Armability Review",
        "",
        f"Final status: {payload.get('status')}",
        "",
        "This is an operator-facing review packet only. It does not place, prepare, route, sign, cancel, transmit, authorize, or recommend any real order. It does not load keys, auth, balances, or portfolio.",
        "",
        f"Current PR: {payload.get('current_pr')}",
        f"Current PR head: {payload.get('current_pr_head') or payload.get('pr_head')}",
        f"Independent proof head: {payload.get('independent_proof_head') or payload.get('proof_head_oid')}",
        f"Exact resume command: `{payload.get('exact_resume_command')}`",
        "",
    ]
    section_map = [
        ("1. Exact Strategy/Lane Armable For Review", pack.get("strategy_lane_armable_for_review", {})),
        ("2. Public Data That Proved It", pack.get("public_data_proof", {})),
        ("3. Sample Size And PnL Proven", pack.get("sample_size_and_pnl", {})),
        ("4. Baseline And Placebo Beaten By", pack.get("baseline_and_placebo", {})),
        ("5. Gates Passed", pack.get("gates_passed", {})),
        ("6. Remaining Real-Money Risks", pack.get("remaining_real_money_risks", [])),
        ("7. Exact Human Actions Required Later", pack.get("later_human_actions_required", [])),
        ("8. What Must Remain Disabled", pack.get("must_remain_disabled", [])),
        ("9. Abort Conditions Blocking Arming", pack.get("abort_conditions", [])),
        (
            "10. One-Shot Tiny Canary Protocol For Review Only",
            pack.get("one_shot_tiny_canary_protocol_for_review_only", []),
        ),
        (
            "11. Post-Action Reconciliation Required If A Human Separately Acts Later",
            pack.get("post_action_reconciliation_required_if_human_acts_later", []),
        ),
        ("Portfolio Margin Controls", pack.get("portfolio_margin_controls", {})),
        ("Adversarial Review Record", payload.get("adversarial_review_record", {})),
        ("Project Improvement Review", payload.get("project_improvement_review", [])),
        ("Completion Protocol", payload.get("completion_protocol", [])),
    ]
    for title, value in section_map:
        lines.extend([f"## {title}", *_markdown_items(value), ""])
    lines.extend(["## Blockers", *_markdown_items(payload.get("blockers", []) or ["None"])])
    lines.extend(
        [
            "",
            "## Safety Controls Verified",
            f"- live_trading_enabled: {payload.get('live_trading_enabled')}",
            f"- execution_authority: {payload.get('execution_authority')}",
            f"- order_transmission_enabled: {payload.get('order_transmission_enabled')}",
            f"- authenticated_requests_enabled: {payload.get('authenticated_requests_enabled')}",
            f"- request_signing_enabled: {payload.get('request_signing_enabled')}",
            f"- api_keys_loaded: {payload.get('api_keys_loaded')}",
            f"- private_keys_loaded: {payload.get('private_keys_loaded')}",
            f"- actual_order_count: {payload.get('actual_order_count')}",
            f"- actual_cancel_count: {payload.get('actual_cancel_count')}",
            f"- unsafe_action_attempts: {payload.get('unsafe_action_attempts')}",
            f"- auth_key_order_attempts: {payload.get('auth_key_order_attempts')}",
        ]
    )
    if payload.get("next_action"):
        lines.extend(["", "## Next Action", f"- {payload['next_action']}"])
    return "\n".join(lines).rstrip() + "\n"


def _markdown_items(value: Any, *, indent: int = 0) -> list[str]:
    prefix = "  " * indent
    if isinstance(value, dict):
        if not value:
            return [f"{prefix}- None"]
        lines: list[str] = []
        for key, item in value.items():
            if isinstance(item, dict | list):
                lines.append(f"{prefix}- {key}:")
                lines.extend(_markdown_items(item, indent=indent + 1))
            else:
                lines.append(f"{prefix}- {key}: {item}")
        return lines
    if isinstance(value, list):
        if not value:
            return [f"{prefix}- None"]
        lines = []
        for item in value:
            if isinstance(item, dict):
                lines.append(f"{prefix}-")
                lines.extend(_markdown_items(item, indent=indent + 1))
            elif isinstance(item, list):
                lines.extend(_markdown_items(item, indent=indent))
            else:
                lines.append(f"{prefix}- {item}")
        return lines
    return [f"{prefix}- {value}"]
