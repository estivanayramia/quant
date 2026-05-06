from __future__ import annotations

from typing import Any

from quant_os.research.prediction_markets.lane_dynamics import apply_dynamic_signal_families
from quant_os.research.prediction_markets.time_series_features import build_time_series_features

LANE_SPLIT_SAFETY = {
    "execution_authority": "NONE",
    "wallet_signing_enabled": False,
    "live_trading_enabled": False,
    "copy_trading_enabled": False,
    "real_orders_enabled": False,
}
MIN_RESOLVED_FOR_OOS_SPLITS = 18
MIN_OOS_OBSERVATIONS = 10


def build_chronological_lane_splits(dataset: dict[str, Any]) -> dict[str, Any]:
    features = [
        feature
        for feature in apply_dynamic_signal_families(build_time_series_features(dataset))
        if feature["prediction_label"] is not None
    ]
    features = sorted(features, key=lambda item: (item["prediction_timestamp"], item["market_id"]))
    split_status = (
        "OOS_SPLITS_READY"
        if len(features) >= MIN_RESOLVED_FOR_OOS_SPLITS
        else "LANE_OOS_TOO_THIN"
    )
    train, validation, test = _split(features)
    leakage_check = _leakage_check(train=train, validation=validation, test=test)
    return {
        "sequence": "26",
        "source": dataset["source"],
        "source_mode": dataset["source_mode"],
        "lane_id": dataset["lane_id"],
        "dataset_id": dataset["dataset_id"],
        "dataset_hash": dataset["dataset_hash"],
        "split_status": split_status,
        "resolved_observation_count": len(features),
        "oos_observation_count": len(validation) + len(test),
        "split_counts": {
            "train": len(train),
            "validation": len(validation),
            "test": len(test),
        },
        "splits": {
            "train": train,
            "validation": validation,
            "test": test,
        },
        "leakage_check": leakage_check,
        **LANE_SPLIT_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _split(features: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], ...]:
    if len(features) < MIN_RESOLVED_FOR_OOS_SPLITS:
        midpoint = len(features) // 2
        return features[:midpoint], [], features[midpoint:]
    train_count = len(features) // 2
    remaining = len(features) - train_count
    validation_count = remaining // 2
    train = features[:train_count]
    validation = features[train_count : train_count + validation_count]
    test = features[train_count + validation_count :]
    return train, validation, test


def _leakage_check(
    *,
    train: list[dict[str, Any]],
    validation: list[dict[str, Any]],
    test: list[dict[str, Any]],
) -> dict[str, Any]:
    warnings = []
    if not train or not validation or not test:
        warnings.append("INSUFFICIENT_SPLIT_COVERAGE")
    if _overlaps(train, validation) or _overlaps(train, test) or _overlaps(validation, test):
        warnings.append("MARKET_ID_SPLIT_OVERLAP")
    if train and validation and max(_timestamps(train)) >= min(_timestamps(validation)):
        warnings.append("TRAIN_VALIDATION_CHRONOLOGY_VIOLATION")
    if validation and test and max(_timestamps(validation)) >= min(_timestamps(test)):
        warnings.append("VALIDATION_TEST_CHRONOLOGY_VIOLATION")
    oos_count = len(validation) + len(test)
    if oos_count < MIN_OOS_OBSERVATIONS:
        warnings.append("LANE_OOS_TOO_THIN")
    return {
        "passed": not warnings,
        "warnings": warnings,
        "train_end": max(_timestamps(train)) if train else None,
        "validation_start": min(_timestamps(validation)) if validation else None,
        "validation_end": max(_timestamps(validation)) if validation else None,
        "test_start": min(_timestamps(test)) if test else None,
    }


def _overlaps(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> bool:
    return bool({item["market_id"] for item in left} & {item["market_id"] for item in right})


def _timestamps(rows: list[dict[str, Any]]) -> list[str]:
    return [item["prediction_timestamp"] for item in rows]
