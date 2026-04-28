from __future__ import annotations

from typing import Any

from quant_os.features.feature_report import write_feature_report
from quant_os.research.leaderboard import build_strategy_leaderboard
from quant_os.research.research_report import write_strategy_research_report


def strategy_research_status() -> dict[str, Any]:
    features = write_feature_report()
    report = write_strategy_research_report()
    leaderboard = build_strategy_leaderboard()
    return {
        "features_built": True,
        "strategies_tested": len(report["strategy_list"]),
        "leaderboard_status": leaderboard["status"],
        "top_research_strategy": leaderboard["top_strategy"],
        "overfit_warnings_count": len(report["overfit_warnings"]),
        "dry_run_candidates": leaderboard["dry_run_candidates"],
        "live_promotion_status": "TINY_LIVE_BLOCKED",
        "latest_report_path": "reports/strategy/latest_research_report.md",
        "feature_report_path": features["report_path"],
    }
