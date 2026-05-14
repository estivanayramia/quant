from __future__ import annotations

from typing import Any

from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

ALLOWED_FETCH_MODES = {
    "LOCAL_CAPTURE_ONLY",
    "CACHED_HTML_ONLY",
    "PUBLIC_STATIC_ALLOWED",
    "PUBLIC_DYNAMIC_MANUAL_ONLY",
    "OFFICIAL_API_ONLY",
    "RSS_ALLOWED",
    "BLOCKED_BY_POLICY",
}

LOCAL_OR_CACHE_MODES = {"LOCAL_CAPTURE_ONLY", "CACHED_HTML_ONLY"}
NETWORK_MODES = {
    "PUBLIC_STATIC_ALLOWED",
    "PUBLIC_DYNAMIC_MANUAL_ONLY",
    "OFFICIAL_API_ONLY",
    "RSS_ALLOWED",
}


def evaluate_source_policy(
    source: dict[str, Any],
    *,
    manual_network_fetch_enabled: bool = False,
) -> dict[str, Any]:
    mode = str(source.get("allowed_fetch_mode") or "BLOCKED_BY_POLICY")
    blockers: list[str] = []

    if mode not in ALLOWED_FETCH_MODES:
        blockers.append("UNSAFE_OR_UNSUPPORTED_FETCH_MODE")
    if mode == "BLOCKED_BY_POLICY":
        blockers.append("BLOCKED_BY_SOURCE_POLICY")
    if bool(source.get("network_allowed_by_default")):
        blockers.append("NETWORK_DEFAULT_NOT_ALLOWED")
    if mode in NETWORK_MODES and not manual_network_fetch_enabled:
        blockers.append("MANUAL_NETWORK_FETCH_DISABLED")
    if mode in NETWORK_MODES and bool(source.get("requires_manual_approval", True)):
        blockers.append("MANUAL_REVIEW_REQUIRED")
    if str(source.get("safety_classification", "")).lower() == "blocked":
        blockers.append("BLOCKED_SAFETY_CLASSIFICATION")

    status = "BLOCKED" if blockers else "ALLOWED"
    return {
        "source_id": source.get("source_id", "unknown_source"),
        "source_type": source.get("source_type", "unknown"),
        "allowed_fetch_mode": mode,
        "policy_status": status,
        "policy_decision": "ALLOW_LOCAL_OR_CACHED" if status == "ALLOWED" else "REJECT",
        "blockers": sorted(set(blockers)),
        "network_fetch_attempted": False,
        "manual_network_fetch_enabled": manual_network_fetch_enabled,
        "requires_manual_approval": bool(source.get("requires_manual_approval", True)),
        "network_allowed_by_default": bool(source.get("network_allowed_by_default")),
        "expected_artifact_type": source.get("expected_artifact_type", "unknown"),
        "notes": source.get("notes", ""),
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "evidence_only": True,
    }


def summarize_source_policies(
    *,
    sources: list[dict[str, Any]],
    manual_network_fetch_enabled: bool = False,
) -> dict[str, Any]:
    evaluations = [
        evaluate_source_policy(
            source,
            manual_network_fetch_enabled=manual_network_fetch_enabled,
        )
        for source in sources
    ]
    allowed = [item for item in evaluations if item["policy_status"] == "ALLOWED"]
    blocked = [item for item in evaluations if item["policy_status"] == "BLOCKED"]
    return {
        "schema_version": "research_intake_source_policy_v1",
        "sequence": "35",
        "policy_status": "SOURCE_POLICY_EVALUATED_FAIL_CLOSED",
        "default_network_allowed": False,
        "manual_network_fetch_enabled": manual_network_fetch_enabled,
        "anti_bot_bypass_enabled": False,
        "allowed_source_count": len(allowed),
        "blocked_source_count": len(blocked),
        "allowed_source_ids": [item["source_id"] for item in allowed],
        "blocked_source_ids": [item["source_id"] for item in blocked],
        "sources": evaluations,
        "network_fetch_attempted": False,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }
