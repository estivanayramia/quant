from __future__ import annotations

from quant_os.features.smc_scoring import add_smc_scores


def test_smc_score_is_deterministic(spy_frame) -> None:
    first = add_smc_scores(spy_frame)
    second = add_smc_scores(spy_frame)
    assert first["smc_score"].round(10).tolist() == second["smc_score"].round(10).tolist()
    assert {"smc_liquidity_score", "smc_fvg_score", "smc_structure_score"}.issubset(first.columns)
