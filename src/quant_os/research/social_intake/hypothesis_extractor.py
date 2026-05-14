from __future__ import annotations

from typing import Any

from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY


def extract_social_hypotheses(*, classifications: dict[str, Any]) -> dict[str, Any]:
    hypotheses = [
        _hypothesis_from_classification(item)
        for item in classifications["classifications"]
        if item["can_be_falsifiable_research_task"]
    ]
    return {
        "schema_version": "social_hypothesis_queue_v1",
        "sequence": "34",
        "hypothesis_queue_status": "SOCIAL_RESEARCH_TASKS_ONLY",
        "hypothesis_count": len(hypotheses),
        "hypotheses": sorted(hypotheses, key=lambda item: item["hypothesis_id"]),
        "queue_policy": (
            "Hypotheses from social posts require timestamped data, baselines, replay, "
            "and safety constraints before they can inform future research."
        ),
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def _hypothesis_from_classification(item: dict[str, Any]) -> dict[str, Any]:
    primary = item["primary_category"]
    post_id = item["post_id"]
    template = _template(primary)
    return {
        "hypothesis_id": f"social_{post_id}_{template['hypothesis_type']}",
        "source_post_id": post_id,
        "source_url": item["source_url"],
        "hypothesis_type": template["hypothesis_type"],
        "claim_summary": template["claim_summary"],
        "lane_candidate": template["lane_candidate"],
        "required_data": template["required_data"],
        "measurable_variables": template["measurable_variables"],
        "baseline_comparison_required": True,
        "replay_feasibility": template["replay_feasibility"],
        "expected_failure_modes": template["expected_failure_modes"],
        "safety_constraints": [
            "social_post_not_trade_signal",
            "direct_execution_prohibited",
            *template["safety_constraints"],
        ],
        "do_not_trade_directly": True,
        "direct_execution_allowed": False,
        "classification_categories": item["categories"],
    }


def _template(primary: str) -> dict[str, Any]:
    templates = {
        "DATA_SOURCE_CANDIDATE": {
            "hypothesis_type": "source_candidate",
            "claim_summary": "Evaluate a read-only market data source candidate.",
            "lane_candidate": "evidence_acquisition",
            "required_data": [
                "license_and_cost_check",
                "coverage_sample",
                "schema_sample",
                "offline_fixture",
            ],
            "measurable_variables": ["coverage", "latency", "missingness", "cost"],
            "replay_feasibility": "source_registry_review_required",
            "expected_failure_modes": ["paid_only", "license_blocked", "thin_history"],
            "safety_constraints": ["read_only_source_candidate"],
        },
        "TOOLING_OR_WORKFLOW": {
            "hypothesis_type": "workflow_task",
            "claim_summary": "Turn reusable capture/research instructions into process tasks.",
            "lane_candidate": "research_workflow",
            "required_data": ["workflow_spec", "repeatability_check"],
            "measurable_variables": ["artifact_completeness", "repeatability"],
            "replay_feasibility": "not_a_market_signal",
            "expected_failure_modes": ["process_overhead_without_edge"],
            "safety_constraints": ["not_alpha"],
        },
        "REPLAY_OR_BACKTESTING_REFERENCE": {
            "hypothesis_type": "benchmark_reference",
            "claim_summary": "Compare open-source stack ideas for source/replay inspiration.",
            "lane_candidate": "replay_realism",
            "required_data": ["benchmark_notes", "fixture_safe_example"],
            "measurable_variables": ["replay_coverage", "architecture_fit"],
            "replay_feasibility": "benchmark_only",
            "expected_failure_modes": ["platform_sprawl", "agent_overreach"],
            "safety_constraints": ["no_execution_adoption"],
        },
        "MACRO_THESIS": {
            "hypothesis_type": "macro_hypothesis",
            "claim_summary": "Test a timestamped macro thesis against out-of-sample data.",
            "lane_candidate": "macro_feature_research",
            "required_data": ["timestamped_macro_series", "market_returns", "oos_split"],
            "measurable_variables": ["lead_lag", "hit_rate", "calibration_error"],
            "replay_feasibility": "requires_timestamped_dataset",
            "expected_failure_modes": ["lookahead_bias", "regime_instability"],
            "safety_constraints": ["oos_required"],
        },
        "MODEL_WARNING": {
            "hypothesis_type": "baseline_calibration_warning",
            "claim_summary": "Require baseline-first testing before model complexity.",
            "lane_candidate": "calibration_validation",
            "required_data": ["baseline_results", "model_results", "oos_split"],
            "measurable_variables": ["baseline_delta", "calibration_error"],
            "replay_feasibility": "validation_gate",
            "expected_failure_modes": ["average_regression", "overfit_model"],
            "safety_constraints": ["baseline_required"],
        },
        "COPY_TRADE_UNSAFE": {
            "hypothesis_type": "unsafe_copy_trade_research",
            "claim_summary": "Reject direct following and only allow timestamped replay study.",
            "lane_candidate": "unsafe_research_only",
            "required_data": ["timestamped_actor_dataset", "independent_market_baseline"],
            "measurable_variables": ["lagged_return", "drawdown", "slippage_burden"],
            "replay_feasibility": "requires_timestamped_dataset",
            "expected_failure_modes": ["selection_bias", "identity_hype", "unreplayable_claim"],
            "safety_constraints": ["unsafe_copy_trade_rejected"],
        },
    }
    return templates.get(
        primary,
        {
            "hypothesis_type": "manual_review",
            "claim_summary": "Manual review required before research conversion.",
            "lane_candidate": "research_triage",
            "required_data": ["manual_review_notes"],
            "measurable_variables": ["review_outcome"],
            "replay_feasibility": "not_testable_yet",
            "expected_failure_modes": ["hype_without_data"],
            "safety_constraints": ["manual_review_required"],
        },
    )
