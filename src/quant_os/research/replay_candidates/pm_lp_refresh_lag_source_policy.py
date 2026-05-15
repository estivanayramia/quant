from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.research.replay_candidates.pm_lp_refresh_lag_schema import (
    CANDIDATE_ID,
    PmLpRefreshLagReplayEvent,
    load_pm_lp_refresh_lag_fixture_events,
)
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

SOURCE_POLICY_REPORT_ROOT = Path("reports/sequence47/source_policy")
READINESS_REPORT_ROOT = Path("reports/sequence47/candidate_readiness")

FINAL_READINESS_STATUSES = [
    "CANDIDATE_PACK_READY_FOR_DATA_ACQUISITION",
    "BLOCKED_BY_SOURCE_AVAILABILITY",
    "REJECTED_UNSAFE_COPY_TRADE_DEPENDENCY",
]


def build_pm_lp_refresh_lag_source_policy() -> dict[str, Any]:
    return {
        "schema_version": "pm_lp_refresh_lag_source_policy_v1",
        "sequence": "47",
        "candidate_id": CANDIDATE_ID,
        "policy_status": "PUBLIC_READ_ONLY_SOURCE_POLICY_DEFINED",
        "public_read_only_only": True,
        "network_capture_allowed_without_auth": True,
        "authenticated_api_allowed": False,
        "order_endpoints_allowed": False,
        "private_wallet_labeling_allowed": False,
        "social_post_to_trade_shortcut_allowed": False,
        "unsafe_dependency_flags": [],
        "allowed_sources": [
            _source(
                "public_clob_orderbook_snapshots",
                "Point-in-time public orderbook snapshots with best bid/ask and size.",
            ),
            _source(
                "public_trade_or_fill_events",
                "Public trade/fill event stream or archive if available without auth.",
            ),
            _source(
                "public_quote_refresh_timestamps",
                "Timestamped quote-change observations derived from public snapshots.",
            ),
            _source(
                "public_liquidity_reward_market_metadata",
                "Public metadata about liquidity/reward-market eligibility and incentives.",
            ),
            _source(
                "public_spot_directional_triggers",
                "Read-only spot price snapshots used only as trigger context.",
            ),
            _source(
                "public_resolution_labels",
                "Public final outcomes or resolution labels for scored replay only.",
            ),
        ],
        "blocked_sources": [
            _blocked("copy_trading", "Social or wallet-follow instructions are never data truth."),
            _blocked("wallet_mirroring", "Mirroring wallet behavior is outside this lane."),
            _blocked(
                "private_wallet_label_truth",
                "Private wallet labels cannot be treated as replay evidence.",
            ),
            _blocked(
                "authenticated_trading_api",
                "Authenticated trading surfaces are forbidden in Phase 47.",
            ),
            _blocked("order_endpoint", "Order placement and cancellation are forbidden."),
            _blocked("claimed_pnl_social_post", "Claimed profit and loss is not evidence."),
        ],
        "capture_plan": [
            "cache public CLOB/orderbook snapshots with provenance hashes",
            "cache public trade/fill events only if available without authentication",
            "derive quote refresh timestamps from public snapshot deltas",
            "join public spot triggers by timestamp without generating trade instructions",
            "label fill/no-fill realism only from replayable public data",
        ],
        "blockers_before_replay": [
            "PUBLIC_SOURCES_REQUIRED_NOT_ACQUIRED",
            "QUOTE_REFRESH_TIMESTAMPS_NOT_VERIFIED",
            "FILL_NO_FILL_REALISM_NOT_MODELED",
            "BASELINES_AND_PLACEBOS_NOT_RUN",
        ],
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def evaluate_pm_lp_refresh_lag_candidate_readiness(
    *,
    source_policy: dict[str, Any] | None = None,
    fixture_events: list[PmLpRefreshLagReplayEvent] | None = None,
) -> dict[str, Any]:
    policy = source_policy or build_pm_lp_refresh_lag_source_policy()
    unsafe_flags = set(policy.get("unsafe_dependency_flags", []))
    rejected = bool(unsafe_flags & {"copy_trading", "wallet_mirroring", "private_wallet_label_truth"})
    fixture_events = fixture_events or []
    schema_valid = all(event.candidate_id == CANDIDATE_ID for event in fixture_events)
    status = (
        "REJECTED_UNSAFE_COPY_TRADE_DEPENDENCY"
        if rejected
        else "CANDIDATE_PACK_READY_FOR_DATA_ACQUISITION"
        if schema_valid
        else "BLOCKED_BY_SOURCE_AVAILABILITY"
    )
    blockers = (
        ["REJECTED_UNSAFE_COPY_TRADE_DEPENDENCY"]
        if rejected
        else ["PUBLIC_SOURCES_REQUIRED_NOT_ACQUIRED"]
        if status == "CANDIDATE_PACK_READY_FOR_DATA_ACQUISITION"
        else ["FIXTURE_SCHEMA_INVALID"]
    )
    return {
        "schema_version": "pm_lp_refresh_lag_candidate_readiness_v1",
        "sequence": "47",
        "candidate_id": CANDIDATE_ID,
        "allowed_final_statuses": FINAL_READINESS_STATUSES,
        "candidate_readiness_status": status,
        "data_availability_status": "PUBLIC_SOURCES_REQUIRED_NOT_ACQUIRED",
        "fixture_event_count": len(fixture_events),
        "fixture_schema_valid": schema_valid,
        "rejected_unsafe_copy_trade_dependency": rejected,
        "unsafe_dependency_flags": sorted(unsafe_flags),
        "blockers": blockers,
        "source_policy": policy,
        "exact_next_command": (
            "python -m quant_os.cli research pm-lp-refresh-lag-source-policy"
            if rejected
            else "python -m quant_os.cli research pm-lp-refresh-lag-candidate-pack"
        ),
        "autonomy_milestones": {
            "phase46_preserved": "met",
            "candidate_pack": "ready_for_data_acquisition"
            if status == "CANDIDATE_PACK_READY_FOR_DATA_ACQUISITION"
            else "blocked",
            "public_source_acquisition": "blocked",
            "bounded_shadow_rehearsal": "blocked",
            "canary": "blocked",
            "live": "blocked",
        },
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_pm_lp_refresh_lag_source_policy_report(
    *,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    payload = build_pm_lp_refresh_lag_source_policy()
    payload["report_paths"] = _write_report(
        payload,
        output_root=output_root,
        report_root=SOURCE_POLICY_REPORT_ROOT,
        json_name="latest_source_policy.json",
        md_name="latest_source_policy.md",
        title="Sequence 47 PM LP Refresh-Lag Source Policy",
        status_key="policy_status",
    )
    return payload


def write_pm_lp_refresh_lag_candidate_readiness_report(
    *,
    fixture_path: str | Path | None = None,
    source_policy: dict[str, Any] | None = None,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    events = load_pm_lp_refresh_lag_fixture_events(fixture_path) if fixture_path else []
    payload = evaluate_pm_lp_refresh_lag_candidate_readiness(
        source_policy=source_policy,
        fixture_events=events,
    )
    payload["report_paths"] = _write_report(
        payload,
        output_root=output_root,
        report_root=READINESS_REPORT_ROOT,
        json_name="latest_candidate_readiness.json",
        md_name="latest_candidate_readiness.md",
        title="Sequence 47 PM LP Refresh-Lag Candidate Readiness",
        status_key="candidate_readiness_status",
    )
    return payload


def _source(source_type: str, description: str) -> dict[str, Any]:
    return {
        "source_type": source_type,
        "description": description,
        "auth_required": False,
        "wallet_required": False,
        "execution_authority": "NONE",
    }


def _blocked(source_type: str, reason: str) -> dict[str, str]:
    return {"source_type": source_type, "reason": reason}


def _write_report(
    payload: dict[str, Any],
    *,
    output_root: str | Path,
    report_root: Path,
    json_name: str,
    md_name: str,
    title: str,
    status_key: str,
) -> dict[str, str]:
    root = Path(output_root) / report_root
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / json_name
    md_path = root / md_name
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        f"# {title}",
        "",
        "Research-only public source policy. No live trading, wallet signing, order routing, order placement, or cancellation.",
        "",
        f"Status: {payload[status_key]}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        f"Execution authority: {payload['execution_authority']}",
        "",
        "## Blockers",
    ]
    lines.extend(f"- {item}" for item in payload.get("blockers", []) or ["None"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
