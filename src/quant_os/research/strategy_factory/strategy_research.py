from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.research.strategy_factory.campaign_common import safe_payload, write_json_md

SOURCES = [
    {
        "name": "Binance Spot API public market data",
        "url": "https://developers.binance.com/docs/binance-spot-api-docs/rest-api/market-data-endpoints",
        "source_type": "official_docs",
    },
    {
        "name": "Polymarket CLOB API",
        "url": "https://docs.polymarket.com/developers/CLOB/introduction",
        "source_type": "official_docs",
    },
    {
        "name": "Kalshi market data API",
        "url": "https://docs.kalshi.com/api-reference/market/get-market-orderbook",
        "source_type": "official_docs",
    },
    {
        "name": "National Weather Service API",
        "url": "https://www.weather.gov/documentation/services-web-api",
        "source_type": "official_docs",
    },
]

RESEARCH_FAMILIES = [
    "crypto_spot_momentum",
    "crypto_spot_mean_reversion",
    "volatility_breakout_compression",
    "cross_asset_lead_lag",
    "btc_eth_relative_strength",
    "session_time_of_day_effects",
    "weekend_overnight_crypto_behavior",
    "liquidity_spread_microstructure_filters",
    "volume_volatility_shock_filters",
    "trend_following_regime_filters",
    "market_making_like_passive_signals",
    "prediction_market_up_down_microstructure",
    "prediction_market_structural_relations",
    "weather_forecast_mismatch",
    "etf_equity_rotation_public_only",
    "temperature_ladder_tail_pricing",
    "near_resolution_residual_yield",
    "orderbook_imbalance_skew",
]


def build_strategy_research() -> dict[str, Any]:
    families = []
    for index, family in enumerate(RESEARCH_FAMILIES):
        market = _market_for_family(family)
        families.append(
            {
                "family": family,
                "market_family": market,
                "source_references": [source["url"] for source in SOURCES if _source_matches(source, market)],
                "why_it_may_have_edge": _edge_reason(family),
                "required_data": _required_data(market),
                "public_data_availability": "PUBLIC_READ_ONLY_RESEARCHABLE",
                "expected_failure_modes": [
                    "costs_absorb_edge",
                    "baseline_or_placebo_wins",
                    "multiple_testing_false_discovery",
                    "window_or_asset_dominance",
                ],
                "baseline_requirements": ["no_trade", "naive_family_baseline", "buy_and_hold_if_applicable"],
                "placebo_requirements": [
                    "random_timestamp",
                    "sign_flip",
                    "shuffled_signal_or_asset",
                ],
                "safety_classification": "PUBLIC_DATA_FAKE_MONEY_ONLY",
                "eligible_for_live_sim": True,
                "social_or_web_claim_is_proof": False,
                "priority": len(RESEARCH_FAMILIES) - index,
            }
        )
    return safe_payload(
        status="STRATEGY_RESEARCH_READY",
        sources=SOURCES,
        families=families,
        ignored_inputs=["hype_claims", "copy_trade_claims", "pnl_screenshots", "stealth_scraping"],
    )


def write_strategy_research_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_strategy_research()
    lines = [
        "Research seeds hypotheses only; it never promotes a strategy by itself.",
        f"Status: {payload['status']}",
        f"Families researched: {len(payload['families'])}",
        f"Sources: {len(payload['sources'])}",
    ]
    lines.extend(f"- {card['family']}: {card['market_family']}" for card in payload["families"][:20])
    return write_json_md(
        payload,
        output_root=output_root,
        report_dir="research",
        json_name="latest_strategy_research.json",
        md_name="latest_strategy_research.md",
        title="Strategy Research",
        lines=lines,
    )


def _market_for_family(family: str) -> str:
    if "prediction_market" in family or "near_resolution" in family or "orderbook" in family:
        return "prediction_market"
    if "weather" in family or "temperature" in family:
        return "weather"
    if "etf" in family or "equity" in family:
        return "equity_etf"
    return "crypto_spot"


def _source_matches(source: dict[str, str], market: str) -> bool:
    url = source["url"]
    return (
        (market == "crypto_spot" and "binance" in url)
        or (market == "prediction_market" and ("polymarket" in url or "kalshi" in url))
        or (market == "weather" and "weather.gov" in url)
        or market == "equity_etf"
    )


def _required_data(market: str) -> list[str]:
    if market == "crypto_spot":
        return ["public candles", "public spreads/depth proxy", "future public marks"]
    if market == "prediction_market":
        return ["public market metadata", "public orderbook snapshots", "resolved outcomes"]
    if market == "weather":
        return ["issue-time public forecasts", "market bucket prices", "resolved weather outcomes"]
    return ["public OHLCV", "public benchmarks", "paper-only costs"]


def _edge_reason(family: str) -> str:
    if "microstructure" in family or "orderbook" in family:
        return "Public books can lag fair-value or structural constraints, but only replay can test it."
    if "weather" in family or "temperature" in family:
        return "Forecast distributions and bucket prices can diverge before resolution."
    if "volatility" in family:
        return "Volatility regime changes can alter continuation/reversion odds."
    return "Public market behavior may show conditional drift after costs in narrow regimes."
