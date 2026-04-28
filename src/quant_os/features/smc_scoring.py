from __future__ import annotations

import pandas as pd

from quant_os.features.market_structure import add_market_structure_features


def add_smc_scores(frame: pd.DataFrame) -> pd.DataFrame:
    data = add_market_structure_features(frame)
    data["smc_liquidity_score"] = data["liquidity_sweep_down"].astype(float) - data[
        "liquidity_sweep_up"
    ].astype(float)
    data["smc_fvg_score"] = data["bullish_fvg"].astype(float) - data["bearish_fvg"].astype(float)
    data["smc_structure_score"] = data["bos_up"].astype(float) - data["bos_down"].astype(float)
    data["smc_premium_discount_score"] = 0.5 - data["premium_discount"]
    data["smc_score"] = (
        0.30 * data["smc_liquidity_score"]
        + 0.25 * data["smc_fvg_score"]
        + 0.25 * data["smc_structure_score"]
        + 0.20 * data["smc_premium_discount_score"]
    )
    return data
