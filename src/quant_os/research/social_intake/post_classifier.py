from __future__ import annotations

from typing import Any

from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

ALL_CATEGORIES = [
    "DATA_SOURCE_CANDIDATE",
    "TOOLING_OR_WORKFLOW",
    "REPLAY_OR_BACKTESTING_REFERENCE",
    "SIGNAL_HYPOTHESIS",
    "MACRO_THESIS",
    "MODEL_WARNING",
    "COPY_TRADE_UNSAFE",
    "WALLET_OR_INFLUENCER_FOLLOWING_UNSAFE",
    "HYPE_OR_LOW_SIGNAL",
    "NEEDS_MANUAL_REVIEW",
]


def classify_social_posts(*, inventory: dict[str, Any]) -> dict[str, Any]:
    classifications = [_classify_post(post) for post in inventory["posts"]]
    return {
        "schema_version": "social_post_classification_v1",
        "sequence": "34",
        "classification_status": "CLASSIFIED_SOCIAL_RESEARCH_ONLY",
        "categories": ALL_CATEGORIES,
        "post_count": len(classifications),
        "classifications": sorted(classifications, key=lambda item: item["post_id"]),
        "classification_policy": (
            "Social posts can create hypotheses, source candidates, risk filters, "
            "and replay tasks. They must not create direct trade logic."
        ),
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _classify_post(post: dict[str, Any]) -> dict[str, Any]:
    text = str(post["text"]).lower()
    categories = _categories(text)
    primary = categories[0]
    unsafe = any(category.endswith("_UNSAFE") for category in categories)
    return {
        "post_id": post["post_id"],
        "source_url": post["provenance"]["post_url"],
        "primary_category": primary,
        "categories": categories,
        "rationale": _rationale(primary),
        "confidence": _confidence(primary),
        "safety_flags": _safety_flags(categories),
        "can_be_falsifiable_research_task": primary != "HYPE_OR_LOW_SIGNAL",
        "must_never_be_direct_execution_logic": True,
        "direct_execution_allowed": False,
        "unsafe_copy_or_following": unsafe,
    }


def _categories(text: str) -> list[str]:
    categories = []
    if "open-source" in text or "benchmark" in text or "replay inspiration" in text:
        categories.append("REPLAY_OR_BACKTESTING_REFERENCE")
    if "financialdatasets" in text or "mcp" in text:
        categories.append("DATA_SOURCE_CANDIDATE")
    if "spec" in text or "workflow" in text or "plan" in text or "tasks" in text:
        categories.append("TOOLING_OR_WORKFLOW")
    if "macro" in text or "liquidity" in text:
        categories.append("MACRO_THESIS")
    if "neural" in text or "baseline" in text or "calibration" in text:
        categories.append("MODEL_WARNING")
    if "copy" in text and ("wallet" in text or "trader" in text or "politician" in text):
        categories.append("COPY_TRADE_UNSAFE")
        categories.append("WALLET_OR_INFLUENCER_FOLLOWING_UNSAFE")
    if "signal" in text or "alpha" in text:
        categories.append("SIGNAL_HYPOTHESIS")
    if not categories:
        categories.extend(["HYPE_OR_LOW_SIGNAL", "NEEDS_MANUAL_REVIEW"])
    return _dedupe(categories)


def _rationale(primary: str) -> str:
    return {
        "DATA_SOURCE_CANDIDATE": "Mentions a potential read-only data/source integration.",
        "TOOLING_OR_WORKFLOW": "Useful as process or capture workflow improvement, not alpha.",
        "REPLAY_OR_BACKTESTING_REFERENCE": "Useful as benchmark or replay architecture inspiration.",
        "MACRO_THESIS": "Can become a timestamped out-of-sample macro hypothesis.",
        "MODEL_WARNING": "Warns that models require baseline-first calibration.",
        "COPY_TRADE_UNSAFE": "Copying wallets or people is unsafe execution logic.",
        "SIGNAL_HYPOTHESIS": "May be falsifiable only after data and replay conversion.",
        "HYPE_OR_LOW_SIGNAL": "Insufficient concrete research content.",
        "NEEDS_MANUAL_REVIEW": "Needs human review before research conversion.",
    }.get(primary, "Classified by deterministic social intake rules.")


def _confidence(primary: str) -> str:
    if primary in {"COPY_TRADE_UNSAFE", "DATA_SOURCE_CANDIDATE", "MODEL_WARNING"}:
        return "0.90"
    if primary in {"TOOLING_OR_WORKFLOW", "REPLAY_OR_BACKTESTING_REFERENCE"}:
        return "0.80"
    return "0.70"


def _safety_flags(categories: list[str]) -> list[str]:
    flags = ["SOCIAL_POST_NOT_TRADE_SIGNAL", "DIRECT_EXECUTION_PROHIBITED"]
    if "COPY_TRADE_UNSAFE" in categories:
        flags.append("COPY_TRADE_REJECTED")
    if "WALLET_OR_INFLUENCER_FOLLOWING_UNSAFE" in categories:
        flags.append("FOLLOWING_PEOPLE_OR_WALLETS_REJECTED")
    return flags


def _dedupe(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
