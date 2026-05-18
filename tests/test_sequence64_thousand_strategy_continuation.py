from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def test_sequence64_generates_second_1000_without_reusing_variant_ids(
    local_project: Path,
) -> None:
    from quant_os.research.strategy_factory.strategy_variant_generator import (
        generate_strategy_variants,
        write_strategy_variants_report,
    )

    batch1 = generate_strategy_variants(target_count=1000, batch_index=1)
    batch2 = generate_strategy_variants(target_count=1000, batch_index=2)
    batch1_report = write_strategy_variants_report(
        output_root=local_project,
        target_count=1000,
        batch_index=1,
    )
    batch2_report = write_strategy_variants_report(
        output_root=local_project,
        target_count=1000,
        batch_index=2,
    )

    assert len(batch1) == 1000
    assert len(batch2) == 1000
    assert {variant["id"] for variant in batch1}.isdisjoint({variant["id"] for variant in batch2})
    assert batch1_report["batch_index"] == 1
    assert batch2_report["batch_index"] == 2
    assert batch2_report["variant_count"] == 1000
    assert batch2_report["cumulative_variant_count"] == 2000
    assert batch2_report["pre_registered_before_testing"] is True
    assert all(variant["batch_index"] == 2 for variant in batch2)
    assert all(variant["no_live_metadata"]["actual_order_count"] == 0 for variant in batch2)


def test_sequence64_next_tranche_tournament_updates_cumulative_checkpoint(
    local_project: Path,
) -> None:
    from quant_os.research.strategy_factory.strategy_tournament import (
        write_next_strategy_tranche_report,
        write_strategy_tournament_report,
    )

    first = write_strategy_tournament_report(output_root=local_project, batch_index=1)
    second = write_strategy_tournament_report(output_root=local_project, batch_index=2)
    state = json.loads(
        (
            local_project / "reports/thousand_strategy_campaign/state/latest_state.json"
        ).read_text(encoding="utf-8")
    )

    assert first["batch_index"] == 1
    assert second["batch_index"] == 2
    assert second["variants_generated"] == 1000
    assert second["cumulative_variants_generated"] == 2000
    assert second["variants_tested"] == 250
    assert second["cumulative_variants_tested"] == 500
    assert second["campaign_complete"] is False
    assert state["campaign_status"] == "THOUSAND_STRATEGY_CAMPAIGN_CHECKPOINTED_NOT_COMPLETE"
    assert state["variants_generated"] == 2000
    assert state["variants_tested"] == 500
    assert state["last_completed_batch_index"] == 2
    assert state["manual_canary_packet_status"] == "FIRST_TINY_MANUAL_CANARY_PACKET_BLOCKED"

    dynamic_third = write_next_strategy_tranche_report(output_root=local_project)
    state_after_dynamic = json.loads(
        (
            local_project / "reports/thousand_strategy_campaign/state/latest_state.json"
        ).read_text(encoding="utf-8")
    )
    assert dynamic_third["batch_index"] == 3
    assert dynamic_third["cumulative_variants_generated"] == 3000
    assert dynamic_third["cumulative_variants_tested"] == 750
    assert state_after_dynamic["last_completed_batch_index"] == 3
    assert state_after_dynamic["exact_resume_command"] == ".\\make.cmd thousand-strategy-next-tranche"


def test_sequence64_next_tranche_cli_and_make_target_are_data_only(local_project: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = {**os.environ, "PYTHONPATH": str(repo_root / "src")}
    commands = [
        [
            sys.executable,
            "-m",
            "quant_os.cli",
            "research",
            "generate-strategy-variants",
            "--batch-index",
            "2",
        ],
        [
            sys.executable,
            "-m",
            "quant_os.cli",
            "research",
            "strategy-tournament",
            "--batch-index",
            "2",
        ],
        [sys.executable, "-m", "quant_os.cli", "research", "strategy-next-tranche"],
    ]

    for command in commands:
        result = subprocess.run(
            command,
            cwd=local_project,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert "ORDER_SENT" not in result.stdout
        assert "LIVE_READY" not in result.stdout

    make_cmd = (repo_root / "make.cmd").read_text(encoding="utf-8")
    assert 'if "%TARGET%"=="thousand-strategy-next-tranche"' in make_cmd
    assert 'if "%TARGET%"=="sequence64-smoke"' in make_cmd
