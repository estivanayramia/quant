from __future__ import annotations

from typing import Any

from quant_os.research.strategy_factory.campaign_common import safe_payload

SUCCESS = "MONEY_WORTHY_CANARY_GRADE_PROFITABILITY_PROVEN"


def build_money_worthy_strategy_readiness(
    *,
    tournament: dict[str, Any] | None = None,
    overfit: dict[str, Any] | None = None,
    conflict: dict[str, Any] | None = None,
    repeatability: dict[str, Any] | None = None,
    capacity: dict[str, Any] | None = None,
    fresh_repro: dict[str, Any] | None = None,
) -> dict[str, Any]:
    tournament = tournament or {}
    overfit = overfit or {"status": "OVERFIT_GUARD_BLOCKED"}
    conflict = conflict or {"status": "CONFLICT_DETECTOR_VETOED"}
    repeatability = repeatability or {"status": "REPEATABILITY_BLOCKED"}
    capacity = capacity or {"status": "CAPACITY_BLOCKED"}
    fresh_repro = fresh_repro or {"status": "FRESH_REPRO_BLOCKED"}
    candidate = dict(tournament.get("current_best_candidate") or {})
    blockers = []
    if not candidate:
        blockers.append("NO_TOP_CANDIDATE")
    if float(candidate.get("fake_net_pnl", 0.0)) <= 0:
        blockers.append("FAKE_NET_PNL_NOT_POSITIVE")
    if overfit.get("status") != "OVERFIT_GUARD_PASSED":
        blockers.append("OVERFIT_GUARD_NOT_PASSED")
    if conflict.get("status") != "CONFLICT_DETECTOR_PASSED":
        blockers.append("CONFLICT_DETECTOR_NOT_PASSED")
    if repeatability.get("status") != "REPEATABILITY_PASSED":
        blockers.append("REPEATABILITY_NOT_PASSED")
    if capacity.get("status") != "CAPACITY_TINY_CANARY_PASSED":
        blockers.append("CAPACITY_TINY_CANARY_NOT_PASSED")
    if fresh_repro.get("status") != "FRESH_REPRO_PASSED":
        blockers.append("FRESH_WORKTREE_REPRO_NOT_PASSED")
    status = SUCCESS if not blockers else _blocked_status(blockers)
    if candidate:
        candidate["blockers"] = list(blockers)
        candidate["status"] = "MONEY_WORTHY_NOT_PROVEN" if blockers else SUCCESS
    return safe_payload(
        status=status,
        campaign_complete=status == SUCCESS,
        blockers=blockers,
        current_best_candidate=candidate,
        overfit_status=overfit.get("status"),
        conflict_status=conflict.get("status"),
        repeatability_status=repeatability.get("status"),
        capacity_status=capacity.get("status"),
        fresh_repro_status=fresh_repro.get("status"),
    )


def _blocked_status(blockers: list[str]) -> str:
    if "OVERFIT_GUARD_NOT_PASSED" in blockers:
        return "MONEY_WORTHY_BLOCKED_BY_OVERFIT"
    if "CONFLICT_DETECTOR_NOT_PASSED" in blockers:
        return "MONEY_WORTHY_NOT_PROVEN"
    if "REPEATABILITY_NOT_PASSED" in blockers:
        return "MONEY_WORTHY_BLOCKED_BY_REPEATABILITY"
    if "CAPACITY_TINY_CANARY_NOT_PASSED" in blockers:
        return "MONEY_WORTHY_BLOCKED_BY_CAPACITY"
    if "FRESH_WORKTREE_REPRO_NOT_PASSED" in blockers:
        return "MONEY_WORTHY_BLOCKED_BY_REPRODUCIBILITY"
    return "MONEY_WORTHY_NOT_PROVEN"
