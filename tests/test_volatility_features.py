from __future__ import annotations

import pandas as pd

from quant_os.features.volatility import add_volatility_features


def test_volatility_builder_creates_technical_features(spy_frame) -> None:
    features = add_volatility_features(spy_frame)
    assert {"returns", "log_returns", "rolling_volatility", "atr_like"}.issubset(features.columns)
    assert features["rolling_volatility"].isna().sum() == 0


def test_rolling_volatility_avoids_future_leakage(spy_frame) -> None:
    base = add_volatility_features(spy_frame)
    changed = spy_frame.copy()
    changed.loc[changed.index[-1], "close"] = changed["close"].max() * 10
    rerun = add_volatility_features(changed)
    pd.testing.assert_series_equal(
        base["rolling_volatility"].iloc[:40].reset_index(drop=True),
        rerun["rolling_volatility"].iloc[:40].reset_index(drop=True),
        check_names=False,
    )
