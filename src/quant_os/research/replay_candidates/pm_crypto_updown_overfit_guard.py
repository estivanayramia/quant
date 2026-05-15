from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from quant_os.research.replay_candidates.pm_crypto_updown_policy_replay_eval import (
    MIN_ALLOWED_SHADOW_INTENTS,
)
from quant_os.research.replay_candidates.pm_crypto_updown_schema import CANDIDATE_ID
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY


@dataclass(frozen=True)
class PmCryptoUpdownOverfitGuardConfig:
    min_allowed_primary_intents: int = MIN_ALLOWED_SHADOW_INTENTS
    min_allowed_real_cached_intents: int = 3
    min_filtered_rows: int = MIN_ALLOWED_SHADOW_INTENTS
    max_one_row_contribution_share: float = 0.50
    max_placebo_similarity_margin: float = 0.01


DEFAULT_OVERFIT_GUARD_CONFIG = PmCryptoUpdownOverfitGuardConfig()


def evaluate_pm_crypto_updown_overfit_guard(
    *,
    diagnostics: dict[str, Any],
    discriminator_report: dict[str, Any],
    config: PmCryptoUpdownOverfitGuardConfig = DEFAULT_OVERFIT_GUARD_CONFIG,
) -> dict[str, Any]:
    blockers = _blockers(
        diagnostics=diagnostics,
        discriminator_report=discriminator_report,
        config=config,
    )
    status = _status(blockers)
    return {
        "schema_version": "pm_crypto_updown_overfit_guard_v1",
        "sequence": "44",
        "candidate_id": CANDIDATE_ID,
        "status": status,
        "passes": status == "PASSES_ANTI_OVERFIT_GUARD",
        "blockers": blockers,
        "minimum_allowed_primary_intents": config.min_allowed_primary_intents,
        "minimum_allowed_real_cached_intents": config.min_allowed_real_cached_intents,
        "minimum_filtered_rows": config.min_filtered_rows,
        "maximum_one_row_contribution_share": config.max_one_row_contribution_share,
        "maximum_placebo_similarity_margin": config.max_placebo_similarity_margin,
        "network_fetch_attempted": False,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _blockers(
    *,
    diagnostics: dict[str, Any],
    discriminator_report: dict[str, Any],
    config: PmCryptoUpdownOverfitGuardConfig,
) -> list[str]:
    blockers = []
    allowed_primary = int(diagnostics.get("allowed_primary_intent_count", 0))
    allowed_real_cached = int(diagnostics.get("allowed_real_cached_intent_count", 0))
    if allowed_primary < config.min_allowed_primary_intents:
        blockers.append(
            f"ALLOWED_PRIMARY_INTENTS_{allowed_primary}_LT_{config.min_allowed_primary_intents}"
        )
    if allowed_real_cached < config.min_allowed_real_cached_intents:
        blockers.append(
            "ALLOWED_REAL_CACHED_INTENTS_"
            f"{allowed_real_cached}_LT_{config.min_allowed_real_cached_intents}"
        )
    for discriminator in discriminator_report.get("discriminators", []):
        if int(discriminator.get("rows_kept", 0)) < config.min_filtered_rows:
            blockers.append(
                "DISCRIMINATOR_"
                f"{discriminator['name']}_ROWS_{discriminator.get('rows_kept', 0)}"
                f"_LT_{config.min_filtered_rows}"
            )
        if discriminator.get("diagnostic_only"):
            blockers.append(f"DISCRIMINATOR_{discriminator['name']}_DIAGNOSTIC_ONLY")
        if not discriminator.get("threshold_predeclared", False):
            blockers.append(f"DISCRIMINATOR_{discriminator['name']}_THRESHOLD_NOT_PREDECLARED")
    one_row_share = float(diagnostics.get("one_row_dominance_share") or 0.0)
    if one_row_share > config.max_one_row_contribution_share:
        blockers.append(
            "ONE_ROW_DOMINANCE_SHARE_"
            f"{one_row_share:.3f}_GT_{config.max_one_row_contribution_share:.3f}"
        )
    placebo_similarity = float(diagnostics.get("placebo_similarity_score") or 1.0)
    if placebo_similarity <= config.max_placebo_similarity_margin:
        blockers.append(
            "PLACEBO_SIMILARITY_MARGIN_"
            f"{placebo_similarity:.3f}_LTE_{config.max_placebo_similarity_margin:.3f}"
        )
    synthetic = int(diagnostics.get("allowed_synthetic_diagnostic_intent_count", 0))
    if synthetic >= allowed_primary and synthetic > 0:
        blockers.append("SYNTHETIC_DIAGNOSTIC_ROWS_DOMINATE_ALLOWED_SET")
    if diagnostics.get("synthetic_rows_counted_as_primary"):
        blockers.append("SYNTHETIC_PROOF_INFLATION_BLOCKED")
    return _dedupe(blockers)


def _status(blockers: list[str]) -> str:
    if not blockers:
        return "PASSES_ANTI_OVERFIT_GUARD"
    if any(item.startswith("ALLOWED_PRIMARY_INTENTS_") for item in blockers):
        return "ALLOWED_INTENTS_TOO_THIN"
    if any(item.startswith("ALLOWED_REAL_CACHED_INTENTS_") for item in blockers):
        return "REAL_CACHED_INTENTS_TOO_THIN"
    if any(item.startswith("ONE_ROW_DOMINANCE_SHARE_") for item in blockers):
        return "ONE_ROW_DOMINANCE"
    if any(item.startswith("PLACEBO_SIMILARITY_MARGIN_") for item in blockers):
        return "PLACEBO_SIMILARITY_TOO_HIGH"
    if any("DIAGNOSTIC_ONLY" in item for item in blockers):
        return "DISCRIMINATOR_DIAGNOSTIC_ONLY"
    return "OVERFIT_RISK_TOO_HIGH"


def _dedupe(items: list[str]) -> list[str]:
    deduped = []
    seen = set()
    for item in items:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped
