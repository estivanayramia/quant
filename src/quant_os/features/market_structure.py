from __future__ import annotations

import pandas as pd

from quant_os.features.liquidity import add_liquidity_features


def add_market_structure_features(frame: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    data = add_liquidity_features(frame, window)
    pieces = []
    for _, group in data.groupby("symbol", sort=False):
        group = group.copy()
        high_low_range = (group["rolling_high"] - group["rolling_low"]).replace(0, pd.NA)
        group["premium_discount"] = (
            (group["close"] - group["rolling_low"]) / high_low_range
        ).fillna(0.5)
        group["bullish_fvg"] = group["low"] > group["high"].shift(2)
        group["bearish_fvg"] = group["high"] < group["low"].shift(2)
        group["fvg_gap_size"] = 0.0
        group.loc[group["bullish_fvg"], "fvg_gap_size"] = group.loc[
            group["bullish_fvg"], "low"
        ] - group["high"].shift(2)
        group.loc[group["bearish_fvg"], "fvg_gap_size"] = (
            group["low"].shift(2) - group.loc[group["bearish_fvg"], "high"]
        )
        group["bos_up"] = group["close"] > group["prior_swing_high"]
        group["bos_down"] = group["close"] < group["prior_swing_low"]
        group["structure_direction"] = "neutral"
        group.loc[group["bos_up"], "structure_direction"] = "up"
        group.loc[group["bos_down"], "structure_direction"] = "down"
        group["structure_confidence"] = (
            (group["close"].pct_change().abs().rolling(5, min_periods=1).mean() * 100).clip(0, 1)
        ).fillna(0.0)
        group["order_block_freshness"] = (
            (~group["bullish_fvg"] & ~group["bearish_fvg"]).rolling(10, min_periods=1).mean()
        )
        group["displacement_score"] = (
            ((group["close"] - group["open"]).abs() / group["close"])
            .rolling(3, min_periods=1)
            .mean()
            * 100
        ).fillna(0.0)
        pieces.append(group)
    return pd.concat(pieces).sort_index()


def detect_fvg(frame: pd.DataFrame) -> list[dict[str, object]]:
    data = add_market_structure_features(frame)
    events = []
    for _, row in data.iterrows():
        if bool(row["bullish_fvg"]):
            events.append(
                {
                    "timestamp": row["timestamp"],
                    "symbol": row["symbol"],
                    "direction": "bullish",
                    "gap_size": float(row["fvg_gap_size"]),
                }
            )
        if bool(row["bearish_fvg"]):
            events.append(
                {
                    "timestamp": row["timestamp"],
                    "symbol": row["symbol"],
                    "direction": "bearish",
                    "gap_size": float(row["fvg_gap_size"]),
                }
            )
    return events


def detect_bos_choch(frame: pd.DataFrame) -> list[dict[str, object]]:
    data = add_market_structure_features(frame)
    return [
        {
            "timestamp": row["timestamp"],
            "symbol": row["symbol"],
            "direction": row["structure_direction"],
            "confidence": float(row["structure_confidence"]),
        }
        for _, row in data.iterrows()
        if row["structure_direction"] != "neutral"
    ]


def detect_order_block(frame: pd.DataFrame) -> list[dict[str, object]]:
    data = add_market_structure_features(frame)
    candidates = data[
        data["displacement_score"] > data["displacement_score"].rolling(20, min_periods=1).mean()
    ]
    return [
        {
            "timestamp": row["timestamp"],
            "symbol": row["symbol"],
            "freshness_score": float(row["order_block_freshness"]),
            "displacement_score": float(row["displacement_score"]),
        }
        for _, row in candidates.iterrows()
    ]
