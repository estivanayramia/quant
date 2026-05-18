from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.research.strategy_factory.campaign_common import safe_payload, write_json_md

REPORT_DIR = "live_sim"


def build_variant_observations(count: int = 60) -> list[dict[str, Any]]:
    assets = ["BTC/USD", "ETH/USD", "SOL/USD", "XRP/USD", "DOGE/USD"]
    return [
        {
            "observation_id": f"vlso_{index:04d}",
            "timestamp": f"2026-05-18T{index // 60:02d}:{index % 60:02d}:00Z",
            "asset": assets[index % len(assets)],
            "bid": 100.0 + index,
            "ask": 100.05 + index,
            "source": "public_fixture_safe_market_data",
        }
        for index in range(count)
    ]


def build_variant_intents(count: int = 60) -> list[dict[str, Any]]:
    observations = build_variant_observations(count)
    return [
        {
            "intent_id": f"vlsi_{index:04d}",
            "variant_id": f"tsv_fixture_{index % 10:02d}",
            "timestamp": row["timestamp"],
            "asset": row["asset"],
            "side": "buy" if index % 2 == 0 else "sell",
            "fake_money": True,
            "no_transmit": True,
            "endpoint": "/public/market-data/preview",
            "notional_usd": 1.0,
        }
        for index, row in enumerate(observations)
    ]


def build_variant_fills(count: int = 60) -> list[dict[str, Any]]:
    intents = build_variant_intents(count)
    return [
        {
            "fill_id": f"vlsf_{index:04d}",
            "intent_id": intent["intent_id"],
            "variant_id": intent["variant_id"],
            "asset": intent["asset"],
            "side": intent["side"],
            "entry_timestamp": intent["timestamp"],
            "entry_price": 100.1 + index,
            "quantity": 0.01,
            "fake_money": True,
            "no_transmit": True,
            "fill_type": "conservative_fake_fill" if index % 7 else "fake_no_fill",
        }
        for index, intent in enumerate(intents)
    ]


def build_variant_pnl_rows(count: int = 60) -> list[dict[str, Any]]:
    rows = []
    for index, fill in enumerate(build_variant_fills(count)):
        if fill["fill_type"] == "fake_no_fill":
            continue
        entry_hour = index // 60
        entry_minute = index % 60
        mark_minute = entry_minute + 1
        mark_hour = entry_hour
        if mark_minute >= 60:
            mark_hour += 1
            mark_minute -= 60
        mark_price = fill["entry_price"] + (0.08 if index % 3 == 0 else -0.03)
        rows.append(
            {
                **fill,
                "mark_timestamp": f"2026-05-18T{mark_hour:02d}:{mark_minute:02d}:00Z",
                "mark_price": round(mark_price, 6),
                "fee_cost": 0.005,
                "spread_cost": 0.005,
                "slippage_cost": 0.005,
                "net_pnl": round((mark_price - fill["entry_price"]) * fill["quantity"] - 0.015, 6),
            }
        )
    return rows


def write_live_sim_summary(*, output_root: str | Path = ".") -> dict[str, Any]:
    rows = build_variant_pnl_rows()
    payload = safe_payload(
        status="VARIANT_LIVE_SIM_SUMMARY_READY",
        observation_count=60,
        eligible_intent_count=60,
        fake_fill_count=len(rows),
        completed_mark_count=len(rows),
        fake_net_pnl=round(sum(row["net_pnl"] for row in rows), 6),
        data_sources=["public_fixture_safe_market_data"],
        no_credentials=True,
        no_orders=True,
    )
    return write_json_md(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_live_sim_summary.json",
        md_name="latest_live_sim_summary.md",
        title="Variant Live Sim Summary",
        lines=[
            f"Status: {payload['status']}",
            f"Fake net PnL: {payload['fake_net_pnl']}",
            "No live orders, auth, or signing.",
        ],
    )
