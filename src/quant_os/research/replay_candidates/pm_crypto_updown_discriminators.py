from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quant_os.research.replay_candidates.pm_crypto_updown_baselines import (
    evaluate_pm_crypto_updown_baselines,
)
from quant_os.research.replay_candidates.pm_crypto_updown_placebos import (
    run_pm_crypto_updown_placebos,
)
from quant_os.research.replay_candidates.pm_crypto_updown_policy_replay_eval import (
    MIN_ALLOWED_SHADOW_INTENTS,
)
from quant_os.research.replay_candidates.pm_crypto_updown_schema import CANDIDATE_ID
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

DiscriminatorRule = Callable[[dict[str, Any], dict[str, Any]], bool]


def evaluate_pm_crypto_updown_discriminators(
    *,
    diagnostics: dict[str, Any],
) -> dict[str, Any]:
    rows = diagnostics["allowed_primary_rows"]
    signal_report = diagnostics["allowed_primary_signal_report"]
    rules = [
        _rule(
            "SPOT_LAG_STRENGTH",
            "abs(spot_return_5s) >= 0.00015",
            "Require a spot move large enough to reduce micro-move noise.",
            ["Strong spot moves can reverse before the prediction-market window resolves."],
            lambda row, _decision: abs(float(row.get("spot_return_5s") or 0.0)) >= 0.00015,
        ),
        _rule(
            "MARKET_UNDERREACTION_GAP",
            "predicted_probability - market_ask >= 0.03",
            "Require the signal probability to clear observed ask by a visible margin.",
            ["The market may already encode information not present in the local fixture."],
            lambda row, decision: float(decision["predicted_probability"])
            - float(row["market_ask"])
            >= 0.03,
        ),
        _rule(
            "SPREAD_QUALITY_FILTER",
            "market_spread <= 0.03",
            "Require narrow enough spread that costs do not dominate the candidate signal.",
            ["A narrow spread does not guarantee passive fill quality."],
            lambda row, _decision: float(row.get("market_spread") or 0.0) <= 0.03,
        ),
        _rule(
            "LIQUIDITY_QUALITY_FILTER",
            "market_liquidity >= 250",
            "Require enough displayed liquidity to avoid obviously thin books.",
            ["Displayed liquidity can disappear before a hypothetical limit order rests."],
            lambda row, _decision: float(row.get("market_liquidity") or 0.0) >= 250.0,
        ),
        _rule(
            "TIME_TO_WINDOW_END_FILTER",
            "seconds_to_window_end >= 15",
            "Avoid expiry-adjacent microstructure in the allowed-intent diagnostic set.",
            ["More time to expiry can also give the original signal more time to decay."],
            lambda row, _decision: float(row.get("seconds_to_window_end") or 0.0) >= 15.0,
        ),
    ]
    simple_results = [_evaluate_rule(rule, rows, signal_report) for rule in rules]
    combined = _evaluate_rule(
        _rule(
            "COMBINED_CONSERVATIVE_FILTER",
            "all predeclared discriminator filters pass",
            "Require the allowed intent to survive all transparent conservative filters.",
            ["Combining filters can leave a subset too small for promotion."],
            lambda row, decision: all(rule["predicate"](row, decision) for rule in rules),
        ),
        rows,
        signal_report,
    )
    return {
        "schema_version": "pm_crypto_updown_discriminators_v1",
        "sequence": "44",
        "candidate_id": CANDIDATE_ID,
        "input_allowed_primary_count": len(rows),
        "discriminators": simple_results + [combined],
        "network_fetch_attempted": False,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _rule(
    name: str,
    rule: str,
    rationale: str,
    failure_modes: list[str],
    predicate: DiscriminatorRule,
) -> dict[str, Any]:
    return {
        "name": name,
        "rule": rule,
        "rationale": rationale,
        "failure_modes": failure_modes,
        "predicate": predicate,
    }


def _evaluate_rule(
    rule: dict[str, Any],
    rows: list[dict[str, Any]],
    signal_report: dict[str, Any],
) -> dict[str, Any]:
    decisions = {str(item["row_id"]): item for item in signal_report["row_decisions"]}
    kept = [
        row
        for row in rows
        if rule["predicate"](row, decisions[str(row["clob_snapshot_id"])])
    ]
    kept_ids = [row["clob_snapshot_id"] for row in kept]
    filtered_signal_report = _filter_signal_report(
        signal_report=signal_report,
        row_ids=kept_ids,
    )
    baselines = evaluate_pm_crypto_updown_baselines(
        rows=kept,
        signal_report=filtered_signal_report,
    )
    placebos = run_pm_crypto_updown_placebos(
        rows=kept,
        signal_report=filtered_signal_report,
    )
    diagnostic_only = len(kept) < MIN_ALLOWED_SHADOW_INTENTS
    return {
        "name": rule["name"],
        "rule": rule["rule"],
        "rationale": rule["rationale"],
        "failure_modes": rule["failure_modes"],
        "threshold_predeclared": True,
        "rows_kept": len(kept),
        "rows_rejected": len(rows) - len(kept),
        "kept_row_ids": kept_ids,
        "rejected_row_ids": [
            row["clob_snapshot_id"] for row in rows if row["clob_snapshot_id"] not in kept_ids
        ],
        "result_vs_baseline": {
            "candidate_beats_market_baseline": baselines["candidate_beats_market_baseline"],
            "candidate_beats_no_skill": baselines["candidate_beats_no_skill"],
            "promotion_claimed": False,
        },
        "result_vs_placebo": {
            "candidate_beats_placebos_for_readiness": placebos[
                "candidate_beats_placebos_for_readiness"
            ],
            "placebo_comparison_status": placebos["placebo_comparison_status"],
            "promotion_claimed": False,
        },
        "diagnostic_only": diagnostic_only,
    }


def _filter_signal_report(
    *,
    signal_report: dict[str, Any],
    row_ids: list[str],
) -> dict[str, Any]:
    allowed = set(row_ids)
    decisions = [
        item for item in signal_report["row_decisions"] if str(item["row_id"]) in allowed
    ]
    return {
        **signal_report,
        "row_decisions": decisions,
        "candidate_signal_count": len([item for item in decisions if item["side"] == "BUY"]),
        "blocked_row_count": sum(1 for item in decisions if item.get("blocked")),
    }
