from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.autonomy.canary_grade_live_sim_common import ROOT, canary_safe_payload
from quant_os.autonomy.live_market_sim_common import load_json
from quant_os.readiness.canary_readiness_common import write_json_markdown_report

REPORT_DIR = ROOT / "capacity"


def build_crypto_live_sim_capacity(
    *, output_root: str | Path = ".", fills: dict[str, Any] | None = None
) -> dict[str, Any]:
    fills = fills or load_json("reports/canary_grade_live_sim/crypto/latest_fills.json", output_root=output_root) or {}
    rows = list(fills.get("fake_fills", []) or [])
    min_depth = min([float(row.get("public_depth_notional") or 0.0) for row in rows] or [0.0])
    max_spread = max([float(row.get("spread") or 0.0) for row in rows] or [999.0])
    sizes = {"1_usd": 1.0, "5_usd": 5.0, "10_usd": 10.0, "25_usd_diagnostic": 25.0}
    capacity_by_size = {
        name: {
            "notional": size,
            "supported": min_depth >= size,
            "partial_fill_rate": 0.0 if min_depth >= size else 1.0,
            "expected_slippage_bps": round(max_spread / max(size, 1.0), 8),
        }
        for name, size in sizes.items()
    }
    blockers: list[str] = []
    if not capacity_by_size["1_usd"]["supported"]:
        blockers.append("TINY_CANARY_LIQUIDITY_UNSUPPORTED")
    if max_spread > 1.0:
        blockers.append("SPREAD_TOO_WIDE")
    if blockers and "TINY_CANARY_LIQUIDITY_UNSUPPORTED" in blockers:
        status = "CAPACITY_BLOCKED_BY_LIQUIDITY"
    elif blockers:
        status = "CAPACITY_BLOCKED_BY_SPREAD"
    elif capacity_by_size["10_usd"]["supported"]:
        status = "CAPACITY_TINY_CANARY_PASSED"
    else:
        status = "CAPACITY_LIMITED"
    return canary_safe_payload(
        schema_version="crypto_live_sim_capacity_v1",
        status=status,
        allowed_statuses=[
            "CAPACITY_TINY_CANARY_PASSED",
            "CAPACITY_LIMITED",
            "CAPACITY_BLOCKED_BY_LIQUIDITY",
            "CAPACITY_BLOCKED_BY_SPREAD",
            "CAPACITY_DIAGNOSTIC_ONLY",
        ],
        sample_count=len(rows),
        min_public_depth_notional=round(min_depth, 8),
        max_spread=round(max_spread, 8),
        capacity_by_size=capacity_by_size,
        max_safe_notional=round(min_depth, 8),
        venue_minimums="not_checked_no_auth_public_data_only",
        blockers=blockers,
        next_action="Run final canary-grade readiness." if status == "CAPACITY_TINY_CANARY_PASSED" else "Reduce size or collect deeper public liquidity.",
    )


def write_crypto_live_sim_capacity_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_crypto_live_sim_capacity(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_capacity.json",
        md_name="latest_capacity.md",
        title="Crypto Live Sim Capacity",
        summary="Public book-depth capacity model for tiny manual canary sizing.",
    )
    return payload
