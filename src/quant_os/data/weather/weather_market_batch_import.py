from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from quant_os.data.weather.weather_market_capture_artifacts import load_capture_artifact


def import_weather_batch_capture(capture_manifest_path: str | Path) -> dict[str, Any]:
    manifest = load_capture_artifact(capture_manifest_path)["payload"]
    proof_rows = 0
    pending_rows = 0
    missing_market_data = 0
    ambiguous_mapping = 0
    quality_counter: Counter[str] = Counter()
    for record in manifest.get("markets", []):
        quality_counter.update([record.get("source_quality", "UNKNOWN")])
        if record.get("proof_row_ready"):
            proof_rows += 1
        if record.get("pending_label"):
            pending_rows += 1
        if record.get("blocked_by_missing_market_data"):
            missing_market_data += 1
        if record.get("blocked_by_ambiguous_mapping"):
            ambiguous_mapping += 1
    return {
        "schema_version": "weather_market_batch_import_v1",
        "sequence": "52",
        "manifest_path": str(capture_manifest_path).replace("\\", "/"),
        "proof_rows_created": proof_rows,
        "rows_pending_labels": pending_rows,
        "rows_blocked_by_missing_market_data": missing_market_data,
        "rows_blocked_by_ambiguous_mapping": ambiguous_mapping,
        "source_quality_distribution": dict(sorted(quality_counter.items())),
        "combined_provenance_hash": manifest.get("combined_provenance_hash"),
        "read_only": True,
        "ci_network_dependency": False,
        "live_trading_enabled": False,
        "execution_authority": "NONE",
    }
