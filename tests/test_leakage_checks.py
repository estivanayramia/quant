from __future__ import annotations

from quant_os.data.leakage_checks import run_leakage_checks


def test_leakage_check_catches_overlapping_train_test_ranges() -> None:
    payload = {
        "items": [
            {
                "symbol": "SPY",
                "timeframe": "1h",
                "splits": {
                    "train": {"start_index": 0, "end_index": 50, "rows": 51},
                    "validation": {"start_index": 40, "end_index": 60, "rows": 21},
                    "test": {"start_index": 61, "end_index": 99, "rows": 39},
                },
                "walk_forward": [],
            }
        ]
    }
    result = run_leakage_checks(write=False, splits_payload=payload)
    assert result["status"] == "FAIL"
    assert result["target_leakage"] == "NOT_APPLICABLE"
