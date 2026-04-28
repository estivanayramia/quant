from __future__ import annotations

from pathlib import Path

from quant_os.research.leaderboard import build_strategy_leaderboard


def test_strategy_leaderboard_blocks_live_and_is_not_total_return_only(local_project) -> None:
    payload = build_strategy_leaderboard()
    assert payload["live_promotion_status"] == "TINY_LIVE_BLOCKED"
    assert "total return alone" in payload["ranking_note"]
    assert all(entry["live_ready"] is False for entry in payload["entries"])
    assert Path("reports/strategy/leaderboard/latest_leaderboard.json").exists()
