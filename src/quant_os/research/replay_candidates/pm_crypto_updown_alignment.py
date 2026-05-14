from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from quant_os.data.crypto_spot_snapshots import load_crypto_spot_snapshots, parse_utc
from quant_os.data.prediction_markets.clob_snapshots import load_clob_snapshots
from quant_os.data.prediction_markets.updown_market_windows import load_updown_market_windows
from quant_os.data.prediction_markets.window_labels import load_window_labels
from quant_os.research.replay_candidates.pm_crypto_updown_schema import (
    CANDIDATE_ID,
    PmCryptoUpDownReplayRow,
)
from quant_os.research.replay_candidates.timestamp_alignment import (
    asof_snapshot,
    seconds_between,
    shifted_timestamp,
)
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

DEFAULT_FIXTURE_ROOT = Path("tests/fixtures/replay_candidates/pm_crypto_updown")
STALE_SPOT_SECONDS = 2.0
WIDE_SPREAD_THRESHOLD = 0.05
LOW_LIQUIDITY_THRESHOLD = 100.0


def build_pm_crypto_updown_dataset(
    *,
    fixture_root: str | Path = DEFAULT_FIXTURE_ROOT,
) -> dict[str, Any]:
    root = Path(fixture_root)
    rows = align_pm_crypto_updown_rows(
        spot_snapshots=load_crypto_spot_snapshots(root / "spot_snapshots.csv"),
        market_windows=load_updown_market_windows(root / "market_windows.json"),
        clob_snapshots=load_clob_snapshots(root / "clob_snapshots.json"),
        window_labels=load_window_labels(root / "window_labels.json"),
    )
    return {
        "schema_version": "pm_crypto_updown_replay_dataset_v1",
        "sequence": "36",
        "candidate_id": CANDIDATE_ID,
        "rows": rows,
        "row_count": len(rows),
        "network_fetch_attempted": False,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def align_pm_crypto_updown_rows(
    *,
    spot_snapshots: list[dict[str, Any]],
    market_windows: list[dict[str, Any]],
    clob_snapshots: list[dict[str, Any]],
    window_labels: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    clob_by_market = _group_clob_by_market(clob_snapshots)
    for window in market_windows:
        market_clob = clob_by_market.get(window["market_id"], [])
        if not market_clob:
            rows.extend(
                _missing_clob_rows(
                    window=window,
                    spot_snapshots=spot_snapshots,
                    label=window_labels.get(window["market_id"]),
                )
            )
            continue
        for clob in market_clob:
            rows.append(
                _row_from_clob(
                    window=window,
                    clob=clob,
                    spot_snapshots=spot_snapshots,
                    label=window_labels.get(window["market_id"]),
                )
            )
    return sorted(rows, key=lambda item: (item["market_id"], item["token_id"], item["event_ts"]))


def _row_from_clob(
    *,
    window: dict[str, Any],
    clob: dict[str, Any],
    spot_snapshots: list[dict[str, Any]],
    label: dict[str, Any] | None,
) -> dict[str, Any]:
    event_dt = parse_utc(clob["event_ts"])
    spot = asof_snapshot(
        spot_snapshots,
        timestamp=event_dt,
        timestamp_field="timestamp_utc",
        symbol=window["spot_symbol"],
    )
    flags = ["LOOKAHEAD_PREVENTED"]
    if spot is None:
        flags.append("MISSING_SPOT_SNAPSHOT")
    else:
        age = seconds_between(spot["timestamp_utc"], clob["event_ts"])
        if age > STALE_SPOT_SECONDS:
            flags.append("STALE_SPOT_SNAPSHOT")
    market_spread = clob["ask"] - clob["bid"]
    if market_spread > WIDE_SPREAD_THRESHOLD:
        flags.append("WIDE_SPREAD")
    if clob["liquidity"] < LOW_LIQUIDITY_THRESHOLD:
        flags.append("LOW_LIQUIDITY")
    if label is None:
        flags.append("MISSING_WINDOW_LABELS")
    elif label["label_status"] != "RESOLVED":
        flags.append("LABEL_UNRESOLVED")

    row = PmCryptoUpDownReplayRow(
        candidate_id=CANDIDATE_ID,
        market_id=window["market_id"],
        condition_id=window["condition_id"],
        slug=window["slug"],
        token_id=clob["token_id"],
        outcome=_outcome_for_token(window, clob["token_id"]),
        window_start_ts=window["window_start_ts"],
        window_end_ts=window["window_end_ts"],
        event_ts=clob["event_ts"],
        seconds_to_window_end=seconds_between(clob["event_ts"], window["window_end_ts"]),
        spot_symbol=window["spot_symbol"],
        spot_price=spot["price"] if spot else None,
        spot_return_1s=_spot_return(spot_snapshots, window["spot_symbol"], event_dt, 1),
        spot_return_5s=_spot_return(spot_snapshots, window["spot_symbol"], event_dt, 5),
        spot_return_15s=_spot_return(spot_snapshots, window["spot_symbol"], event_dt, 15),
        market_bid=clob["bid"],
        market_ask=clob["ask"],
        market_mid=(clob["bid"] + clob["ask"]) / 2.0,
        market_spread=market_spread,
        market_last_trade_price=clob["last_trade_price"],
        market_volume=clob["volume"],
        market_liquidity=clob["liquidity"],
        clob_snapshot_id=clob["clob_snapshot_id"],
        source_ids=_source_ids(spot, clob, label),
        provenance_hash=_provenance_hash(window, clob, spot, label),
        data_quality_flags=sorted(set(flags)),
        label_status=label["label_status"] if label else "MISSING",
        resolved_outcome=label.get("resolved_outcome") if label else None,
    )
    return row.to_report_dict()


def _missing_clob_rows(
    *,
    window: dict[str, Any],
    spot_snapshots: list[dict[str, Any]],
    label: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    event_ts = window["window_start_ts"]
    event_dt = parse_utc(event_ts)
    spot = asof_snapshot(
        spot_snapshots,
        timestamp=event_dt,
        timestamp_field="timestamp_utc",
        symbol=window["spot_symbol"],
    )
    rows = []
    for token in window["tokens"]:
        flags = ["MISSING_CLOB_SNAPSHOT", "LOOKAHEAD_PREVENTED"]
        if spot is None:
            flags.append("MISSING_SPOT_SNAPSHOT")
        if label is None:
            flags.append("MISSING_WINDOW_LABELS")
        elif label["label_status"] != "RESOLVED":
            flags.append("LABEL_UNRESOLVED")
        row = PmCryptoUpDownReplayRow(
            candidate_id=CANDIDATE_ID,
            market_id=window["market_id"],
            condition_id=window["condition_id"],
            slug=window["slug"],
            token_id=token["token_id"],
            outcome=token["outcome"],
            window_start_ts=window["window_start_ts"],
            window_end_ts=window["window_end_ts"],
            event_ts=event_ts,
            seconds_to_window_end=seconds_between(event_ts, window["window_end_ts"]),
            spot_symbol=window["spot_symbol"],
            spot_price=spot["price"] if spot else None,
            spot_return_1s=None,
            spot_return_5s=None,
            spot_return_15s=None,
            market_bid=None,
            market_ask=None,
            market_mid=None,
            market_spread=None,
            market_last_trade_price=None,
            market_volume=None,
            market_liquidity=None,
            clob_snapshot_id=f"missing_{window['market_id']}_{token['token_id']}",
            source_ids=_source_ids(spot, None, label),
            provenance_hash=_provenance_hash(window, {"token_id": token["token_id"]}, spot, label),
            data_quality_flags=sorted(set(flags)),
            label_status=label["label_status"] if label else "MISSING",
            resolved_outcome=label.get("resolved_outcome") if label else None,
        )
        rows.append(row.to_report_dict())
    return rows


def _spot_return(
    spot_snapshots: list[dict[str, Any]],
    symbol: str,
    event_dt: Any,
    seconds: int,
) -> float | None:
    current = asof_snapshot(
        spot_snapshots,
        timestamp=event_dt,
        timestamp_field="timestamp_utc",
        symbol=symbol,
    )
    prior = asof_snapshot(
        spot_snapshots,
        timestamp=shifted_timestamp(event_dt, seconds=seconds),
        timestamp_field="timestamp_utc",
        symbol=symbol,
    )
    if current is None or prior is None or prior["price"] == 0:
        return None
    return (current["price"] / prior["price"]) - 1.0


def _group_clob_by_market(snapshots: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for snapshot in snapshots:
        grouped.setdefault(snapshot["market_id"], []).append(snapshot)
    return grouped


def _outcome_for_token(window: dict[str, Any], token_id: str) -> str:
    token = next(item for item in window["tokens"] if item["token_id"] == token_id)
    return token["outcome"]


def _source_ids(
    spot: dict[str, Any] | None,
    clob: dict[str, Any] | None,
    label: dict[str, Any] | None,
) -> list[str]:
    source_ids = []
    if spot is not None:
        source_ids.append(str(spot["source_id"]))
    if clob is not None:
        source_ids.append(str(clob["source_id"]))
    if label is not None:
        source_ids.append(str(label["resolution_source_id"]))
    return sorted(set(source_ids))


def _provenance_hash(
    window: dict[str, Any],
    clob: dict[str, Any],
    spot: dict[str, Any] | None,
    label: dict[str, Any] | None,
) -> str:
    digest = hashlib.sha256()
    for value in [
        window.get("market_id"),
        window.get("condition_id"),
        clob.get("clob_snapshot_id"),
        clob.get("token_id"),
        clob.get("event_ts"),
        spot.get("timestamp_utc") if spot else None,
        label.get("label_status") if label else None,
        label.get("resolved_outcome") if label else None,
    ]:
        digest.update(str(value).encode("utf-8"))
    return digest.hexdigest()
