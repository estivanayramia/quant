from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.research.lane_selection.paper_profit_lane_models import (
    LANE_STATUSES,
    build_default_lane_universe,
    rank_paper_profit_lanes,
)
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

REPORT_ROOT = Path("reports/paper_profit_discovery/lane_tournament")


def build_paper_profit_lane_tournament_report() -> dict[str, Any]:
    ranked = rank_paper_profit_lanes(build_default_lane_universe())
    selected = next((lane for lane in ranked if lane.status.startswith("PROMOTE_TO_")), ranked[0])
    return {
        "schema_version": "paper_profit_lane_tournament_v1",
        "status": "LANE_TOURNAMENT_COMPLETE",
        "allowed_statuses": LANE_STATUSES,
        "selected_lane_id": selected.lane_id,
        "selected_lane_status": selected.status,
        "selected_lane_score": selected.total_score,
        "selected_lane": selected.to_report_dict(),
        "lane_count": len(ranked),
        "candidate_lanes": [lane.to_report_dict() for lane in ranked],
        "ranking_rules": [
            "Rank deterministic path-to-proof, not expected profit.",
            "Never promote lanes with auth, wallet, order, cancellation, copy-trade, leverage, margin, futures, options, or source-unavailable blockers.",
            "Prefer public data, replayability, baselines, placebos, cost/fill realism, and low source ambiguity.",
        ],
        "profitability_claimed": False,
        "paper_only": True,
        "ci_network_dependency": False,
        "evidence_only": True,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
    }


def write_paper_profit_lane_tournament_report(
    *, output_root: str | Path = "."
) -> dict[str, Any]:
    payload = build_paper_profit_lane_tournament_report()
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_lane_tournament.json"
    md_path = root / "latest_lane_tournament.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Paper-Profit Lane Tournament",
        "",
        "Deterministic path-to-proof ranking. No profit claim and no execution authority.",
        "",
        f"Status: {payload['status']}",
        f"Selected lane: {payload['selected_lane_id']}",
        f"Selected lane status: {payload['selected_lane_status']}",
        f"Selected lane score: {payload['selected_lane_score']}",
        f"Execution authority: {payload['execution_authority']}",
        "",
        "## Ranked Lanes",
    ]
    lines.extend(
        "- {lane_id}: {status} (score {score}) - {reason}".format(
            lane_id=lane["lane_id"],
            status=lane["status"],
            score=lane["total_score"],
            reason=lane["status_reason"],
        )
        for lane in payload["candidate_lanes"]
    )
    lines.extend(["", "## Ranking Rules"])
    lines.extend(f"- {rule}" for rule in payload["ranking_rules"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
