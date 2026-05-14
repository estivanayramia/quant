from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.data.crypto_spot_manual_capture import build_crypto_spot_manual_capture_instructions
from quant_os.data.prediction_markets.pm_updown_manual_capture import (
    DEFAULT_CAPTURE_ROOT,
    write_pm_updown_manual_capture_manifest,
)
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

REPORT_ROOT = Path("reports/sequence38/manual_capture")


def build_pm_updown_manual_capture_plan(
    *,
    output_root: str | Path = ".",
    capture_root: str | Path = DEFAULT_CAPTURE_ROOT,
) -> dict[str, Any]:
    manifest = write_pm_updown_manual_capture_manifest(
        output_root=output_root,
        capture_root=capture_root,
    )
    spot = build_crypto_spot_manual_capture_instructions(capture_root=capture_root)
    return {
        "schema_version": "pm_updown_manual_capture_plan_v1",
        "sequence": "38",
        "manual_only": True,
        "read_only": True,
        "network_enabled": False,
        "network_fetch_attempted": False,
        "auth_required": False,
        "wallet_required": False,
        "signing_allowed": False,
        "order_placement_allowed": False,
        "order_cancellation_allowed": False,
        "ci_network_dependency": False,
        "manifest_written": True,
        "capture_manifest_path": manifest["manifest_path"],
        "capture_targets": manifest["capture_targets"],
        "spot_capture": spot,
        "manual_steps": [
            "Create or update the ignored capture directory under data/external/manual_captures.",
            "Save public UP/DOWN market windows, CLOB snapshots, spot snapshots, and labels.",
            "Run the expanded dataset and evidence quality commands locally.",
            "Commit only tiny sanitized fixtures if they are deliberately promoted for tests.",
        ],
        "blocked_when_network_disabled": False,
        "capture_artifacts_are_ignored_by_default": True,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_pm_updown_manual_capture_plan(
    *,
    output_root: str | Path = ".",
    capture_root: str | Path = DEFAULT_CAPTURE_ROOT,
) -> dict[str, Any]:
    payload = build_pm_updown_manual_capture_plan(
        output_root=output_root,
        capture_root=capture_root,
    )
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_manual_capture_plan.json"
    md_path = root / "latest_manual_capture_plan.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 38 Manual Capture Plan",
        "",
        "Manual read-only capture scaffold. Network is disabled by default.",
        "",
        f"Manual only: {payload['manual_only']}",
        f"Read-only: {payload['read_only']}",
        f"Network enabled: {payload['network_enabled']}",
        f"Manifest: {payload['capture_manifest_path']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        "",
        "## Targets",
    ]
    lines.extend(f"- {item}" for item in payload["capture_targets"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
