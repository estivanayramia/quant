from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from quant_os.research.replay_candidates.pm_crypto_updown_allowed_intent_diagnostics import (
    evaluate_pm_crypto_updown_allowed_intent_diagnostics,
)
from quant_os.research.replay_candidates.pm_crypto_updown_policy_replay_eval import (
    MIN_ALLOWED_SHADOW_INTENTS,
)
from quant_os.research.replay_candidates.pm_crypto_updown_schema import CANDIDATE_ID
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

REPORT_ROOT = Path("reports/sequence45/allowed_intent_acquisition")
TARGET_ALLOWED_REAL_CACHED_INTENTS = 3

REQUIRED_NEW_WINDOW_PROPERTIES = [
    "sufficient_spot_lag_signal",
    "underreaction_gap",
    "acceptable_spread",
    "sufficient_liquidity",
    "non_stale_clob",
    "enough_time_to_window_end",
    "cost_fill_surviving_limit_price_discipline",
    "resolved_label",
    "no_synthetic_proof_dependency",
]


def build_pm_crypto_updown_allowed_intent_acquisition_plan(
    *,
    diagnostics: dict[str, Any] | None = None,
    fixture_root: str | Path | None = None,
    real_cached_artifact_roots: list[str | Path] | None = None,
) -> dict[str, Any]:
    diagnostics = diagnostics or evaluate_pm_crypto_updown_allowed_intent_diagnostics(
        fixture_root=fixture_root,
        real_cached_artifact_roots=real_cached_artifact_roots,
    )
    current_allowed_primary = int(diagnostics["allowed_primary_intent_count"])
    current_allowed_real_cached = int(diagnostics["allowed_real_cached_intent_count"])
    required_primary = max(MIN_ALLOWED_SHADOW_INTENTS - current_allowed_primary, 0)
    required_real_cached = max(TARGET_ALLOWED_REAL_CACHED_INTENTS - current_allowed_real_cached, 0)
    estimated_windows = _estimate_additional_windows(required_primary, required_real_cached)
    capture_status = (
        "ALLOWED_INTENT_TARGET_REACHED"
        if required_primary == 0 and required_real_cached == 0
        else "OPERATOR_ACTION_REQUIRED"
    )
    return {
        "schema_version": "pm_crypto_updown_allowed_intent_acquisition_plan_v1",
        "sequence": "45",
        "candidate_id": CANDIDATE_ID,
        "capture_or_import_status": capture_status,
        "current_allowed_primary_intents": current_allowed_primary,
        "target_allowed_primary_intents": MIN_ALLOWED_SHADOW_INTENTS,
        "current_allowed_real_cached_intents": current_allowed_real_cached,
        "target_allowed_real_cached_intents": TARGET_ALLOWED_REAL_CACHED_INTENTS,
        "allowed_synthetic_diagnostic_intents": int(
            diagnostics.get("allowed_synthetic_diagnostic_intent_count", 0)
        ),
        "required_additional_allowed_primary_intents": required_primary,
        "required_additional_allowed_real_cached_intents": required_real_cached,
        "estimated_additional_two_token_windows_required": estimated_windows,
        "required_new_window_properties": REQUIRED_NEW_WINDOW_PROPERTIES,
        "window_property_details": {
            "sufficient_spot_lag_signal": "spot move survives the predeclared signal threshold",
            "underreaction_gap": "predicted probability clears observed ask after costs",
            "acceptable_spread": "CLOB spread remains inside conservative shadow policy",
            "sufficient_liquidity": "displayed liquidity is above the shadow policy floor",
            "non_stale_clob": "snapshot age and quality flags do not mark stale CLOB data",
            "enough_time_to_window_end": "intent is not expiry-adjacent",
            "cost_fill_surviving_limit_price_discipline": (
                "hypothetical limit price stays under the max acceptable price"
            ),
            "resolved_label": "window has a resolved UP/DOWN label",
            "no_synthetic_proof_dependency": "synthetic rows remain diagnostic only",
        },
        "operator_commands": _operator_commands(estimated_windows),
        "missing_coverage_report": _missing_coverage_report(
            required_primary=required_primary,
            required_real_cached=required_real_cached,
            estimated_windows=estimated_windows,
        ),
        "network_capture_possible_with_current_code": False,
        "network_capture_status": (
            "DATA_CAPTURE_BLOCKED"
            if required_primary > 0 or required_real_cached > 0
            else "NOT_REQUIRED"
        ),
        "capture_artifacts_are_ignored_by_default": True,
        "ci_network_dependency": False,
        "manual_network_flag": "--manual-network-ok",
        "synthetic_rows_counted_as_primary": False,
        "network_fetch_attempted": False,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_pm_crypto_updown_allowed_intent_acquisition_plan(
    *,
    diagnostics: dict[str, Any] | None = None,
    fixture_root: str | Path | None = None,
    real_cached_artifact_roots: list[str | Path] | None = None,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    payload = build_pm_crypto_updown_allowed_intent_acquisition_plan(
        diagnostics=diagnostics,
        fixture_root=fixture_root,
        real_cached_artifact_roots=real_cached_artifact_roots,
    )
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _estimate_additional_windows(required_primary: int, required_real_cached: int) -> int:
    if required_primary <= 0 and required_real_cached <= 0:
        return 0
    # This is intentionally conservative: a two-token window is not assumed to
    # yield two allowed intents after cost/fill and discriminator filters.
    return max(required_primary, required_real_cached, math.ceil(required_primary / 2))


def _operator_commands(estimated_windows: int) -> list[str]:
    return [
        "python -m quant_os.cli data pm-crypto-updown-capture-plan --manual-network-ok --run-id <run_id>",
        "Save public read-only Gamma/CLOB, spot, and resolution artifacts under data/external/manual_captures/pm_crypto_updown/<run_id>/artifacts.jsonl",
        "python -m quant_os.cli data pm-crypto-updown-real-cached-import --real-cached-root data/external/manual_captures/pm_crypto_updown/<run_id>",
        "python -m quant_os.cli research pm-crypto-updown-allowed-intent-progress --real-cached-root tests/fixtures/replay_candidates/pm_crypto_updown/real_cached_sample --real-cached-root data/external/manual_captures/pm_crypto_updown/<run_id>",
        "python -m quant_os.cli readiness pm-crypto-updown-allowed-intent-decision --real-cached-root tests/fixtures/replay_candidates/pm_crypto_updown/real_cached_sample --real-cached-root data/external/manual_captures/pm_crypto_updown/<run_id>",
        f"Repeat until at least {estimated_windows} additional two-token windows have been evaluated.",
    ]


def _missing_coverage_report(
    *,
    required_primary: int,
    required_real_cached: int,
    estimated_windows: int,
) -> dict[str, Any]:
    return {
        "required_additional_allowed_primary_intents": required_primary,
        "required_additional_allowed_real_cached_intents": required_real_cached,
        "estimated_additional_two_token_windows_required": estimated_windows,
        "missing_window_properties": REQUIRED_NEW_WINDOW_PROPERTIES
        if estimated_windows > 0
        else [],
        "blocker_if_not_collected": (
            "NEEDS_MORE_ALLOWED_INTENTS"
            if required_primary > 0
            else "NEEDS_MORE_REAL_CACHED_EVIDENCE"
            if required_real_cached > 0
            else "NONE"
        ),
    }


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_allowed_intent_acquisition_plan.json"
    md_path = root / "latest_allowed_intent_acquisition_plan.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 45 Allowed Intent Acquisition Plan",
        "",
        "Targets allowed intents, not generic rows. Synthetic evidence remains diagnostic only.",
        "",
        f"Status: {payload['capture_or_import_status']}",
        f"Allowed primary intents: {payload['current_allowed_primary_intents']} / {payload['target_allowed_primary_intents']}",
        f"Allowed real-cached intents: {payload['current_allowed_real_cached_intents']} / {payload['target_allowed_real_cached_intents']}",
        f"Additional allowed primary intents required: {payload['required_additional_allowed_primary_intents']}",
        f"Additional allowed real-cached intents required: {payload['required_additional_allowed_real_cached_intents']}",
        f"Estimated additional two-token windows required: {payload['estimated_additional_two_token_windows_required']}",
        f"Network capture possible with current code: {payload['network_capture_possible_with_current_code']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        "",
        "## Required Window Properties",
    ]
    lines.extend(f"- {item}" for item in payload["required_new_window_properties"])
    lines.extend(["", "## Operator Commands"])
    lines.extend(f"- `{item}`" for item in payload["operator_commands"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
