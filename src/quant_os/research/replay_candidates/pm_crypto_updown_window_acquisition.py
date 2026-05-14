from __future__ import annotations

import math
from collections import Counter
from pathlib import Path
from typing import Any

from quant_os.research.replay_candidates.pm_crypto_updown_real_cached_import import (
    build_pm_crypto_updown_real_cached_source,
)
from quant_os.research.replay_candidates.pm_crypto_updown_schema import CANDIDATE_ID
from quant_os.research.replay_candidates.pm_crypto_updown_threshold_progress import (
    evaluate_pm_crypto_updown_sequence41_threshold_progress,
)
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

REQUIRED_ARTIFACTS_PER_WINDOW = [
    "market_metadata",
    "condition_id",
    "token_ids_and_outcomes",
    "window_start_ts_and_window_end_ts",
    "clob_orderbook_snapshots",
    "spot_snapshots_or_candles",
    "label_or_resolution_data",
    "liquidity_and_spread",
]


def build_pm_crypto_updown_window_acquisition_plan(
    *,
    fixture_root: str | Path,
    real_cached_artifact_roots: list[str | Path] | None = None,
) -> dict[str, Any]:
    progress = evaluate_pm_crypto_updown_sequence41_threshold_progress(
        fixture_root=fixture_root,
        real_cached_artifact_roots=real_cached_artifact_roots,
    )
    row_gap = progress["row_gap"]
    required_windows = math.ceil(row_gap / 2)
    existing_window_coverage = _existing_window_coverage(real_cached_artifact_roots or [])
    needed_windows = _needed_windows(required_windows)
    missing_by_window = _missing_source_coverage_by_window(
        needed_windows=needed_windows,
        existing_window_coverage=existing_window_coverage,
    )
    return {
        "schema_version": "pm_crypto_updown_window_acquisition_plan_v1",
        "sequence": "41",
        "candidate_id": CANDIDATE_ID,
        "capture_or_import_status": (
            "READY_FOR_REPLAY_GATE" if row_gap == 0 else "OPERATOR_ACTION_REQUIRED"
        ),
        "previous_primary_row_count": progress["previous_primary_row_count"],
        "current_primary_row_count": progress["current_primary_row_count"],
        "previous_real_cached_row_count": progress["previous_real_cached_row_count"],
        "current_real_cached_row_count": progress["current_real_cached_row_count"],
        "target_primary_row_count": progress["target_primary_row_count"],
        "row_gap": row_gap,
        "required_remaining_two_token_windows": required_windows,
        "needed_two_token_windows": needed_windows,
        "required_artifacts_per_window": REQUIRED_ARTIFACTS_PER_WINDOW,
        "existing_window_coverage": existing_window_coverage,
        "missing_source_coverage_by_window": missing_by_window,
        "source_coverage": progress["source_coverage"],
        "source_coverage_bottleneck": progress["source_bottleneck"],
        "blockers": progress["blockers"],
        "operator_action_required": row_gap > 0,
        "code_missing": False,
        "operator_commands": _operator_commands(required_windows),
        "operator_action_items": _operator_action_items(required_windows),
        "code_status": {
            "multi_root_import_supported": True,
            "manifest_only_roots_supported": True,
            "malformed_artifacts_rejected_with_reasons": True,
            "network_capture_required": False,
        },
        "network_fetch_attempted": False,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _needed_windows(required_windows: int) -> list[dict[str, Any]]:
    windows = []
    for index in range(1, required_windows + 1):
        windows.append(
            {
                "window_slot": f"required_window_{index:03d}",
                "window_type": "two-token crypto UP/DOWN resolved window",
                "spot_symbols": ["BTC-USD"],
                "tokens_required": ["UP", "DOWN"],
                "minimum_primary_rows_expected": 2,
                "required_artifacts": REQUIRED_ARTIFACTS_PER_WINDOW,
                "missing_artifacts": REQUIRED_ARTIFACTS_PER_WINDOW,
                "operator_action": (
                    "Capture one resolved UP/DOWN market window with both token books, "
                    "near-time spot data, and resolution label, then import the local root."
                ),
            }
        )
    return windows


def _existing_window_coverage(import_roots: list[str | Path]) -> list[dict[str, Any]]:
    coverage = []
    for root_index, import_root in enumerate(import_roots, start=1):
        source = build_pm_crypto_updown_real_cached_source(
            import_root=import_root,
            source_name=f"real_cached_import_{root_index}",
        )
        normalized = source["normalized_source"]
        clobs_by_market = Counter(item["market_id"] for item in normalized["clob_snapshots"])
        labels_by_market = {item["market_id"] for item in normalized["window_labels"]}
        spot_symbols = {item["symbol"] for item in normalized["spot_snapshots"]}
        if not normalized["market_windows"]:
            coverage.append(
                {
                    "import_root": source["import_root"],
                    "window_id": "root_level",
                    "coverage_status": "NO_WINDOW_ARTIFACTS_FOUND",
                    "missing_artifacts": REQUIRED_ARTIFACTS_PER_WINDOW,
                    "operator_action_required": True,
                }
            )
            continue
        for window in normalized["market_windows"]:
            market_id = window["market_id"]
            missing = []
            if not window.get("condition_id"):
                missing.append("condition_id")
            if len(window.get("tokens") or []) < 2:
                missing.append("token_ids_and_outcomes")
            if clobs_by_market[market_id] < 2:
                missing.append("clob_orderbook_snapshots")
            if window.get("spot_symbol") not in spot_symbols:
                missing.append("spot_snapshots_or_candles")
            if market_id not in labels_by_market:
                missing.append("label_or_resolution_data")
            coverage.append(
                {
                    "import_root": source["import_root"],
                    "window_id": market_id,
                    "condition_id": window.get("condition_id"),
                    "window_start_ts": window.get("window_start_ts"),
                    "window_end_ts": window.get("window_end_ts"),
                    "token_count": len(window.get("tokens") or []),
                    "clob_snapshot_count": clobs_by_market[market_id],
                    "spot_symbol": window.get("spot_symbol"),
                    "label_present": market_id in labels_by_market,
                    "coverage_status": "COMPLETE" if not missing else "INCOMPLETE",
                    "missing_artifacts": missing,
                    "operator_action_required": bool(missing),
                }
            )
    return coverage


def _missing_source_coverage_by_window(
    *,
    needed_windows: list[dict[str, Any]],
    existing_window_coverage: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    missing = [
        item for item in existing_window_coverage if item["coverage_status"] != "COMPLETE"
    ]
    missing.extend(
        {
            "window_id": item["window_slot"],
            "coverage_status": "MISSING_NEW_WINDOW",
            "missing_artifacts": item["missing_artifacts"],
            "operator_action_required": True,
        }
        for item in needed_windows
    )
    return missing


def _operator_commands(required_windows: int) -> list[str]:
    return [
        "python -m quant_os.cli data pm-crypto-updown-capture-plan --manual-network-ok --run-id <run_id>",
        "python -m quant_os.cli data pm-crypto-updown-real-cached-import --real-cached-root data/external/manual_captures/pm_crypto_updown/<run_id>",
        "python -m quant_os.cli research pm-crypto-updown-window-acquisition --real-cached-root tests/fixtures/replay_candidates/pm_crypto_updown/real_cached_sample --real-cached-root data/external/manual_captures/pm_crypto_updown/<run_id>",
        "python -m quant_os.cli research pm-crypto-updown-threshold-progress --sequence41 --real-cached-root tests/fixtures/replay_candidates/pm_crypto_updown/real_cached_sample --real-cached-root data/external/manual_captures/pm_crypto_updown/<run_id>",
        "python -m quant_os.cli readiness expanded-shadow-replay-readiness --real-cached-root tests/fixtures/replay_candidates/pm_crypto_updown/real_cached_sample --real-cached-root data/external/manual_captures/pm_crypto_updown/<run_id>",
        f"Repeat capture/import until at least {required_windows} additional two-token windows are replay-ready.",
    ]


def _operator_action_items(required_windows: int) -> list[str]:
    if required_windows <= 0:
        return ["Run the expanded shadow replay readiness gate with the imported roots."]
    return [
        f"Collect at least {required_windows} additional resolved two-token UP/DOWN windows.",
        "For each window, store market metadata, condition id, both token ids, CLOB books, spot data, labels, liquidity, and spread.",
        "Keep captures local under data/external/manual_captures/pm_crypto_updown/<run_id>.",
        "Import all capture roots with repeated --real-cached-root arguments.",
    ]
