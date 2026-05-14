from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.research.replay_candidates.pm_crypto_updown_alignment import DEFAULT_FIXTURE_ROOT
from quant_os.research.replay_candidates.pm_crypto_updown_dataset_builder import (
    MIN_PRIMARY_REPLAY_READY_ROWS,
)
from quant_os.research.replay_candidates.pm_crypto_updown_replay_eval import (
    evaluate_pm_crypto_updown_replay,
)
from quant_os.research.replay_candidates.pm_crypto_updown_schema import CANDIDATE_ID
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

REPORT_ROOT = Path("reports/sequence38/evidence_expansion")


def build_pm_crypto_updown_expansion_plan(
    *,
    fixture_root: str | Path = DEFAULT_FIXTURE_ROOT,
) -> dict[str, Any]:
    current = evaluate_pm_crypto_updown_replay(fixture_root=fixture_root)
    current_primary = current["primary_evidence_row_count"]
    rows_needed = max(MIN_PRIMARY_REPLAY_READY_ROWS - current_primary, 0)
    return {
        "schema_version": "pm_crypto_updown_expansion_plan_v1",
        "sequence": "38",
        "candidate_id": CANDIDATE_ID,
        "plan_status": "REPLAY_EVIDENCE_EXPANSION_PLAN_READY",
        "target_primary_replay_ready_rows": MIN_PRIMARY_REPLAY_READY_ROWS,
        "current_replay_ready_row_count": current["replay_ready_row_count"],
        "current_primary_evidence_row_count": current_primary,
        "rows_needed_from_current": rows_needed,
        "required_market_windows": {
            "minimum_additional_resolved_windows": 9,
            "preferred_window_type": "BTC UP/DOWN one-minute resolved windows",
            "event_sampling": "public CLOB snapshot 10-20 seconds before window end",
            "candidate_id": CANDIDATE_ID,
        },
        "required_spot_coverage": {
            "symbols": ["BTC-USD"],
            "minimum_fields": ["timestamp_utc", "symbol", "price", "source_id"],
            "lookback_seconds": [1, 5, 15],
            "no_lookahead_required": True,
        },
        "required_clob_coverage": [
            "public_clob_orderbook_snapshots",
            "token bid",
            "token ask",
            "last trade price",
            "liquidity",
            "volume",
        ],
        "required_label_coverage": [
            "resolved outcome per market window",
            "resolution source id",
            "label status",
        ],
        "acquisition_source_candidates": [
            "manual read-only Polymarket public market metadata capture",
            "manual read-only Polymarket public CLOB/orderbook snapshot capture",
            "manual read-only BTC spot snapshot/candle export from an allowed public source",
            "manual read-only market resolution metadata export",
        ],
        "manual_capture_commands": [
            "python -m quant_os.cli research pm-crypto-updown-manual-capture-plan",
            "python -m quant_os.cli research pm-crypto-updown-expanded-dataset",
            "python -m quant_os.cli research pm-crypto-updown-evidence-quality",
            "python -m quant_os.cli research pm-crypto-updown-expanded-replay-eval",
            "python -m quant_os.cli readiness expanded-shadow-replay",
        ],
        "data_quality_gates": [
            "spot snapshot at or before CLOB event timestamp",
            "CLOB bid and ask present",
            "spread not wider than replay filter threshold",
            "liquidity above replay filter threshold",
            "resolved labels present",
            "source quality labeled as real_cached, fixture_real_shaped, or synthetic_stress",
        ],
        "blockers": _blockers(rows_needed),
        "candidate_ready_for_expanded_shadow_replay": False,
        "network_fetch_attempted": False,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_pm_crypto_updown_expansion_plan(
    *,
    fixture_root: str | Path = DEFAULT_FIXTURE_ROOT,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    payload = build_pm_crypto_updown_expansion_plan(fixture_root=fixture_root)
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _blockers(rows_needed: int) -> list[str]:
    blockers = []
    if rows_needed:
        blockers.append(f"PRIMARY_ROWS_BELOW_{MIN_PRIMARY_REPLAY_READY_ROWS}")
        blockers.append("NEED_REAL_CACHED_CLOB_WINDOWS")
        blockers.append("NEED_REAL_CACHED_SPOT_CANDLES")
        blockers.append("NEED_RESOLVED_UPDOWN_LABELS")
    return blockers


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_expansion_plan.json"
    md_path = root / "latest_expansion_plan.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 38 Replay Evidence Expansion Plan",
        "",
        "Plan to expand pm_crypto_updown_repricing_lag replay-ready evidence.",
        "",
        f"Current replay-ready rows: {payload['current_replay_ready_row_count']}",
        f"Current primary evidence rows: {payload['current_primary_evidence_row_count']}",
        f"Target primary rows: {payload['target_primary_replay_ready_rows']}",
        f"Rows needed: {payload['rows_needed_from_current']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        "",
        "## Blockers",
    ]
    lines.extend(f"- {item}" for item in (payload["blockers"] or ["None"]))
    lines.extend(["", "## Manual Commands"])
    lines.extend(f"- `{item}`" for item in payload["manual_capture_commands"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
