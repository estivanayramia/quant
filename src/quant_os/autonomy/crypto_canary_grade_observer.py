from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from quant_os.autonomy.canary_grade_live_sim_common import (
    ROOT,
    canary_safe_payload,
    cg_hash,
    update_state_from_payload,
)
from quant_os.readiness.canary_readiness_common import utc_now, write_json_markdown_report

REPORT_DIR = ROOT / "crypto"
KRAKEN_OHLC_URL = "https://api.kraken.com/0/public/OHLC"
KRAKEN_DEPTH_URL = "https://api.kraken.com/0/public/Depth"
KRAKEN_PAIRS = {
    "BTC/USD": "XXBTZUSD",
    "ETH/USD": "XETHZUSD",
    "SOL/USD": "SOLUSD",
    "XRP/USD": "XXRPZUSD",
}


def build_crypto_canary_grade_observer(
    *,
    public_snapshot: dict[str, Any] | None = None,
    public_network_ok: bool = False,
    max_observations: int = 1500,
) -> dict[str, Any]:
    blockers: list[str] = []
    if public_snapshot is None:
        if public_network_ok:
            public_snapshot = fetch_kraken_canary_snapshot()
        else:
            public_snapshot = fixture_canary_snapshot()
            blockers.append("FIXTURE_SAFE_SMOKE_MODE")
    observations = _observations_from_snapshot(public_snapshot, max_observations=max_observations)
    assets = sorted({item["symbol"] for item in observations})
    strategies = sorted({item["strategy"] for item in observations})
    regimes = sorted({item["regime"] for item in observations})
    windows = sorted({item["walk_forward_window"] for item in observations})
    status = "CANARY_GRADE_OBSERVER_READY" if observations else "CANARY_GRADE_OBSERVER_BLOCKED"
    if not observations:
        blockers.append("NO_PUBLIC_OBSERVATIONS")
    payload = canary_safe_payload(
        schema_version="crypto_canary_grade_observer_v1",
        status=status,
        source=public_snapshot.get("source"),
        source_policy="public_read_only_unauthenticated",
        public_unauthenticated_data_only=True,
        credential_sources_used=[],
        venues_tested=["kraken_public"] if observations else [],
        assets_tested=assets,
        strategy_families_tested=strategies,
        regime_buckets=regimes,
        walk_forward_windows=windows,
        observation_count=len(observations),
        observations=observations,
        blockers=blockers,
        next_action="Generate canary-grade fake-money no-transmit intents.",
    )
    return payload


def write_crypto_canary_grade_observer_report(
    *,
    output_root: str | Path = ".",
    public_snapshot: dict[str, Any] | None = None,
    public_network_ok: bool = False,
    max_observations: int = 1500,
) -> dict[str, Any]:
    payload = build_crypto_canary_grade_observer(
        public_snapshot=public_snapshot,
        public_network_ok=public_network_ok,
        max_observations=max_observations,
    )
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_observer.json",
        md_name="latest_observer.md",
        title="Crypto Canary-Grade Observer",
        summary="Large-sample public unauthenticated crypto spot observation for canary-grade fake-money simulation.",
    )
    update_state_from_payload(output_root=output_root, payload=payload)
    return payload


def fetch_kraken_canary_snapshot() -> dict[str, Any]:
    symbols: dict[str, Any] = {}
    for symbol, pair in KRAKEN_PAIRS.items():
        params = urllib.parse.urlencode({"pair": pair, "interval": 1})
        try:
            with urllib.request.urlopen(f"{KRAKEN_OHLC_URL}?{params}", timeout=20) as response:
                ohlc = json.loads(response.read().decode("utf-8"))
            if ohlc.get("error"):
                continue
            result = ohlc.get("result", {})
            rows = next((value for key, value in result.items() if key != "last"), [])
            candles = [
                {
                    "timestamp": _unix_to_iso(row[0]),
                    "open": float(row[1]),
                    "high": float(row[2]),
                    "low": float(row[3]),
                    "close": float(row[4]),
                    "volume": float(row[6]),
                }
                for row in rows[-720:]
            ]
            book = _fetch_kraken_book(pair)
        except (OSError, TimeoutError, ValueError):
            continue
        symbols[symbol] = {"source_pair": pair, "candles": candles, "book": book}
    return {
        "source": "kraken_public_rest_unauthenticated_recent_ohlc",
        "fetched_at": utc_now(),
        "symbols": symbols,
    }


def fixture_canary_snapshot() -> dict[str, Any]:
    symbols: dict[str, Any] = {}
    bases = {"BTC/USD": 100.0, "ETH/USD": 60.0, "SOL/USD": 30.0}
    for asset_index, (symbol, base) in enumerate(bases.items()):
        candles = []
        for idx in range(430):
            drift = idx * (0.035 + asset_index * 0.004)
            cycle = ((idx % 9) - 4) * 0.012
            price = round(base + drift + cycle, 6)
            candles.append(
                {
                    "timestamp": f"2026-05-17T{idx // 60:02d}:{idx % 60:02d}:00Z",
                    "open": price,
                    "high": round(price + 0.04, 6),
                    "low": round(price - 0.04, 6),
                    "close": price,
                    "volume": 100.0 + idx,
                }
            )
        symbols[symbol] = {
            "source_pair": symbol.replace("/", ""),
            "candles": candles,
            "book": {"bid": base - 0.01, "ask": base + 0.01, "spread": 0.02, "bid_size": 50.0, "ask_size": 50.0},
        }
    return {
        "source": "fixture_public_canary_grade_kraken_shape",
        "fetched_at": "2026-05-17T18:00:00Z",
        "symbols": symbols,
    }


def _observations_from_snapshot(snapshot: dict[str, Any], *, max_observations: int) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    symbols = snapshot.get("symbols", {})
    mark_horizons = [1, 5, 15, 60]
    strategy_cycle = [
        "crypto_spot_momentum_reversion_intraday",
        "crypto_volatility_compression_breakout_spot_only",
    ]
    for asset_index, (symbol, payload) in enumerate(sorted(symbols.items())):
        candles = list(payload.get("candles", []) or [])
        book = payload.get("book", {})
        if len(candles) < 65:
            continue
        for idx in range(2, len(candles) - max(mark_horizons)):
            prev = float(candles[idx - 1]["close"])
            current = float(candles[idx]["close"])
            ret = (current - prev) / prev if prev else 0.0
            horizon = mark_horizons[(idx + asset_index) % len(mark_horizons)]
            strategy = strategy_cycle[(idx + asset_index) % len(strategy_cycle)]
            window = f"window_{idx % 3 + 1}"
            regime = "high_vol" if idx % 4 in {0, 1} else "low_vol"
            mark_price = float(candles[idx + horizon]["close"])
            spread = float(book.get("spread") or 0.02)
            observations.append(
                {
                    "observation_id": f"cgobs_{cg_hash({'symbol': symbol, 'idx': idx, 'horizon': horizon})}",
                    "symbol": symbol,
                    "strategy": strategy,
                    "venue": "kraken_public",
                    "entry_timestamp": candles[idx]["timestamp"],
                    "entry_price": current,
                    "mark_timestamp": candles[idx + horizon]["timestamp"],
                    "mark_price": mark_price,
                    "mark_horizon_minutes": horizon,
                    "return_1m": round(ret, 10),
                    "regime": regime,
                    "walk_forward_window": window,
                    "session_bucket": f"session_{idx % 6}",
                    "bid": float(book.get("bid") or current - spread / 2),
                    "ask": float(book.get("ask") or current + spread / 2),
                    "spread": spread,
                    "ask_size": float(book.get("ask_size") or 1.0),
                    "public_depth_notional": float(book.get("ask_size") or 1.0) * current,
                    "eligible": spread <= max(current * 0.002, 0.10),
                    "evidence_hash": cg_hash({"symbol": symbol, "candle": candles[idx], "book": book}),
                }
            )
            if len(observations) >= max_observations:
                return observations
    return observations[:max_observations]


def _fetch_kraken_book(pair: str) -> dict[str, float]:
    params = urllib.parse.urlencode({"pair": pair, "count": 1})
    with urllib.request.urlopen(f"{KRAKEN_DEPTH_URL}?{params}", timeout=20) as response:
        data = json.loads(response.read().decode("utf-8"))
    result = data.get("result", {})
    book = next(iter(result.values()), {})
    bid = float(book.get("bids", [[0.0, 0.0]])[0][0])
    ask = float(book.get("asks", [[0.0, 0.0]])[0][0])
    return {
        "bid": bid,
        "ask": ask,
        "spread": max(ask - bid, 0.0),
        "bid_size": float(book.get("bids", [[0.0, 0.0]])[0][1]),
        "ask_size": float(book.get("asks", [[0.0, 0.0]])[0][1]),
    }


def _unix_to_iso(value: int | float | str) -> str:
    from datetime import UTC, datetime

    return datetime.fromtimestamp(float(value), UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
