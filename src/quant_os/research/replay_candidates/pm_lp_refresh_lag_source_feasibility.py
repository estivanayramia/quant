from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.research.replay_candidates.pm_lp_refresh_lag_schema import (
    ALIASES,
    CANDIDATE_ID,
)
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

REPORT_ROOT = Path("reports/sequence48/source_feasibility")

AVAILABLE_PUBLIC_READ_ONLY = "AVAILABLE_PUBLIC_READ_ONLY"
AVAILABLE_WITH_MANUAL_CAPTURE = "AVAILABLE_WITH_MANUAL_CAPTURE"
AVAILABLE_ONLY_AUTHENTICATED = "AVAILABLE_ONLY_AUTHENTICATED"
NOT_AVAILABLE_PUBLICLY = "NOT_AVAILABLE_PUBLICLY"
UNSAFE_DEPENDENCY = "UNSAFE_DEPENDENCY"
UNKNOWN_NEEDS_DOC_REVIEW = "UNKNOWN_NEEDS_DOC_REVIEW"

FIELD_STATUS_VALUES = [
    AVAILABLE_PUBLIC_READ_ONLY,
    AVAILABLE_WITH_MANUAL_CAPTURE,
    AVAILABLE_ONLY_AUTHENTICATED,
    NOT_AVAILABLE_PUBLICLY,
    UNSAFE_DEPENDENCY,
    UNKNOWN_NEEDS_DOC_REVIEW,
]

SOURCE_READY_STATUSES = {AVAILABLE_PUBLIC_READ_ONLY, AVAILABLE_WITH_MANUAL_CAPTURE}


def build_pm_lp_refresh_lag_source_feasibility(
    *,
    field_status_overrides: dict[str, str] | None = None,
    unsafe_dependency_flags: list[str] | None = None,
) -> dict[str, Any]:
    fields = _required_fields()
    overrides = field_status_overrides or {}
    if overrides:
        fields = [
            {**field, "status": _validated_status(overrides[field["field_id"]])}
            if field["field_id"] in overrides
            else field
            for field in fields
        ]
    unsafe_flags = sorted(set(unsafe_dependency_flags or []))
    active_blocker = _active_blocker(fields=fields, unsafe_dependency_flags=unsafe_flags)
    return {
        "schema_version": "pm_lp_refresh_lag_source_feasibility_v1",
        "sequence": "48",
        "candidate_id": CANDIDATE_ID,
        "aliases": ALIASES,
        "feasibility_status": "PUBLIC_SOURCE_FEASIBILITY_REVIEWED",
        "allowed_field_statuses": FIELD_STATUS_VALUES,
        "required_fields": fields,
        "reviewed_sources": _reviewed_sources(),
        "unsafe_dependencies": _unsafe_dependencies(),
        "unsafe_dependency_flags": unsafe_flags,
        "active_blocker": active_blocker,
        "public_source_acquisition_ready": active_blocker is None,
        "exact_missing_source_fields": _missing_fields_for_blocker(
            fields=fields,
            blocker=active_blocker,
        ),
        "network_fetch_attempted": False,
        "ci_network_dependency": False,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
        **SOCIAL_INTAKE_SAFETY,
    }


def write_pm_lp_refresh_lag_source_feasibility_report(
    *,
    output_root: str | Path = ".",
    field_status_overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    payload = build_pm_lp_refresh_lag_source_feasibility(
        field_status_overrides=field_status_overrides,
    )
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _required_fields() -> list[dict[str, Any]]:
    return [
        _field(
            "market_id_condition_id",
            "market id / condition id",
            AVAILABLE_PUBLIC_READ_ONLY,
            ["Gamma market conditionId", "CLOB book market", "Market Channel condition_id"],
            "Public metadata and CLOB messages identify the market condition.",
        ),
        _field(
            "token_ids_outcomes",
            "token ids / outcomes",
            AVAILABLE_PUBLIC_READ_ONLY,
            ["Gamma clobTokenIds", "CLOB MarketToken token_id/outcome", "Market Channel assets"],
            "Public metadata maps outcome labels to CLOB token IDs.",
        ),
        _field(
            "orderbook_snapshots",
            "orderbook snapshots",
            AVAILABLE_WITH_MANUAL_CAPTURE,
            ["CLOB GET /book", "CLOB Market Channel book event"],
            "Current book snapshots are public; replay history requires local read-only capture.",
        ),
        _field(
            "bid_ask_levels",
            "bid/ask levels",
            AVAILABLE_WITH_MANUAL_CAPTURE,
            ["CLOB book bids", "CLOB book asks", "Market Channel price_change"],
            "Best levels and depth can be captured from public book and market-channel messages.",
        ),
        _field(
            "quote_timestamps",
            "quote timestamps",
            AVAILABLE_WITH_MANUAL_CAPTURE,
            ["CLOB book timestamp", "Market Channel timestamp"],
            "Timestamps are present on public book/channel messages but need local capture.",
        ),
        _field(
            "quote_refresh_timestamps",
            "quote refresh timestamps",
            AVAILABLE_WITH_MANUAL_CAPTURE,
            ["Market Channel price_change timestamp", "Market Channel best_bid_ask timestamp"],
            "Refresh timestamps can only be reconstructed from observed public quote deltas.",
        ),
        _field(
            "trade_fill_events",
            "trade/fill events",
            AVAILABLE_PUBLIC_READ_ONLY,
            ["Data API /trades", "Market Channel last_trade_price"],
            "Public feeds expose market trade events, but not enough maker fill attribution.",
        ),
        _field(
            "maker_taker_role",
            "maker/taker role if publicly available",
            AVAILABLE_ONLY_AUTHENTICATED,
            ["Authenticated CLOB /data/trades trader_side"],
            "The exact trader_side field is documented behind CLOB API-key authentication.",
        ),
        _field(
            "maker_wallet_order_attribution",
            "maker wallet/order attribution if publicly available",
            AVAILABLE_ONLY_AUTHENTICATED,
            ["Authenticated CLOB /data/trades maker_address", "maker_orders"],
            "Public trade feeds do not provide exact maker order attribution for LP fill replay.",
        ),
        _field(
            "two_sided_quoting_evidence",
            "two-sided quoting evidence",
            AVAILABLE_WITH_MANUAL_CAPTURE,
            ["Two token books", "bid/ask depth over time"],
            "Anonymous two-sided book presence is capturable, but same-maker evidence is not.",
        ),
        _field(
            "spread_maintenance",
            "spread maintenance",
            AVAILABLE_WITH_MANUAL_CAPTURE,
            ["CLOB spread", "book-derived best bid/ask deltas"],
            "Spread maintenance can be derived from captured public quote snapshots.",
        ),
        _field(
            "liquidity_reward_market_metadata",
            "liquidity/reward-market metadata",
            AVAILABLE_PUBLIC_READ_ONLY,
            ["CLOB rewards/markets/current", "Gamma rewardsMinSize/rewardsMaxSpread"],
            "Reward and liquidity fields are available from public market metadata endpoints.",
        ),
        _field(
            "spot_trigger_timestamps",
            "spot trigger timestamps",
            AVAILABLE_PUBLIC_READ_ONLY,
            ["Binance public klines/trades", "Coinbase public candles/trades"],
            "Spot reference timestamps are available from public exchange market-data sources.",
        ),
        _field(
            "taker_burst_evidence",
            "taker burst evidence",
            AVAILABLE_PUBLIC_READ_ONLY,
            ["Data API /trades timestamp", "Market Channel last_trade_price timestamp"],
            "Public trade timestamps are enough for burst counts, not exact maker attribution.",
        ),
        _field(
            "resolution_labels",
            "resolution labels",
            AVAILABLE_PUBLIC_READ_ONLY,
            ["Gamma market outcome labels", "Market Channel market_resolved"],
            "Public metadata and resolved-market events expose labels for scored replay.",
        ),
    ]


def _field(
    field_id: str,
    field_name: str,
    status: str,
    source_fields: list[str],
    feasibility_note: str,
) -> dict[str, Any]:
    return {
        "field_id": field_id,
        "field_name": field_name,
        "status": status,
        "source_fields": source_fields,
        "feasibility_note": feasibility_note,
    }


def _reviewed_sources() -> list[dict[str, str]]:
    return [
        {
            "source_id": "polymarket_market_data_overview",
            "name": "Polymarket Market Data Overview",
            "url": "https://docs.polymarket.com/market-data/overview",
            "use": "public market metadata, CLOB public data, and Data API public surface",
        },
        {
            "source_id": "polymarket_clob_get_order_book",
            "name": "Polymarket CLOB Get order book",
            "url": "https://docs.polymarket.com/api-reference/market-data/get-order-book",
            "use": "current public orderbook snapshots with timestamp, hash, bids, asks",
        },
        {
            "source_id": "polymarket_public_market_channel",
            "name": "Polymarket Market Channel",
            "url": "https://docs.polymarket.com/api-reference/wss/market",
            "use": "public real-time book, price-change, trade, and resolution messages",
        },
        {
            "source_id": "polymarket_data_api_trades",
            "name": "Polymarket Data API public trades",
            "url": "https://docs.polymarket.com/api-reference/core/get-trades-for-a-user-or-markets",
            "use": "public trade history without exact maker order attribution",
        },
        {
            "source_id": "polymarket_clob_get_trades",
            "name": "Polymarket authenticated CLOB trades",
            "url": "https://docs.polymarket.com/api-reference/trade/get-trades",
            "use": "documents auth-only maker_address, trader_side, and maker_orders",
        },
        {
            "source_id": "polymarket_rewards_current",
            "name": "Polymarket current rewards configurations",
            "url": "https://docs.polymarket.com/api-reference/rewards/get-current-active-rewards-configurations",
            "use": "public liquidity reward market metadata",
        },
        {
            "source_id": "binance_public_data",
            "name": "Binance public data",
            "url": "https://github.com/binance/binance-public-data",
            "use": "public spot klines and trades for trigger alignment",
        },
        {
            "source_id": "coinbase_public_candles",
            "name": "Coinbase public product candles",
            "url": "https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-candles",
            "use": "public spot reference candles for trigger alignment",
        },
    ]


def _unsafe_dependencies() -> list[dict[str, str]]:
    return [
        {
            "dependency_id": "copy_trade_or_wallet_mirroring",
            "status": UNSAFE_DEPENDENCY,
            "reason": "Copy trading and wallet mirroring are forbidden and not evidence.",
        },
        {
            "dependency_id": "authenticated_order_management",
            "status": UNSAFE_DEPENDENCY,
            "reason": "Order placement and cancellation endpoints are outside this phase.",
        },
        {
            "dependency_id": "browser_cookie_or_login_wall_capture",
            "status": UNSAFE_DEPENDENCY,
            "reason": "Cookie, login-wall, CAPTCHA, proxy, or anti-bot evasion is forbidden.",
        },
    ]


def _active_blocker(
    *,
    fields: list[dict[str, Any]],
    unsafe_dependency_flags: list[str],
) -> str | None:
    statuses = {item["field_id"]: item["status"] for item in fields}
    if unsafe_dependency_flags:
        return "REJECTED_UNSAFE_COPY_TRADE_DEPENDENCY"
    if any(
        statuses[field_id] not in {AVAILABLE_PUBLIC_READ_ONLY}
        for field_id in ("maker_taker_role", "maker_wallet_order_attribution")
    ):
        return "BLOCKED_MISSING_PUBLIC_FILL_ATTRIBUTION"
    if statuses["quote_refresh_timestamps"] not in SOURCE_READY_STATUSES:
        return "BLOCKED_MISSING_QUOTE_REFRESH_TIMESTAMPS"
    if statuses["orderbook_snapshots"] not in SOURCE_READY_STATUSES:
        return "BLOCKED_MISSING_ORDERBOOK_HISTORY"
    if statuses["spot_trigger_timestamps"] not in SOURCE_READY_STATUSES:
        return "BLOCKED_MISSING_SPOT_TRIGGER_ALIGNMENT"
    return None


def _missing_fields_for_blocker(
    *,
    fields: list[dict[str, Any]],
    blocker: str | None,
) -> list[str]:
    statuses = {item["field_id"]: item["status"] for item in fields}
    if blocker == "BLOCKED_MISSING_PUBLIC_FILL_ATTRIBUTION":
        return [
            field_id
            for field_id in ("maker_taker_role", "maker_wallet_order_attribution")
            if statuses[field_id] != AVAILABLE_PUBLIC_READ_ONLY
        ]
    if blocker == "BLOCKED_MISSING_QUOTE_REFRESH_TIMESTAMPS":
        return ["quote_refresh_timestamps"]
    if blocker == "BLOCKED_MISSING_ORDERBOOK_HISTORY":
        return ["orderbook_snapshots"]
    if blocker == "BLOCKED_MISSING_SPOT_TRIGGER_ALIGNMENT":
        return ["spot_trigger_timestamps"]
    return []


def _validated_status(status: str) -> str:
    if status not in FIELD_STATUS_VALUES:
        raise ValueError(f"unknown source field status: {status}")
    return status


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_source_feasibility.json"
    md_path = root / "latest_source_feasibility.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 48 PM LP Refresh-Lag Source Feasibility",
        "",
        "Public read-only source feasibility review. No auth, wallet, order, cancel, or live path.",
        "",
        f"Status: {payload['feasibility_status']}",
        f"Active blocker: {payload['active_blocker']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        f"Execution authority: {payload['execution_authority']}",
        "",
        "## Required Fields",
    ]
    lines.extend(
        "- {field}: {status}".format(
            field=item["field_id"],
            status=item["status"],
        )
        for item in payload["required_fields"]
    )
    lines.extend(["", "## Missing Fields"])
    lines.extend(f"- {field}" for field in payload["exact_missing_source_fields"] or ["None"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
