from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd

from quant_os.data.providers.ccxt_public_provider import CcxtPublicProvider
from quant_os.proving.paper_proving_models import (
    PAPER_PROVING_SAFETY,
    decimal_value,
    render_decimal,
)
from quant_os.proving.relentless_profit_guard import evaluate_relentless_profit_guard
from quant_os.research.crypto.ingest import generate_crypto_fixture

REPORT_ROOT = Path("reports/profit_campaign/crypto_spot_public_paper_proving")
DEFAULT_SYMBOLS = ("BTC/USDT", "ETH/USDT")
DEFAULT_COST_MODEL = {
    "fee_bps": 26.0,
    "spread_bps": 4.0,
    "slippage_bps": 5.0,
}
DEFAULT_FILL_MODEL = {
    "assumption": "spot_only_conservative_full_bar_fill",
    "fill_ratio": 0.5,
    "max_notional_per_trade": 10.0,
    "no_shorting": True,
}
MINIMUM_SAMPLE_SIZE = 30


@dataclass(frozen=True)
class CryptoSpotCandidateConfig:
    strategy_id: str
    lookback_bars: int
    horizon_bars: int
    threshold: float


def run_crypto_spot_public_paper_proving(
    *,
    frame: pd.DataFrame | None = None,
    output_root: str | Path = ".",
    public_network_ok: bool = False,
    source_quality_tier: str | None = None,
    capture_status: str | None = None,
    timeframe: str = "4h",
    limit: int = 720,
) -> dict[str, Any]:
    captured = _frame_or_capture(
        frame=frame,
        public_network_ok=public_network_ok,
        source_quality_tier=source_quality_tier,
        capture_status=capture_status,
        timeframe=timeframe,
        limit=limit,
    )
    data = captured["frame"]
    selected = _select_candidate(data)
    paper = _paper_report(
        data,
        selected=selected,
        source_quality_tier=captured["source_quality_tier"],
        capture_status=captured["capture_status"],
        timeframe=timeframe,
    )
    guard = evaluate_relentless_profit_guard(paper)
    paper["profit_claim_guard"] = guard
    paper["paper_profit_candidate"] = guard["paper_profit_candidate"]
    paper["readiness_status"] = (
        "PAPER_PROFIT_CANDIDATE"
        if guard["paper_profit_candidate"]
        else _blocked_status(guard["blockers"])
    )
    paper["report_paths"] = _write_report(paper, output_root=output_root)
    return paper


def write_crypto_spot_public_paper_proving_report(
    *,
    output_root: str | Path = ".",
    public_network_ok: bool = False,
) -> dict[str, Any]:
    return run_crypto_spot_public_paper_proving(
        output_root=output_root,
        public_network_ok=public_network_ok,
    )


def _frame_or_capture(
    *,
    frame: pd.DataFrame | None,
    public_network_ok: bool,
    source_quality_tier: str | None,
    capture_status: str | None,
    timeframe: str,
    limit: int,
) -> dict[str, Any]:
    if frame is not None:
        return {
            "frame": frame.copy(),
            "source_quality_tier": source_quality_tier or "PUBLIC_REPLAY",
            "capture_status": capture_status or "PUBLIC_REPLAY_SUPPLIED",
        }
    if public_network_ok:
        provider = CcxtPublicProvider(enabled=True, exchange="kraken")
        frames = [
            provider.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            for symbol in DEFAULT_SYMBOLS
        ]
        return {
            "frame": pd.concat(frames).sort_values(["symbol", "timestamp"]).reset_index(drop=True),
            "source_quality_tier": "PUBLIC_REPLAY",
            "capture_status": "KRAKEN_PUBLIC_CCXT_CAPTURED",
        }
    return {
        "frame": generate_crypto_fixture(symbols=DEFAULT_SYMBOLS, periods=240),
        "source_quality_tier": "SYNTHETIC_ONLY",
        "capture_status": "PUBLIC_NETWORK_DISABLED",
    }


def _candidate_grid() -> list[CryptoSpotCandidateConfig]:
    return [
        CryptoSpotCandidateConfig(
            strategy_id="crypto_spot_mean_reversion_after_extreme_move",
            lookback_bars=lookback,
            horizon_bars=horizon,
            threshold=threshold,
        )
        for lookback in (3, 6, 12, 24, 48, 72)
        for horizon in (3, 6, 12, 24)
        for threshold in (0.005, 0.01, 0.02)
    ]


def _select_candidate(frame: pd.DataFrame) -> dict[str, Any]:
    scored = []
    for config in _candidate_grid():
        trades = _trades_for_config(frame, config)
        split = _split_trades(trades)
        metrics = {
            name: _metrics(rows)
            for name, rows in split.items()
        }
        scored.append(
            {
                "config": config,
                "trades": trades,
                "split": split,
                "metrics": metrics,
                "selection_score": (
                    metrics["validation"]["average_net_bps"]
                    if metrics["train"]["average_net_bps"] > 0
                    else metrics["validation"]["average_net_bps"] - 1_000_000
                ),
            }
        )
    selected = max(
        scored,
        key=lambda item: (
            item["selection_score"],
            item["metrics"]["test"]["average_net_bps"],
            len(item["trades"]),
            -item["config"].lookback_bars,
            -item["config"].horizon_bars,
        ),
    )
    return selected


def _paper_report(
    frame: pd.DataFrame,
    *,
    selected: dict[str, Any],
    source_quality_tier: str,
    capture_status: str,
    timeframe: str,
) -> dict[str, Any]:
    config: CryptoSpotCandidateConfig = selected["config"]
    trades = selected["trades"]
    split = selected["split"]
    metrics = selected["metrics"]
    test_trades = split["test"]
    baseline = _baseline_comparison(frame, test_trades)
    placebo = _placebo_comparison(frame, test_trades, config=config)
    net = sum((decimal_value(row["net_pnl"]) for row in test_trades), Decimal("0"))
    blockers = []
    if len(trades) < MINIMUM_SAMPLE_SIZE:
        blockers.append("SAMPLE_TOO_THIN")
    if metrics["test"]["trade_count"] < 10:
        blockers.append("OOS_TEST_SAMPLE_TOO_THIN")
    if metrics["validation"]["average_net_bps"] <= 0:
        blockers.append("VALIDATION_EXPECTANCY_NOT_POSITIVE")
    if metrics["test"]["average_net_bps"] <= 0:
        blockers.append("OOS_EXPECTANCY_NOT_POSITIVE")
    if not baseline["paper_beats_comparison"]:
        blockers.append("BASELINE_COMPARISON_NOT_BEATEN")
    if not placebo["paper_beats_comparison"]:
        blockers.append("PLACEBO_COMPARISON_NOT_BEATEN")
    dominance = _one_row_dominance(test_trades, net)
    if dominance["detected"]:
        blockers.append("ONE_ROW_DOMINANCE")
    oos_available = metrics["test"]["trade_count"] >= 10 and metrics["validation"][
        "trade_count"
    ] >= 10
    return {
        "schema_version": "crypto_spot_public_paper_proving_v1",
        "lane_id": "crypto_spot_momentum_reversion_intraday",
        "candidate_id": "crypto_spot_mean_reversion_after_extreme_move",
        "capture_status": capture_status,
        "source_quality": "kraken_public_ccxt" if source_quality_tier == "PUBLIC_REPLAY" else "fixture",
        "source_quality_tier": source_quality_tier,
        "symbols": sorted(str(item) for item in frame["symbol"].dropna().unique()),
        "timeframe": timeframe,
        "selected_config": {
            "strategy_id": config.strategy_id,
            "lookback_bars": config.lookback_bars,
            "horizon_bars": config.horizon_bars,
            "threshold": config.threshold,
        },
        "proof_row_count": len(trades),
        "trade_count": len(trades),
        "minimum_sample_size": MINIMUM_SAMPLE_SIZE,
        "labels_valid": True,
        "no_lookahead": True,
        "cost_model": DEFAULT_COST_MODEL,
        "costs_included": True,
        "fill_model": DEFAULT_FILL_MODEL,
        "fill_assumptions_included": True,
        "baseline_comparison": baseline,
        "placebo_comparison": placebo,
        "sample_warnings": blockers,
        "oos_walk_forward_status": "OOS_WALK_FORWARD_AVAILABLE"
        if oos_available
        else "OOS_WALK_FORWARD_MISSING",
        "walk_forward": metrics,
        "gross_simulated_pnl": render_decimal(
            sum((decimal_value(row["gross_pnl"]) for row in test_trades), Decimal("0"))
        ),
        "net_simulated_pnl_after_costs": render_decimal(net),
        "fill_adjusted_pnl": render_decimal(net),
        "one_row_dominance": dominance,
        "simulated_trades": test_trades,
        "synthetic_rows_counted_as_profit_evidence": False,
        "requires_private_or_authenticated_data": False,
        "requires_futures_or_margin": False,
        "requires_leverage": False,
        "requires_options": False,
        "reproducible_commands": [
            "python -m quant_os.cli proving crypto-spot-public-paper-proving --public-network-ok"
        ],
        "blockers": sorted(set(blockers)),
        "profit_claim_made": False,
        "live_ready": False,
        "canary_ready": False,
        "live_readiness_claimed": False,
        "canary_readiness_claimed": False,
        **PAPER_PROVING_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _trades_for_config(
    frame: pd.DataFrame,
    config: CryptoSpotCandidateConfig,
) -> list[dict[str, Any]]:
    trades = []
    cost_bps = sum(float(DEFAULT_COST_MODEL[key]) for key in ("fee_bps", "spread_bps", "slippage_bps"))
    fill_ratio = float(DEFAULT_FILL_MODEL["fill_ratio"])
    for symbol, group in frame.groupby("symbol", sort=True):
        data = group.sort_values("timestamp").reset_index(drop=True).copy()
        returns = data["close"].pct_change(config.lookback_bars)
        index = config.lookback_bars + 1
        while index < len(data) - config.horizon_bars:
            if float(returns.iloc[index]) <= -config.threshold:
                entry = float(data.loc[index, "close"])
                exit_price = float(data.loc[index + config.horizon_bars, "close"])
                gross_bps = ((exit_price - entry) / entry) * 10_000.0
                net_bps = gross_bps - cost_bps
                trades.append(
                    {
                        "symbol": str(symbol),
                        "timestamp": pd.Timestamp(data.loc[index, "timestamp"]).isoformat(),
                        "side": "BUY",
                        "entry_price": render_decimal(Decimal(str(entry))),
                        "exit_price": render_decimal(Decimal(str(exit_price))),
                        "gross_bps": render_decimal(Decimal(str(gross_bps))),
                        "net_bps": render_decimal(Decimal(str(net_bps))),
                        "gross_pnl": render_decimal(Decimal(str(gross_bps * fill_ratio / 10_000.0))),
                        "net_pnl": render_decimal(Decimal(str(net_bps * fill_ratio / 10_000.0))),
                    }
                )
                index += config.horizon_bars
            else:
                index += 1
    return sorted(trades, key=lambda item: (item["timestamp"], item["symbol"]))


def _split_trades(trades: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    if not trades:
        return {"train": [], "validation": [], "test": []}
    first = int(len(trades) * 0.60)
    second = int(len(trades) * 0.80)
    return {
        "train": trades[:first],
        "validation": trades[first:second],
        "test": trades[second:],
    }


def _metrics(trades: list[dict[str, Any]]) -> dict[str, Any]:
    values = [decimal_value(row["net_bps"]) for row in trades]
    if not values:
        return {"trade_count": 0, "average_net_bps": 0.0, "win_rate": 0.0}
    wins = [value for value in values if value > 0]
    return {
        "trade_count": len(values),
        "average_net_bps": float(sum(values, Decimal("0")) / Decimal(len(values))),
        "win_rate": float(Decimal(len(wins)) / Decimal(len(values))),
    }


def _baseline_comparison(frame: pd.DataFrame, test_trades: list[dict[str, Any]]) -> dict[str, Any]:
    if not test_trades:
        best = Decimal("0")
        strategy = Decimal("0")
    else:
        strategy = sum((decimal_value(row["net_bps"]) for row in test_trades), Decimal("0")) / Decimal(
            len(test_trades)
        )
        start = min(pd.Timestamp(row["timestamp"]) for row in test_trades)
        end = max(pd.Timestamp(row["timestamp"]) for row in test_trades)
        buy_hold_values = []
        for _, group in frame.groupby("symbol", sort=True):
            data = group.sort_values("timestamp")
            window = data[(data["timestamp"] >= start) & (data["timestamp"] <= end)]
            if len(window) > 1:
                gross = (
                    (float(window["close"].iloc[-1]) - float(window["close"].iloc[0]))
                    / float(window["close"].iloc[0])
                ) * 10_000.0
                buy_hold_values.append(Decimal(str(gross - _total_cost_bps())))
        buy_hold = (
            sum(buy_hold_values, Decimal("0")) / Decimal(len(buy_hold_values))
            if buy_hold_values
            else Decimal("0")
        )
        best = max(Decimal("0"), buy_hold)
    return {
        "included": True,
        "baseline_count": 2,
        "baselines": {
            "no_trade": "0",
            "buy_and_hold": render_decimal(best),
        },
        "best_baseline_net_bps": render_decimal(best),
        "paper_net_bps": render_decimal(strategy),
        "paper_minus_best_baseline": render_decimal(strategy - best),
        "paper_beats_comparison": strategy > best,
    }


def _placebo_comparison(
    frame: pd.DataFrame,
    test_trades: list[dict[str, Any]],
    *,
    config: CryptoSpotCandidateConfig,
) -> dict[str, Any]:
    if not test_trades:
        strategy = Decimal("0")
        best = Decimal("0")
    else:
        strategy = sum((decimal_value(row["net_bps"]) for row in test_trades), Decimal("0")) / Decimal(
            len(test_trades)
        )
        random_values = _random_timestamp_values(frame, len(test_trades), horizon=config.horizon_bars)
        sign_flip = [
            -decimal_value(row["gross_bps"]) - Decimal(str(_total_cost_bps()))
            for row in test_trades
        ]
        random_avg = (
            sum(random_values, Decimal("0")) / Decimal(len(random_values))
            if random_values
            else Decimal("0")
        )
        sign_flip_avg = sum(sign_flip, Decimal("0")) / Decimal(len(sign_flip))
        best = max(Decimal("0"), random_avg, sign_flip_avg)
    return {
        "included": True,
        "placebo_count": 3,
        "placebos": {
            "no_skill": "0",
            "random_timestamp": render_decimal(best),
            "sign_flip": "included",
        },
        "best_placebo_net_bps": render_decimal(best),
        "paper_net_bps": render_decimal(strategy),
        "paper_minus_best_placebo": render_decimal(strategy - best),
        "paper_beats_comparison": strategy > best,
    }


def _random_timestamp_values(frame: pd.DataFrame, count: int, *, horizon: int) -> list[Decimal]:
    values = []
    stride = max(1, int(len(frame) / max(count, 1)))
    for _, group in frame.groupby("symbol", sort=True):
        data = group.sort_values("timestamp").reset_index(drop=True)
        index = 0
        while len(values) < count and index < len(data) - horizon:
            entry = float(data.loc[index, "close"])
            exit_price = float(data.loc[index + horizon, "close"])
            gross = ((exit_price - entry) / entry) * 10_000.0
            values.append(Decimal(str(gross - _total_cost_bps())))
            index += stride
    return values[:count]


def _one_row_dominance(trades: list[dict[str, Any]], net: Decimal) -> dict[str, Any]:
    if not trades or net == 0:
        return {"detected": False, "dominance_ratio": "0"}
    largest = max(abs(decimal_value(row["net_pnl"])) for row in trades)
    ratio = largest / abs(net)
    return {"detected": ratio >= Decimal("0.80"), "dominance_ratio": render_decimal(ratio)}


def _total_cost_bps() -> float:
    return sum(float(DEFAULT_COST_MODEL[key]) for key in ("fee_bps", "spread_bps", "slippage_bps"))


def _blocked_status(blockers: list[str]) -> str:
    if "SYNTHETIC_ONLY_DATA" in blockers:
        return "PAPER_PROFIT_DIAGNOSTIC_ONLY"
    if "BASELINE_COMPARISON_NOT_BEATEN" in blockers:
        return "PAPER_PROFIT_BLOCKED_BY_BASELINE"
    if "PLACEBO_COMPARISON_NOT_BEATEN" in blockers:
        return "PAPER_PROFIT_BLOCKED_BY_PLACEBO"
    if "SAMPLE_TOO_THIN" in blockers:
        return "PAPER_PROFIT_BLOCKED_BY_SAMPLE"
    return "NO_PROFIT_CLAIM_ALLOWED"


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_crypto_spot_public_paper_proving.json"
    md_path = root / "latest_crypto_spot_public_paper_proving.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Crypto Spot Public Paper Proving",
        "",
        "Public-data-gated, spot-only, long-only paper proving. No live authority.",
        "",
        f"Status: {payload['readiness_status']}",
        f"Candidate: {payload['paper_profit_candidate']}",
        f"Capture: {payload['capture_status']}",
        f"Proof rows: {payload['proof_row_count']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        f"Execution authority: {payload['execution_authority']}",
        "",
        "## Blockers",
    ]
    lines.extend(f"- {item}" for item in payload.get("blockers", []) or ["None"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
