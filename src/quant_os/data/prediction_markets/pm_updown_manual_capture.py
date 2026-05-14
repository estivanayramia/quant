from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_CAPTURE_ROOT = Path("data/external/manual_captures/pm_crypto_updown")


def build_pm_updown_manual_capture_manifest(
    *,
    capture_root: str | Path = DEFAULT_CAPTURE_ROOT,
) -> dict[str, Any]:
    root = Path(capture_root)
    return {
        "schema_version": "pm_updown_manual_capture_manifest_v1",
        "manual_only": True,
        "read_only": True,
        "network_enabled": False,
        "network_fetch_attempted": False,
        "source_quality_for_completed_capture": "real_cached",
        "capture_root": str(root).replace("\\", "/"),
        "expected_files": {
            "market_windows": str(root / "market_windows.json").replace("\\", "/"),
            "clob_snapshots": str(root / "clob_snapshots.json").replace("\\", "/"),
            "spot_snapshots": str(root / "spot_snapshots.csv").replace("\\", "/"),
            "window_labels": str(root / "window_labels.json").replace("\\", "/"),
        },
        "capture_targets": [
            "polymarket_updown_market_metadata",
            "polymarket_public_clob_orderbook_snapshots",
            "crypto_spot_snapshots_or_candles",
            "market_window_labels_and_resolution_metadata",
        ],
        "disallowed_capabilities": [
            "authenticated access",
            "wallet access",
            "signature creation",
            "live execution",
            "order placement",
            "order cancellation",
            "anti-bot bypass",
        ],
    }


def write_pm_updown_manual_capture_manifest(
    *,
    output_root: str | Path = ".",
    capture_root: str | Path = DEFAULT_CAPTURE_ROOT,
) -> dict[str, Any]:
    manifest = build_pm_updown_manual_capture_manifest(capture_root=capture_root)
    relative_path = Path("data/external/manual_captures/pm_crypto_updown/capture_manifest.json")
    path = Path(output_root) / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    manifest["manifest_path"] = str(relative_path).replace("\\", "/")
    return manifest
