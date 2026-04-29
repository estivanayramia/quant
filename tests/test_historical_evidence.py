from __future__ import annotations

from pathlib import Path

from quant_os.data.historical_import import import_historical_csv
from quant_os.research.historical_evidence import (
    build_historical_splits,
    calculate_historical_evidence_score,
    run_historical_leakage_check,
)

FIXTURES = Path(__file__).parent / "fixtures" / "historical"


def test_historical_splits_do_not_overlap(local_project) -> None:
    import_historical_csv(FIXTURES / "sample_ohlcv_standard.csv")
    splits = build_historical_splits()
    item = splits["items"][0]["splits"]
    assert item["train"]["end_index"] < item["validation"]["start_index"]
    assert item["validation"]["end_index"] < item["test"]["start_index"]


def test_historical_leakage_check_catches_overlap() -> None:
    payload = {
        "items": [
            {
                "symbol": "SPY",
                "timeframe": "1d",
                "splits": {
                    "train": {"start_index": 0, "end_index": 5, "rows": 6},
                    "validation": {"start_index": 5, "end_index": 7, "rows": 3},
                    "test": {"start_index": 8, "end_index": 9, "rows": 2},
                },
                "walk_forward": [],
            }
        ]
    }
    leakage = run_historical_leakage_check(write=False, splits_payload=payload)
    assert leakage["status"] == "FAIL"


def test_historical_evidence_score_blocks_live(local_project) -> None:
    import_historical_csv(FIXTURES / "sample_ohlcv_standard.csv")
    score = calculate_historical_evidence_score()
    assert score["live_promotion_status"] == "LIVE_BLOCKED"
    assert score["live_ready"] is False
