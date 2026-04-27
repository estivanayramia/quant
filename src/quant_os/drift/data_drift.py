from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd


@dataclass
class DriftSignal:
    name: str
    detected: bool
    severity: str
    details: dict[str, float | int | str]


def detect_data_drift(
    frame: pd.DataFrame,
    mean_return_shift_threshold: float = 0.05,
    volatility_shift_pct_threshold: float = 0.75,
    volume_shift_pct_threshold: float = 1.0,
) -> DriftSignal:
    data = frame.sort_values("timestamp").copy()
    data["return"] = data.groupby("symbol")["close"].pct_change().fillna(0.0)
    midpoint = len(data) // 2
    reference = data.iloc[:midpoint]
    current = data.iloc[midpoint:]
    ref_mean = float(reference["return"].mean())
    cur_mean = float(current["return"].mean())
    ref_vol = float(reference["return"].std() or 0.0)
    cur_vol = float(current["return"].std() or 0.0)
    ref_volume = float(reference["volume"].mean())
    cur_volume = float(current["volume"].mean())
    missing_rate = float(data["timestamp"].isna().mean())
    mean_shift = abs(cur_mean - ref_mean)
    vol_shift = _pct_shift(ref_vol, cur_vol)
    volume_shift = _pct_shift(ref_volume, cur_volume)
    detected = (
        mean_shift > mean_return_shift_threshold
        or vol_shift > volatility_shift_pct_threshold
        or volume_shift > volume_shift_pct_threshold
        or missing_rate > 0.0
    )
    return DriftSignal(
        name="data_drift",
        detected=detected,
        severity="warning" if detected else "ok",
        details={
            "mean_return_shift": mean_shift,
            "volatility_shift_pct": vol_shift,
            "volume_shift_pct": volume_shift,
            "missing_timestamp_rate": missing_rate,
        },
    )


def _pct_shift(reference: float, current: float) -> float:
    if abs(reference) < 1e-12:
        return 0.0 if abs(current) < 1e-12 else 1.0
    return abs(current - reference) / abs(reference)


def signal_to_dict(signal: DriftSignal) -> dict[str, object]:
    return asdict(signal)
