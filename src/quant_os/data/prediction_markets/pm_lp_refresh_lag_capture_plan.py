from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.research.replay_candidates.pm_lp_refresh_lag_schema import (
    ALIASES,
    CANDIDATE_ID,
)
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

REPORT_ROOT = Path("reports/sequence48/capture_plan")
DEFAULT_CAPTURE_ROOT = Path("data/external/manual_captures/pm_lp_refresh_lag")


def build_pm_lp_refresh_lag_capture_plan(
    *,
    capture_root: str | Path = DEFAULT_CAPTURE_ROOT,
) -> dict[str, Any]:
    root = Path(capture_root)
    return {
        "schema_version": "pm_lp_refresh_lag_capture_plan_v1",
        "sequence": "48",
        "candidate_id": CANDIDATE_ID,
        "aliases": ALIASES,
        "status": "LOCAL_ONLY_CAPTURE_PLAN_READY_WITH_SOURCE_BLOCKER",
        "manual_only": True,
        "read_only": True,
        "network_enabled": False,
        "network_fetch_attempted": False,
        "ci_network_dependency": False,
        "auth_headers_allowed": False,
        "browser_cookies_allowed": False,
        "wallet_required": False,
        "wallet_signing_allowed": False,
        "order_endpoints_allowed": False,
        "order_placement_allowed": False,
        "order_cancellation_allowed": False,
        "paid_api_allowed": False,
        "anti_bot_evasion_allowed": False,
        "manual_capture_must_be_source_policy_approved": True,
        "capture_root": str(root).replace("\\", "/"),
        "expected_local_files": {
            "source_manifest": str(root / "source_manifest.json").replace("\\", "/"),
            "orderbook_events": str(root / "orderbook_events.jsonl").replace("\\", "/"),
            "trade_events": str(root / "trade_events.jsonl").replace("\\", "/"),
            "spot_triggers": str(root / "spot_triggers.jsonl").replace("\\", "/"),
            "resolution_labels": str(root / "resolution_labels.json").replace("\\", "/"),
            "reduced_fixture": str(root / "reduced_fixture.json").replace("\\", "/"),
        },
        "allowed_public_sources": _allowed_public_sources(),
        "rejected_sources": _rejected_sources(),
        "manual_steps": [
            "Review source policy and source feasibility before any manual capture.",
            "Use only public read-only Gamma, CLOB market-data, Data API, rewards, and spot sources.",
            "Capture only local observations with timestamps and provenance hashes.",
            "Reduce raw captures into tiny sanitized fixtures before committing anything.",
            "If a required public field is unavailable, record the precise blocker and do nothing.",
        ],
        "fallback_policy": (
            "When a source is unavailable, auth-only, unsafe, login-walled, or ambiguous: "
            "source unavailable, do nothing."
        ),
        "blocked_fixture_path": (
            "tests/fixtures/replay_candidates/pm_lp_refresh_lag/public_source_sample/"
            "blocked_missing_public_fill_attribution.json"
        ),
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_pm_lp_refresh_lag_capture_plan(
    *,
    output_root: str | Path = ".",
    capture_root: str | Path = DEFAULT_CAPTURE_ROOT,
) -> dict[str, Any]:
    payload = build_pm_lp_refresh_lag_capture_plan(capture_root=capture_root)
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _allowed_public_sources() -> list[dict[str, Any]]:
    return [
        _source(
            "polymarket_gamma_metadata",
            "Polymarket Gamma markets/events metadata",
            ["market_id", "condition_id", "token_ids", "outcomes", "resolution_labels"],
        ),
        _source(
            "polymarket_public_clob_orderbook",
            "Polymarket public CLOB orderbook and market channel",
            ["orderbook_snapshots", "bid_ask_levels", "quote_timestamps"],
        ),
        _source(
            "polymarket_public_data_trades",
            "Polymarket public Data API trades or market-channel last-trade messages",
            ["trade_fill_events", "taker_burst_evidence"],
        ),
        _source(
            "polymarket_public_rewards",
            "Polymarket public reward-market metadata",
            ["liquidity_reward_market_metadata"],
        ),
        _source(
            "public_spot_reference",
            "Public Coinbase or Binance spot market data",
            ["spot_trigger_timestamps"],
        ),
    ]


def _source(source_id: str, description: str, fields: list[str]) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "description": description,
        "required_fields_supported": fields,
        "read_only": True,
        "auth_required": False,
        "wallet_required": False,
        "execution_authority": "NONE",
    }


def _rejected_sources() -> list[dict[str, str]]:
    return [
        {
            "source_id": "polymarket_authenticated_clob_trades",
            "reason_code": "AVAILABLE_ONLY_AUTHENTICATED",
            "reason": "Exact maker_address, trader_side, and maker_orders require CLOB auth.",
        },
        {
            "source_id": "polymarket_order_or_cancel_endpoints",
            "reason_code": "UNSAFE_DEPENDENCY",
            "reason": "Order placement and cancellation are forbidden.",
        },
        {
            "source_id": "copy_trade_or_wallet_mirroring",
            "reason_code": "UNSAFE_DEPENDENCY",
            "reason": "Copy trading and wallet mirroring are forbidden.",
        },
        {
            "source_id": "browser_cookie_capture",
            "reason_code": "UNSAFE_DEPENDENCY",
            "reason": "Browser cookies and login-wall scraping are forbidden.",
        },
        {
            "source_id": "captcha_or_proxy_evasion",
            "reason_code": "UNSAFE_DEPENDENCY",
            "reason": "CAPTCHA bypass, proxy evasion, and anti-bot bypass are forbidden.",
        },
        {
            "source_id": "paid_or_private_market_api",
            "reason_code": "UNSAFE_DEPENDENCY",
            "reason": "Paid APIs and private market data are outside this public-source phase.",
        },
    ]


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_lp_refresh_lag_capture_plan.json"
    md_path = root / "latest_lp_refresh_lag_capture_plan.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 48 LP Refresh-Lag Capture Plan",
        "",
        "Local-only public read-only capture plan. No live trading or authenticated access.",
        "",
        f"Status: {payload['status']}",
        f"Manual only: {payload['manual_only']}",
        f"Read-only: {payload['read_only']}",
        f"Network enabled: {payload['network_enabled']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        f"Execution authority: {payload['execution_authority']}",
        "",
        "## Allowed Sources",
    ]
    lines.extend(f"- {item['source_id']}" for item in payload["allowed_public_sources"])
    lines.extend(["", "## Rejected Sources"])
    lines.extend(
        "- {source_id}: {reason_code}".format(
            source_id=item["source_id"],
            reason_code=item["reason_code"],
        )
        for item in payload["rejected_sources"]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
