from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quant_os.research.evidence_quality import latest_evidence_adjustment
from quant_os.research.overfit_checks import run_overfit_checks
from quant_os.research.regime_tests import run_regime_tests
from quant_os.research.research_report import run_strategy_research
from quant_os.research.walk_forward import run_walk_forward_validation


def build_strategy_leaderboard(symbol: str = "SPY") -> dict[str, Any]:
    research = run_strategy_research(symbol)
    overfit = run_overfit_checks(symbol)
    walk_forward = run_walk_forward_validation(symbol)
    regime = run_regime_tests(symbol)
    evidence = latest_evidence_adjustment()
    placebo_return = float(
        research["results"]["random_placebo"]["metrics"].get("total_return", 0.0)
    )
    entries = []
    for strategy_id, result in research["results"].items():
        metrics = result["metrics"]
        trades = int(metrics.get("number_of_trades", 0))
        total_return = float(metrics.get("total_return", 0.0))
        max_drawdown = abs(float(metrics.get("max_drawdown", 0.0)))
        placebo_margin = total_return - placebo_return
        trade_score = min(trades / 20, 1.0) * 0.25
        stress_penalty = 0.15 if f"LOW_TRADE_COUNT:{strategy_id}" in overfit["warnings"] else 0.0
        conservative_score = (
            total_return - (max_drawdown * 2.0) + trade_score + placebo_margin - stress_penalty
        )
        conservative_score -= float(evidence["evidence_penalty"])
        if strategy_id == "no_trade":
            status = "REJECTED"
            conservative_score = -1.0
        elif trades < 5:
            status = "NOT_ENOUGH_EVIDENCE"
        elif conservative_score > 0.05 and overfit["status"] in {"PASS", "WARN"}:
            status = "DRY_RUN_CANDIDATE"
        elif conservative_score > 0.0:
            status = "SHADOW_CANDIDATE"
        else:
            status = "RESEARCH_ONLY"
        entries.append(
            {
                "strategy_id": strategy_id,
                "metrics": metrics,
                "conservative_score": float(conservative_score),
                "status": status,
                "live_ready": False,
                "live_promotion_status": "TINY_LIVE_BLOCKED",
                "score_components": {
                    "total_return": total_return,
                    "max_drawdown_penalty": -max_drawdown * 2.0,
                    "trade_count_score": trade_score,
                    "placebo_margin": placebo_margin,
                    "stress_penalty": -stress_penalty,
                    "evidence_penalty": -float(evidence["evidence_penalty"]),
                },
            }
        )
    entries.sort(key=lambda item: item["conservative_score"], reverse=True)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "PASS",
        "entries": entries,
        "top_strategy": entries[0]["strategy_id"] if entries else None,
        "rejected_strategies": [
            item["strategy_id"] for item in entries if item["status"] == "REJECTED"
        ],
        "dry_run_candidates": [
            item["strategy_id"] for item in entries if item["status"] == "DRY_RUN_CANDIDATE"
        ],
        "walk_forward_status": walk_forward["status"],
        "regime_status": regime["status"],
        "overfit_status": overfit["status"],
        "evidence_status": evidence["evidence_status"],
        "evidence_penalty": evidence["evidence_penalty"],
        "live_promotion_status": "TINY_LIVE_BLOCKED",
        "ranking_note": "Ranking is conservative and is not sorted by total return alone.",
    }
    _write_leaderboard(payload)
    return payload


def _write_leaderboard(payload: dict[str, Any]) -> None:
    root = Path("reports/strategy/leaderboard")
    root.mkdir(parents=True, exist_ok=True)
    (root / "latest_leaderboard.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8"
    )
    lines = [
        "# Strategy Leaderboard",
        "",
        "Research only. No live trading. This is not ranked by total return alone.",
        "",
        f"Live promotion: {payload['live_promotion_status']}",
        "",
        "## Entries",
    ]
    for entry in payload["entries"]:
        lines.append(
            f"- {entry['strategy_id']}: status={entry['status']} "
            f"score={entry['conservative_score']:.6f} live_ready={entry['live_ready']}"
        )
    (root / "latest_leaderboard.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
