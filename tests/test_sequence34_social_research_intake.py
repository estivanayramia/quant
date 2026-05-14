from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

CAPTURE_ROOT = Path(__file__).parent / "fixtures" / "social_capture" / "x_capture_sample"


def test_sequence34_capture_inventory_is_deterministic_and_handles_missing_files(
    local_project: Path,
) -> None:
    from quant_os.research.social_intake.capture_loader import write_capture_inventory

    first = write_capture_inventory(capture_root=CAPTURE_ROOT, output_root=local_project)
    second = write_capture_inventory(capture_root=CAPTURE_ROOT, output_root=local_project)

    assert first["schema_version"] == "social_capture_inventory_v1"
    assert first["capture_root"] == str(CAPTURE_ROOT)
    assert first["post_count"] == 6
    assert first["posts"] == second["posts"]
    assert first["missing_optional_file_count"] > 0
    assert first["network_fetch_performed"] is False
    assert first["login_or_session_required"] is False
    assert first["secrets_detected"] is False
    nn_warning = next(post for post in first["posts"] if post["post_id"] == "nn_warning")
    assert "post.json" in nn_warning["missing_optional_files"]
    assert nn_warning["raw_text_sha256"]
    assert nn_warning["provenance"]["post_url"] == "https://x.example/neural-dice"
    assert (
        local_project
        / "reports"
        / "sequence34"
        / "social_intake"
        / "latest_capture_inventory.json"
    ).exists()


def test_sequence34_post_classification_is_stable_and_blocks_copy_trade_logic(
    local_project: Path,
) -> None:
    from quant_os.research.social_intake.post_classification_report import (
        write_post_classification_report,
    )

    payload = write_post_classification_report(
        capture_root=CAPTURE_ROOT,
        output_root=local_project,
    )
    by_id = {item["post_id"]: item for item in payload["classifications"]}

    assert payload["schema_version"] == "social_post_classification_v1"
    assert by_id["financialdatasets_mcp"]["primary_category"] == "DATA_SOURCE_CANDIDATE"
    assert by_id["spec_kit"]["primary_category"] == "TOOLING_OR_WORKFLOW"
    assert by_id["open_source_stack"]["primary_category"] == "REPLAY_OR_BACKTESTING_REFERENCE"
    assert by_id["macro_thesis"]["primary_category"] == "MACRO_THESIS"
    assert by_id["nn_warning"]["primary_category"] == "MODEL_WARNING"
    assert by_id["copy_wallet"]["primary_category"] == "COPY_TRADE_UNSAFE"
    assert "WALLET_OR_INFLUENCER_FOLLOWING_UNSAFE" in by_id["copy_wallet"]["categories"]
    assert by_id["copy_wallet"]["can_be_falsifiable_research_task"] is True
    assert by_id["copy_wallet"]["must_never_be_direct_execution_logic"] is True
    assert by_id["copy_wallet"]["direct_execution_allowed"] is False
    assert payload["live_trading_enabled"] is False
    assert payload["execution_authority"] == "NONE"


def test_sequence34_hypotheses_require_data_baselines_and_do_not_trade_directly(
    local_project: Path,
) -> None:
    from quant_os.research.social_intake.hypothesis_queue import (
        write_hypothesis_queue_report,
    )

    payload = write_hypothesis_queue_report(
        capture_root=CAPTURE_ROOT,
        output_root=local_project,
    )

    assert payload["schema_version"] == "social_hypothesis_queue_v1"
    assert payload["hypothesis_count"] == 6
    assert all(item["do_not_trade_directly"] is True for item in payload["hypotheses"])
    assert all(item["baseline_comparison_required"] is True for item in payload["hypotheses"])
    assert all(item["required_data"] for item in payload["hypotheses"])
    assert all(item["measurable_variables"] for item in payload["hypotheses"])
    copy_task = next(
        item for item in payload["hypotheses"] if item["source_post_id"] == "copy_wallet"
    )
    assert copy_task["hypothesis_type"] == "unsafe_copy_trade_research"
    assert "direct_execution_prohibited" in copy_task["safety_constraints"]
    assert copy_task["replay_feasibility"] == "requires_timestamped_dataset"
    source_task = next(
        item
        for item in payload["hypotheses"]
        if item["source_post_id"] == "financialdatasets_mcp"
    )
    assert source_task["hypothesis_type"] == "source_candidate"
    assert "license_and_cost_check" in source_task["required_data"]


def test_sequence34_research_tasks_prioritize_replay_evidence_over_hype(
    local_project: Path,
) -> None:
    from quant_os.research.social_intake.research_task_queue import (
        write_research_task_queue_report,
    )

    payload = write_research_task_queue_report(
        capture_root=CAPTURE_ROOT,
        output_root=local_project,
    )
    by_source = {task["source_post_id"]: task for task in payload["tasks"]}

    assert payload["schema_version"] == "social_research_task_queue_v1"
    assert by_source["financialdatasets_mcp"]["priority_status"] == "DO_NOW"
    assert by_source["macro_thesis"]["priority_status"] in {"DO_NEXT", "NEEDS_MORE_DATA"}
    assert by_source["copy_wallet"]["priority_status"] == "REJECT_UNSAFE"
    assert by_source["spec_kit"]["priority_status"] == "BACKLOG"
    assert by_source["open_source_stack"]["priority_status"] == "DO_NEXT"
    assert by_source["copy_wallet"]["direct_execution_allowed"] is False
    assert payload["top_priority_reason"] == "reduce_phase33_thin_evidence_blocker"


def test_sequence34_evidence_plan_targets_thin_evidence_without_social_signals(
    local_project: Path,
) -> None:
    from quant_os.research.social_intake.evidence_acquisition_report import (
        write_evidence_acquisition_report,
    )

    payload = write_evidence_acquisition_report(
        capture_root=CAPTURE_ROOT,
        output_root=local_project,
    )

    assert payload["schema_version"] == "social_evidence_acquisition_plan_v1"
    assert payload["phase33_blocker_addressed"] == "BLOCKED_BY_THIN_EVIDENCE"
    assert payload["social_posts_are_trade_signals"] is False
    assert payload["live_trading_enabled"] is False
    assert "timestamped_replay_datasets" in payload["data_needed"]
    assert "source_registry_candidate_review" in payload["source_candidates"]
    assert "copy_wallet" in payload["hypotheses_rejected"]
    assert any(
        item["source_post_id"] == "financialdatasets_mcp"
        for item in payload["hypotheses_worth_testing"]
    )
    assert (
        local_project
        / "reports"
        / "sequence34"
        / "evidence_acquisition"
        / "latest_evidence_plan.json"
    ).exists()


def test_sequence34_cli_commands_are_fixture_safe_and_non_executing(
    local_project: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = {
        **os.environ,
        "PYTHONPATH": str(repo_root / "src"),
    }
    commands = [
        [sys.executable, "-m", "quant_os.cli", "research", "social-capture-inventory"],
        [sys.executable, "-m", "quant_os.cli", "research", "social-post-classification"],
        [sys.executable, "-m", "quant_os.cli", "research", "social-hypothesis-queue"],
        [sys.executable, "-m", "quant_os.cli", "research", "social-task-queue"],
        [sys.executable, "-m", "quant_os.cli", "research", "evidence-acquisition-plan"],
    ]

    for command in commands:
        result = subprocess.run(
            command,
            cwd=local_project,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        assert "live_trading_enabled" in result.stdout
        assert "False" in result.stdout
        assert "execution_authority" in result.stdout
        assert "NONE" in result.stdout


def test_sequence34_modules_do_not_expose_live_or_social_execution_authority() -> None:
    source_paths = [
        Path("src/quant_os/research/social_intake/capture_loader.py"),
        Path("src/quant_os/research/social_intake/post_classifier.py"),
        Path("src/quant_os/research/social_intake/hypothesis_extractor.py"),
        Path("src/quant_os/research/social_intake/task_prioritizer.py"),
        Path("src/quant_os/research/social_intake/evidence_acquisition_plan.py"),
    ]
    forbidden_tokens = [
        "create_order",
        "cancel_order",
        "post_order",
        "private_key",
        "wallet_signer",
        "sign_order",
        "execute_social_signal",
        "copy_wallet_trade",
    ]

    for path in source_paths:
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        for token in forbidden_tokens:
            assert token not in lowered
