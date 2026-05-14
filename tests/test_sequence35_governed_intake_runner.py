from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

SOURCE_CONFIG = Path("configs/research_intake_sources.yaml")


def test_sequence35_source_policy_fails_closed_and_rejects_unsafe_modes(
    local_project: Path,
) -> None:
    from quant_os.research.intake.source_config import write_source_policy_report
    from quant_os.research.intake.source_policy import evaluate_source_policy

    payload = write_source_policy_report(
        source_config_path=SOURCE_CONFIG,
        output_root=local_project,
    )

    assert payload["schema_version"] == "research_intake_source_policy_v1"
    assert payload["default_network_allowed"] is False
    assert payload["manual_network_fetch_enabled"] is False
    assert payload["allowed_source_count"] == 3
    assert payload["blocked_source_count"] == 2
    assert "blocked_evasive_source" in payload["blocked_source_ids"]
    assert payload["anti_bot_bypass_enabled"] is False
    assert payload["execution_authority"] == "NONE"

    unsafe = evaluate_source_policy(
        {
            "source_id": "unsafe_evasion",
            "allowed_fetch_mode": "STEALTH_EVASION",
            "network_allowed_by_default": True,
            "requires_manual_approval": False,
        }
    )
    assert unsafe["policy_status"] == "BLOCKED"
    assert "UNSAFE_OR_UNSUPPORTED_FETCH_MODE" in unsafe["blockers"]


def test_sequence35_scrapling_adapter_parses_cached_artifacts_without_dependency(
    local_project: Path,
) -> None:
    from quant_os.research.intake.artifact_fetcher import write_artifact_fetch_report

    payload = write_artifact_fetch_report(
        source_config_path=SOURCE_CONFIG,
        output_root=local_project,
        force_scrapling_absent=True,
    )

    assert payload["schema_version"] == "research_artifact_fetch_report_v1"
    assert payload["scrapling_available"] is False
    assert payload["manual_network_fetch_enabled"] is False
    assert payload["network_fetch_attempted"] is False
    assert payload["fetched_artifact_count"] == 3
    assert payload["rejected_source_count"] == 2
    assert any(
        artifact["source_id"] == "cached_research_page"
        and "Timestamped replay datasets" in artifact["text"]
        for artifact in payload["artifacts"]
    )
    assert all("anti_bot" not in artifact["fetch_method"] for artifact in payload["artifacts"])


def test_sequence35_intake_runner_dedupes_and_updates_research_outputs(
    local_project: Path,
) -> None:
    from quant_os.research.intake.intake_run_report import write_intake_run_report

    first = write_intake_run_report(
        source_config_path=SOURCE_CONFIG,
        output_root=local_project,
    )
    second = write_intake_run_report(
        source_config_path=SOURCE_CONFIG,
        output_root=local_project,
    )

    assert first["schema_version"] == "research_intake_run_v1"
    assert first["run_id"] == second["run_id"]
    assert first["artifact_count"] == 3
    assert first["duplicate_count"] == 1
    assert first["rejected_source_count"] == 2
    assert first["hypothesis_count"] >= 6
    assert first["task_count"] >= 6
    assert first["evidence_plan_updates"]["phase33_blocker_addressed"] == "BLOCKED_BY_THIN_EVIDENCE"
    assert first["live_trading_enabled"] is False
    assert first["execution_authority"] == "NONE"


def test_sequence35_knowledge_ledger_tracks_hash_dedupe_and_promotions(
    local_project: Path,
) -> None:
    from quant_os.research.intake.intake_run_report import write_intake_run_report
    from quant_os.research.intake.knowledge_ledger import write_knowledge_ledger_summary

    run = write_intake_run_report(
        source_config_path=SOURCE_CONFIG,
        output_root=local_project,
    )
    payload = write_knowledge_ledger_summary(
        intake_run=run,
        output_root=local_project,
    )

    assert payload["schema_version"] == "research_knowledge_ledger_summary_v1"
    assert payload["unique_artifact_count"] == 2
    assert payload["duplicate_artifact_count"] == 1
    assert "PROMOTED_TO_EVIDENCE_PLAN" in payload["status_counts"]
    assert "DUPLICATE" in payload["status_counts"]
    assert all(entry["artifact_hash"] for entry in payload["entries"])
    assert payload["ledger_generated_under_reports"] is True


def test_sequence35_evidence_to_shadow_bridge_maps_tasks_to_existing_blockers(
    local_project: Path,
) -> None:
    from quant_os.research.intake.evidence_to_shadow_report import (
        write_evidence_to_shadow_report,
    )

    payload = write_evidence_to_shadow_report(
        source_config_path=SOURCE_CONFIG,
        output_root=local_project,
    )

    assert payload["schema_version"] == "evidence_to_shadow_bridge_v1"
    assert payload["bridge_status"] == "MAPPED_RESEARCH_TASKS_TO_SHADOW_BLOCKERS"
    assert "BLOCKED_BY_THIN_EVIDENCE" in payload["targeted_blockers"]
    assert "SHADOW_EVIDENCE_TOO_THIN" in payload["targeted_blockers"]
    assert any(item["can_help_shadow_proving"] for item in payload["task_mappings"])
    assert any(item["rejected_as_hype_or_unsafe"] for item in payload["task_mappings"])
    for mapping in payload["task_mappings"]:
        assert mapping["expected_validation_command"].startswith(".\\make.cmd")
        assert mapping["direct_execution_allowed"] is False


def test_sequence35_autonomy_milestones_are_finite_explicit_and_block_live(
    local_project: Path,
) -> None:
    from quant_os.readiness.autonomy_milestone_report import write_autonomy_milestone_report

    payload = write_autonomy_milestone_report(output_root=local_project)

    assert payload["schema_version"] == "autonomy_milestones_v1"
    assert payload["milestone_count"] == 12
    assert [item["milestone_index"] for item in payload["milestones"]] == list(range(1, 13))
    assert payload["live_orders_allowed"] is False
    assert payload["next_required_milestone"]["milestone_id"] == "evidence_acquisition_repeatable"
    assert payload["milestones"][0]["status"] == "MET"
    assert payload["milestones"][-1]["required_for_live_orders"] is True
    assert all(item["required_next_action"] for item in payload["milestones"])


def test_sequence35_cli_commands_are_fixture_safe_and_non_executing(
    local_project: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = {
        **os.environ,
        "PYTHONPATH": str(repo_root / "src"),
    }
    commands = [
        [sys.executable, "-m", "quant_os.cli", "research", "intake-source-policy"],
        [sys.executable, "-m", "quant_os.cli", "research", "intake-run"],
        [sys.executable, "-m", "quant_os.cli", "research", "knowledge-ledger-summary"],
        [sys.executable, "-m", "quant_os.cli", "research", "evidence-to-shadow-bridge"],
        [sys.executable, "-m", "quant_os.cli", "readiness", "autonomy-milestones"],
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


def test_sequence35_modules_do_not_expose_live_scraping_or_social_execution_authority() -> None:
    source_paths = [
        Path("src/quant_os/research/intake/source_policy.py"),
        Path("src/quant_os/research/intake/scrapling_adapter.py"),
        Path("src/quant_os/research/intake/artifact_fetcher.py"),
        Path("src/quant_os/research/intake/intake_runner.py"),
        Path("src/quant_os/research/intake/evidence_to_shadow_bridge.py"),
        Path("src/quant_os/readiness/autonomy_milestones.py"),
    ]
    forbidden_tokens = [
        "create_order",
        "cancel_order",
        "post_order",
        "private_key",
        "wallet_signer",
        "sign_order",
        "captcha_bypass",
        "proxy_rotation",
        "stealth_evasion",
        "copy_trading_enabled = True",
    ]

    for path in source_paths:
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        for token in forbidden_tokens:
            assert token not in lowered
