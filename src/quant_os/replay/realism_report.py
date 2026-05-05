from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.replay.adverse_selection import AdverseSelectionModel
from quant_os.replay.engine import ReplayEngine, ReplayOrderIntent
from quant_os.replay.liquidity_filters import LiquidityGate, LiquidityPolicy
from quant_os.replay.market_impact import MarketImpactModel
from quant_os.research.crypto.features import build_crypto_features
from quant_os.research.crypto.ingest import build_crypto_research_dataset


def write_replay_realism_report(
    *,
    periods: int = 120,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    dataset = build_crypto_research_dataset(periods=periods)
    frame = build_crypto_features(dataset.frame)
    btc = frame[frame["symbol"] == "BTC/USDT"].reset_index(drop=True)
    intents = [
        ReplayOrderIntent(
            "sequence2_replay_realism",
            "BTC/USDT",
            "BUY",
            0.01,
            btc.loc[5, "timestamp"],
            reason_code="SEQUENCE2_REALISM_ENTRY",
        ),
        ReplayOrderIntent(
            "sequence2_replay_realism",
            "BTC/USDT",
            "SELL",
            0.01,
            btc.loc[min(len(btc) - 1, 35), "timestamp"],
            reason_code="SEQUENCE2_REALISM_EXIT",
        ),
    ]
    result = ReplayEngine(
        fee_bps=5.0,
        slippage_bps=3.0,
        liquidity_gate=LiquidityGate(policy=LiquidityPolicy()),
        market_impact_model=MarketImpactModel(),
        adverse_selection_model=AdverseSelectionModel(),
    ).run(frame, intents)
    payload = {
        "status": result.reconciliation["status"],
        "fills": len(result.fills),
        "rejections": len(result.rejections),
        "metrics": result.metrics,
        "rejection_reasons": sorted({item["reason"] for item in result.rejections}),
        "live_trading_enabled": False,
        "live_promotion_status": "LIVE_BLOCKED",
    }
    _write_report(payload, output_root=output_root)
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> None:
    root = Path(output_root) / "reports" / "sequence2" / "replay_realism"
    root.mkdir(parents=True, exist_ok=True)
    (root / "latest_realism_report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    lines = [
        "# Sequence 2 Replay Realism",
        "",
        "Offline replay only. No live trading.",
        "",
        f"Status: {payload['status']}",
        f"Fills: {payload['fills']}",
        f"Rejections: {payload['rejections']}",
        f"Realism penalty bps: {payload['metrics'].get('realism_penalty_bps', 0.0):.4f}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
    ]
    (root / "latest_realism_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
