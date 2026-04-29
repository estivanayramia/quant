from __future__ import annotations

from quant_os.proving.stability import compute_strategy_stability


def test_strategy_instability_detected_when_top_strategy_flips() -> None:
    records = [
        {"top_strategy_id": "a", "leaderboard_hash": "1"},
        {"top_strategy_id": "b", "leaderboard_hash": "2"},
        {"top_strategy_id": "a", "leaderboard_hash": "3"},
    ]
    stability = compute_strategy_stability(records)
    assert stability["status"] == "WARN"
    assert stability["top_strategy_flip_rate"] > 0.5
