from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quant_os.data.prediction_markets.normalization import (
    REPO_ROOT,
    load_prediction_market_payload,
    normalize_polymarket_payload,
)
from quant_os.data.providers.polymarket_public_provider import PolymarketPublicProvider
from quant_os.data.warehouse import ensure_local_dirs

DEFAULT_POLYMARKET_FIXTURE = (
    REPO_ROOT / "tests" / "fixtures" / "prediction_markets" / "polymarket_markets_sample.json"
)
DEFAULT_OUTPUT_DIR = Path("data/prediction_markets/polymarket")


def capture_polymarket_markets(
    *,
    fixture_path: str | Path | None = None,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    allow_network_fetch: bool = False,
    explicit_network_fetch: bool = False,
    provider: PolymarketPublicProvider | None = None,
) -> dict[str, Any]:
    ensure_local_dirs()
    requested_network = bool(allow_network_fetch)
    if requested_network and not explicit_network_fetch and fixture_path is None:
        return _blocked_capture("NETWORK_FETCH_REQUIRES_EXPLICIT_FLAG", requested_network)

    if requested_network and explicit_network_fetch and fixture_path is None:
        raw_payload = (provider or PolymarketPublicProvider(enabled=True)).fetch_markets(
            allow_network_fetch=True,
            explicit_network_fetch=True,
        )
        raw_payload["captured_at"] = datetime.now(UTC).isoformat()
        source_mode = "network_manual"
        source_path: Path | None = None
    else:
        source_path = Path(fixture_path or DEFAULT_POLYMARKET_FIXTURE)
        raw_payload = load_prediction_market_payload(source_path)
        source_mode = str(raw_payload.get("source_mode") or "fixture")

    records = normalize_polymarket_payload(raw_payload, source_path=source_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / "latest_polymarket_markets.json"
    payload = {
        "schema_version": "1.0",
        "source": "polymarket",
        "source_mode": source_mode,
        "captured_at": raw_payload.get("captured_at") or datetime.now(UTC).isoformat(),
        "market_count": len(records),
        "markets": raw_payload.get("markets", []),
        "normalized_market_count": len(records),
        "normalized_markets": [record.model_dump(mode="json") for record in records],
        "network_fetch_requested": requested_network,
        "network_fetch_allowed": bool(source_mode == "network_manual"),
        "live_trading_enabled": False,
        "live_allowed": False,
        "execution_enabled": False,
        "wallet_signing_enabled": False,
        "evidence_only": True,
    }
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    return {
        "status": "PASS",
        "source": "polymarket",
        "source_mode": source_mode,
        "market_count": len(records),
        "file_path": str(output_path),
        "network_fetch_requested": requested_network,
        "network_fetch_allowed": bool(source_mode == "network_manual"),
        "live_trading_enabled": False,
        "execution_enabled": False,
    }


def _blocked_capture(reason: str, requested_network: bool) -> dict[str, Any]:
    return {
        "status": "BLOCKED",
        "source": "polymarket",
        "source_mode": "none",
        "market_count": 0,
        "blockers": [reason],
        "network_fetch_requested": requested_network,
        "network_fetch_allowed": False,
        "live_trading_enabled": False,
        "execution_enabled": False,
    }
