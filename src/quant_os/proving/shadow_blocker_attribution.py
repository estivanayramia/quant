from __future__ import annotations

from typing import Any

from quant_os.proving.shadow_proving_spec import SHADOW_PROVING_SAFETY

BLOCKER_DEFINITIONS = {
    "edge_weakness": {
        "source": "signal_edge",
        "group": "signal_edge_blockers",
        "fixability": "genuine_do_not_trade_blockers",
        "evidence": ["WEAK_EVIDENCE_BLOCKS_PROMOTION"],
    },
    "confidence_too_weak": {
        "source": "signal_edge",
        "group": "signal_edge_blockers",
        "fixability": "genuine_do_not_trade_blockers",
        "evidence": ["WEAK_SIGNAL_BLOCKS_SHADOW_AUTONOMY"],
    },
    "replay_input_insufficient": {
        "source": "data_replay",
        "group": "data_replay_blockers",
        "fixability": "fixable_by_better_data",
        "evidence": ["REPLAY_DESIGN_PARTIAL", "UNRESOLVED_REALISM_DISQUALIFIER"],
    },
    "spread_cost_burden": {
        "source": "data_replay",
        "group": "data_replay_blockers",
        "fixability": "fixable_by_better_data",
        "evidence": ["unearned_due_to_blocked_intents"],
    },
    "stale_book_risk": {
        "source": "data_replay",
        "group": "data_replay_blockers",
        "fixability": "fixable_by_better_data",
        "evidence": ["blocks_shadow_autonomy_until_more_depth"],
    },
    "fill_uncertainty": {
        "source": "data_replay",
        "group": "data_replay_blockers",
        "fixability": "fixable_by_better_data",
        "evidence": ["FILL_RATE_TOO_LOW"],
    },
    "risk_envelope": {
        "source": "risk_policy",
        "group": "risk_policy_blockers",
        "fixability": "genuine_do_not_trade_blockers",
        "evidence": ["RISK_BLOCKS_SHADOW_AUTONOMY", "RISK_BLOCKS_CANARY_CONSIDERATION"],
    },
    "realism_disqualifier": {
        "source": "data_replay",
        "group": "data_replay_blockers",
        "fixability": "fixable_by_better_data",
        "evidence": ["UNRESOLVED_REALISM_DISQUALIFIER"],
    },
    "sample_too_thin": {
        "source": "artifact_fixture",
        "group": "fixture_artifact_blockers",
        "fixability": "fixable_by_better_data",
        "evidence": ["SHADOW_SAMPLE_TOO_THIN", "SHADOW_WINDOW_SAMPLE_TOO_THIN"],
    },
}


def attribute_shadow_blockers(*, shadow_windows: dict[str, Any]) -> dict[str, Any]:
    evidence_tokens = _evidence_tokens(shadow_windows)
    blocker_sources = {
        name: _source_record(name=name, definition=definition, tokens=evidence_tokens)
        for name, definition in BLOCKER_DEFINITIONS.items()
    }
    return {
        "schema_version": "shadow_blocker_attribution_v1",
        "sequence": "33",
        "blocker_attribution_status": "BLOCKERS_UNDERSTOOD_BUT_STILL_ACTIVE",
        "blocker_sources": blocker_sources,
        "blocker_groups": _groups(blocker_sources),
        "fixability": _fixability(blocker_sources),
        "observed_facts": [
            "The current shadow sample contains fixture evidence and synthetic stress windows.",
            "Synthetic windows are diagnostic only and do not prove tradable edge.",
        ],
        "diagnosis": (
            "Current blocks are a mix of weak signal, insufficient replay realism, "
            "fill uncertainty, and fail-closed risk policy."
        ),
        **SHADOW_PROVING_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _source_record(
    *,
    name: str,
    definition: dict[str, Any],
    tokens: set[str],
) -> dict[str, Any]:
    observed = sorted(token for token in definition["evidence"] if token in tokens)
    active = bool(observed) or name in {
        "spread_cost_burden",
        "stale_book_risk",
        "fill_uncertainty",
    }
    return {
        "active": active,
        "source": definition["source"],
        "group": definition["group"],
        "fixability": definition["fixability"],
        "observed_evidence": observed,
        "fixable_by_better_data_or_replay": definition["fixability"]
        == "fixable_by_better_data",
        "genuine_do_not_trade": definition["fixability"]
        == "genuine_do_not_trade_blockers",
    }


def _evidence_tokens(shadow_windows: dict[str, Any]) -> set[str]:
    tokens = set()
    for window in shadow_windows["windows"]:
        tokens.update(str(item) for item in window.get("blockers", []))
        tokens.update(str(item) for item in window.get("proving_blockers", []))
        metrics = window.get("metrics", {})
        tokens.update(str(value) for value in metrics.values())
    return tokens


def _groups(blocker_sources: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    groups = {
        "signal_edge_blockers": [],
        "data_replay_blockers": [],
        "risk_policy_blockers": [],
        "fixture_artifact_blockers": [],
    }
    for name, record in blocker_sources.items():
        if record["active"]:
            groups[record["group"]].append(name)
    return groups


def _fixability(blocker_sources: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    fixability = {
        "fixable_by_better_data": [],
        "genuine_do_not_trade_blockers": [],
    }
    for name, record in blocker_sources.items():
        if record["active"]:
            fixability[record["fixability"]].append(name)
    return fixability
