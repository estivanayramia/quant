from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from quant_os.autonomy.multi_market_live_sim_common import (
    ROOT,
    mm_hash,
    safe_report_payload,
    write_multi_market_state,
)
from quant_os.readiness.canary_readiness_common import utc_now, write_json_markdown_report

REPORT_DIR = ROOT / "crypto_spot"
KRAKEN_OHLC_URL = "https://api.kraken.com/0/public/OHLC"
KRAKEN_DEPTH_URL = "https://api.kraken.com/0/public/Depth"
KRAKEN_PAIRS = {"BTC/USD": "XXBTZUSD", "ETH/USD": "XETHZUSD"}


def build_crypto_spot_live_sim_observer(
    *,
    public_snapshot: dict[str, Any] | None = None,
    public_network_ok: bool = False,
    max_observations: int = 30,
) -> dict[str, Any]:
    blockers: list[str] = []
    if public_snapshot is None:
        if public_network_ok:
            public_snapshot = fetch_kraken_public_snapshot()
        else:
            public_snapshot = fixture_public_snapshot()
            blockers.append("FIXTURE_SAFE_SMOKE_MODE")
    observations = _observations_from_snapshot(public_snapshot, max_observations=max_observations)
    status = "CRYPTO_OBSERVER_READY" if observations else "CRYPTO_OBSERVER_BLOCKED"
    if not observations:
        blockers.append("NO_PUBLIC_CRYPTO_OBSERVATIONS")
    payload = safe_report_payload(
        schema_version="crypto_spot_live_sim_observer_v1",
        status=status,
        allowed_statuses=[
            "CRYPTO_OBSERVER_READY",
            "CRYPTO_OBSERVER_BLOCKED",
        ],
        source=public_snapshot.get("source"),
        source_policy="public_read_only_unauthenticated",
        public_unauthenticated_data_only=True,
        credential_sources_used=[],
        authenticated_endpoint_called=False,
        active_instruments=sorted(public_snapshot.get("symbols", {}).keys()),
        observation_count=len(observations),
        observations=observations,
        blockers=blockers,
        next_action="Generate fake-money no-transmit crypto spot intents."
        if observations
        else "Retry public crypto spot observation later.",
    )
    return payload


def write_crypto_spot_live_sim_observer_report(
    *,
    output_root: str | Path = ".",
    public_snapshot: dict[str, Any] | None = None,
    public_network_ok: bool = False,
    max_observations: int = 30,
) -> dict[str, Any]:
    payload = build_crypto_spot_live_sim_observer(
        public_snapshot=public_snapshot,
        public_network_ok=public_network_ok,
        max_observations=max_observations,
    )
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_crypto_observer.json",
        md_name="latest_crypto_observer.md",
        title="Crypto Spot Live Sim Observer",
        summary="Public unauthenticated crypto spot observation for fake-money live simulation.",
    )
    state = {
        "crypto_spot": {
            "market_family": "crypto_spot",
            "active_instruments": payload["active_instruments"],
            "observations_count": payload["observation_count"],
            "eligible_fake_intents_count": 0,
            "fake_fills_count": 0,
            "fake_no_fill_count": 0,
            "resolved_outcomes_or_future_marks_count": 0,
            "pending_outcomes_count": 0,
            "fake_gross_pnl": 0.0,
            "fake_net_pnl": 0.0,
            "baseline_pnl": 0.0,
            "placebo_pnl": 0.0,
            "reconciliation_status": "NOT_RUN",
            "status": payload["status"],
            "blockers": payload["blockers"],
            "next_action": payload["next_action"],
            "exact_resume_command": ".\\make.cmd multi-market-live-sim-smoke",
            "safety_flags": safe_report_payload(),
        }
    }
    write_multi_market_state(
        output_root=output_root,
        status="MULTI_MARKET_LIVE_SIM_CHECKPOINTED_NOT_COMPLETE",
        market_families=state,
    )
    return payload


def fetch_kraken_public_snapshot() -> dict[str, Any]:
    symbols: dict[str, Any] = {}
    for symbol, pair in KRAKEN_PAIRS.items():
        params = urllib.parse.urlencode({"pair": pair, "interval": 1})
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
            for row in rows[-90:]
        ]
        book = _fetch_kraken_book(pair)
        symbols[symbol] = {"source_pair": pair, "candles": candles, "book": book}
    return {
        "source": "kraken_public_rest_unauthenticated",
        "fetched_at": utc_now(),
        "symbols": symbols,
    }


def fixture_public_snapshot() -> dict[str, Any]:
    closes_btc = [100.0, 100.2, 100.6, 101.2, 101.7, 102.1, 102.7, 103.1]
    closes_eth = [50.0, 49.95, 49.9, 49.8, 49.7, 49.6, 49.5, 49.4]
    return {
        "source": "fixture_public_kraken_shape",
        "fetched_at": "2026-05-17T18:00:00Z",
        "symbols": {
            "BTC/USD": {
                "source_pair": "XXBTZUSD",
                "candles": [_candle("2026-05-17T17", idx, close) for idx, close in enumerate(closes_btc, 50)],
                "book": {"bid": 103.09, "ask": 103.11, "spread": 0.02, "bid_size": 4.0, "ask_size": 4.0},
            },
            "ETH/USD": {
                "source_pair": "XETHZUSD",
                "candles": [_candle("2026-05-17T17", idx, close) for idx, close in enumerate(closes_eth, 50)],
                "book": {"bid": 49.39, "ask": 49.41, "spread": 0.02, "bid_size": 8.0, "ask_size": 8.0},
            },
        },
    }


def _observations_from_snapshot(snapshot: dict[str, Any], *, max_observations: int) -> list[dict[str, Any]]:
    symbols = snapshot.get("symbols", {})
    btc = list((symbols.get("BTC/USD") or {}).get("candles", []) or [])
    eth = list((symbols.get("ETH/USD") or {}).get("candles", []) or [])
    book = (symbols.get("BTC/USD") or {}).get("book", {})
    mark_horizon = 1 if str(snapshot.get("source", "")).startswith("fixture") else 3
    limit = min(len(btc), len(eth)) - mark_horizon
    observations: list[dict[str, Any]] = []
    for idx in range(1, max(limit, 1)):
        prev_btc = float(btc[idx - 1]["close"])
        prev_eth = float(eth[idx - 1]["close"])
        btc_ret = (float(btc[idx]["close"]) - prev_btc) / prev_btc if prev_btc else 0.0
        eth_ret = (float(eth[idx]["close"]) - prev_eth) / prev_eth if prev_eth else 0.0
        spread = float(book.get("spread") or 0.0)
        observation = {
            "observation_id": f"cobs_{mm_hash({'idx': idx, 'btc': btc[idx], 'eth': eth[idx]})}",
            "strategy": "btc_eth_relative_strength_rotation",
            "symbol": "BTC/USD",
            "entry_timestamp": btc[idx]["timestamp"],
            "entry_price": float(btc[idx]["close"]),
            "mark_timestamp": btc[idx + mark_horizon]["timestamp"],
            "mark_price": float(btc[idx + mark_horizon]["close"]),
            "mark_horizon_minutes": mark_horizon,
            "btc_return": round(btc_ret, 10),
            "eth_return": round(eth_ret, 10),
            "relative_strength": round(btc_ret - eth_ret, 10),
            "bid": float(book.get("bid") or btc[idx]["close"]),
            "ask": float(book.get("ask") or btc[idx]["close"]),
            "spread": spread,
            "ask_size": float(book.get("ask_size") or 1.0),
            "public_market_data": True,
            "evidence_hash": mm_hash({"btc": btc[idx], "eth": eth[idx], "book": book}),
            "eligible": btc_ret > eth_ret and spread <= 0.1000001,
        }
        observations.append(observation)
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


def _candle(hour_prefix: str, minute: int, close: float) -> dict[str, float | str]:
    return {
        "timestamp": f"{hour_prefix}:{minute:02d}:00Z",
        "open": close,
        "high": close + 0.2,
        "low": close - 0.2,
        "close": close,
        "volume": 10.0 + minute,
    }
