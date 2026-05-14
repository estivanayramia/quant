from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.data.prediction_markets.pm_updown_manual_capture import DEFAULT_CAPTURE_ROOT
from quant_os.research.replay_candidates.real_cached_artifact_models import (
    ARTIFACT_TYPES,
    PRIMARY_REAL_CACHED_CAPTURE_MODES,
)
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

REPORT_ROOT = Path("reports/sequence39/manual_capture")


def build_pm_crypto_updown_real_cached_capture_plan(
    *,
    manual_network_ok: bool = False,
    capture_root: str | Path = DEFAULT_CAPTURE_ROOT,
    run_id: str = "manual_plan",
) -> dict[str, Any]:
    run_root = Path(capture_root) / run_id
    return {
        "schema_version": "pm_crypto_updown_real_cached_capture_plan_v1",
        "sequence": "39",
        "status": "REAL_CACHED_CAPTURE_READY",
        "manual_only": True,
        "read_only": True,
        "network_enabled": bool(manual_network_ok),
        "network_fetch_attempted": False,
        "auth_required": False,
        "wallet_required": False,
        "signing_allowed": False,
        "order_placement_allowed": False,
        "order_cancellation_allowed": False,
        "ci_network_dependency": False,
        "manual_network_flag": "--manual-network-ok",
        "run_id": run_id,
        "run_root": str(run_root).replace("\\", "/"),
        "manifest_path": str(run_root / "manifest.json").replace("\\", "/"),
        "normalized_artifacts_path": str(run_root / "artifacts.jsonl").replace("\\", "/"),
        "capture_targets": [
            "public_polymarket_updown_market_metadata",
            "public_polymarket_clob_orderbook_snapshots",
            "public_crypto_spot_snapshots_or_candles",
            "local_manual_window_or_resolution_labels",
        ],
        "artifact_types": sorted(ARTIFACT_TYPES),
        "capture_modes_allowed_for_primary_rows": sorted(PRIMARY_REAL_CACHED_CAPTURE_MODES),
        "operator_commands": [
            "python -m quant_os.cli data pm-crypto-updown-capture-plan",
            "python -m quant_os.cli data pm-crypto-updown-real-cached-import --import-root data/external/manual_captures/pm_crypto_updown/<run_id>",
            "python -m quant_os.cli research pm-crypto-updown-threshold-progress --real-cached-root data/external/manual_captures/pm_crypto_updown/<run_id>",
        ],
        "blocked_when_network_disabled": False,
        "capture_artifacts_are_ignored_by_default": True,
        "disallowed_capabilities": [
            "authenticated Polymarket trading",
            "wallet access",
            "signature creation",
            "order creation",
            "order posting",
            "order cancellation",
            "anti-bot bypass",
            "proxy evasion",
        ],
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_pm_crypto_updown_real_cached_capture_plan(
    *,
    output_root: str | Path = ".",
    manual_network_ok: bool = False,
    capture_root: str | Path = DEFAULT_CAPTURE_ROOT,
    run_id: str = "manual_plan",
) -> dict[str, Any]:
    payload = build_pm_crypto_updown_real_cached_capture_plan(
        manual_network_ok=manual_network_ok,
        capture_root=capture_root,
        run_id=run_id,
    )
    root = Path(output_root)
    manifest_path = root / payload["manifest_path"]
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_real_cached_capture_plan.json"
    md_path = root / "latest_real_cached_capture_plan.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 39 Real-Cached Capture Plan",
        "",
        "Manual read-only capture/import plan. Network remains disabled unless explicitly allowed.",
        "",
        f"Status: {payload['status']}",
        f"Manual only: {payload['manual_only']}",
        f"Read-only: {payload['read_only']}",
        f"Network enabled: {payload['network_enabled']}",
        f"Network fetch attempted: {payload['network_fetch_attempted']}",
        f"Run root: {payload['run_root']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        "",
        "## Capture Targets",
    ]
    lines.extend(f"- {target}" for target in payload["capture_targets"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
