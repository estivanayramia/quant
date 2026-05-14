from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "replay_candidates" / "pm_crypto_updown"


def test_sequence38_expansion_plan_is_deterministic(local_project: Path) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_expansion_plan import (
        write_pm_crypto_updown_expansion_plan,
    )

    first = write_pm_crypto_updown_expansion_plan(
        fixture_root=FIXTURE_ROOT,
        output_root=local_project,
    )
    second = write_pm_crypto_updown_expansion_plan(
        fixture_root=FIXTURE_ROOT,
        output_root=local_project,
    )

    assert first == second
    assert first["schema_version"] == "pm_crypto_updown_expansion_plan_v1"
    assert first["candidate_id"] == "pm_crypto_updown_repricing_lag"
    assert first["target_primary_replay_ready_rows"] == 20
    assert first["current_replay_ready_row_count"] == 2
    assert first["current_primary_evidence_row_count"] == 2
    assert first["rows_needed_from_current"] == 18
    assert "public_clob_orderbook_snapshots" in first["required_clob_coverage"]
    assert "BTC-USD" in first["required_spot_coverage"]["symbols"]
    assert "NEED_REAL_CACHED_CLOB_WINDOWS" in first["blockers"]
    assert first["live_trading_enabled"] is False
    assert first["execution_authority"] == "NONE"
    assert (
        local_project
        / "reports"
        / "sequence38"
        / "evidence_expansion"
        / "latest_expansion_plan.json"
    ).exists()


def test_sequence38_manual_capture_plan_is_read_only_and_disabled_by_default(
    local_project: Path,
) -> None:
    from quant_os.data.prediction_markets.pm_updown_capture_plan import (
        write_pm_updown_manual_capture_plan,
    )

    payload = write_pm_updown_manual_capture_plan(output_root=local_project)

    assert payload["schema_version"] == "pm_updown_manual_capture_plan_v1"
    assert payload["manual_only"] is True
    assert payload["read_only"] is True
    assert payload["network_enabled"] is False
    assert payload["network_fetch_attempted"] is False
    assert payload["auth_required"] is False
    assert payload["wallet_required"] is False
    assert payload["signing_allowed"] is False
    assert payload["order_placement_allowed"] is False
    assert payload["order_cancellation_allowed"] is False
    assert payload["ci_network_dependency"] is False
    assert payload["manifest_written"] is True
    assert str(payload["capture_manifest_path"]).startswith("data/external/manual_captures/")
    assert (local_project / payload["capture_manifest_path"]).exists()
    assert {
        "polymarket_updown_market_metadata",
        "polymarket_public_clob_orderbook_snapshots",
        "crypto_spot_snapshots_or_candles",
        "market_window_labels_and_resolution_metadata",
    }.issubset(set(payload["capture_targets"]))


def test_sequence38_expanded_dataset_preserves_source_quality_and_dedupes() -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_dataset_builder import (
        build_pm_crypto_updown_expanded_dataset,
    )

    base = build_pm_crypto_updown_expanded_dataset(fixture_root=FIXTURE_ROOT)
    with_duplicate_source = build_pm_crypto_updown_expanded_dataset(
        fixture_root=FIXTURE_ROOT,
        extra_fixture_roots=[FIXTURE_ROOT],
    )

    assert base["schema_version"] == "pm_crypto_updown_expanded_dataset_v1"
    assert base["row_count"] == 10
    assert base["dedupe_dropped_row_count"] == 0
    assert with_duplicate_source["row_count"] == 10
    assert with_duplicate_source["dedupe_dropped_row_count"] == 4
    assert base["source_quality_counts"] == {
        "fixture_real_shaped": 8,
        "synthetic_stress": 2,
    }
    assert base["replay_ready_row_count"] == 8
    assert base["primary_evidence_row_count"] == 6
    assert base["synthetic_stress_replay_ready_row_count"] == 2
    assert all("source_quality" in row for row in base["rows"])
    assert all("source_hash" in row for row in base["rows"])
    assert all(row["source_quality"] != "synthetic_stress" for row in base["primary_rows"])


def test_sequence38_expanded_alignment_keeps_no_lookahead() -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_dataset_builder import (
        build_pm_crypto_updown_expanded_dataset,
    )

    payload = build_pm_crypto_updown_expanded_dataset(fixture_root=FIXTURE_ROOT)
    row = next(item for item in payload["rows"] if item["clob_snapshot_id"] == "clob_1202_down_01")

    assert row["spot_price"] == 99960.0
    assert row["spot_price"] != 99500.0
    assert "LOOKAHEAD_PREVENTED" in row["data_quality_flags"]
    assert row["source_quality"] == "fixture_real_shaped"
    assert row["spot_return_5s"] < 0


def test_sequence38_evidence_quality_counts_threshold_progress(local_project: Path) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_evidence_quality import (
        write_pm_crypto_updown_evidence_quality_report,
    )

    payload = write_pm_crypto_updown_evidence_quality_report(
        fixture_root=FIXTURE_ROOT,
        output_root=local_project,
    )

    assert payload["schema_version"] == "pm_crypto_updown_evidence_quality_v1"
    assert payload["evidence_expansion_status"] == "REPLAY_EVIDENCE_PARTIAL"
    assert payload["candidate_status"] == "CANDIDATE_REMAINS_BLOCKED"
    assert payload["minimum_primary_replay_ready_rows"] == 20
    assert payload["current_replay_ready_row_count"] == 2
    assert payload["replay_ready_row_count"] == 8
    assert payload["primary_evidence_row_count"] == 6
    assert payload["synthetic_stress_row_count"] == 2
    assert payload["synthetic_stress_replay_ready_row_count"] == 2
    assert payload["rows_needed_for_threshold"] == 14
    assert payload["clob_coverage"] == 1.0
    assert payload["spot_coverage"] == 1.0
    assert payload["label_count"] == 4
    assert "PRIMARY_ROWS_6_LT_20" in payload["blockers"]
    assert (
        local_project
        / "reports"
        / "sequence38"
        / "evidence_quality"
        / "latest_pm_crypto_updown_evidence_quality.json"
    ).exists()


def test_sequence38_expanded_replay_eval_separates_primary_diagnostic_and_synthetic(
    local_project: Path,
) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_expanded_replay_eval import (
        write_pm_crypto_updown_expanded_replay_eval_report,
    )

    payload = write_pm_crypto_updown_expanded_replay_eval_report(
        fixture_root=FIXTURE_ROOT,
        output_root=local_project,
    )

    assert payload["schema_version"] == "pm_crypto_updown_expanded_replay_eval_v1"
    assert payload["evaluation_status"] == "CANDIDATE_REMAINS_BLOCKED"
    assert payload["primary_result"]["row_count"] == 6
    assert payload["primary_result"]["baseline_metrics"]["primary_evidence_row_count"] == 6
    assert payload["fixture_diagnostic_result"]["row_count"] == 8
    assert payload["synthetic_stress_result"]["row_count"] == 2
    assert payload["synthetic_rows_counted_as_primary"] is False
    assert payload["primary_result"]["placebo_metrics"]["candidate_beats_placebos_for_readiness"] is False
    assert "PRIMARY_ROWS_6_LT_20" in payload["readiness_blockers"]
    assert payload["live_trading_enabled"] is False
    assert payload["execution_authority"] == "NONE"


def test_sequence38_expanded_shadow_readiness_blocks_below_threshold_and_never_claims_live(
    local_project: Path,
) -> None:
    from quant_os.readiness.expanded_shadow_replay_readiness_report import (
        write_expanded_shadow_replay_readiness_report,
    )
    from quant_os.research.replay_candidates.pm_crypto_updown_expanded_replay_eval import (
        write_pm_crypto_updown_expanded_replay_eval_report,
    )

    evaluation = write_pm_crypto_updown_expanded_replay_eval_report(
        fixture_root=FIXTURE_ROOT,
        output_root=local_project,
    )
    payload = write_expanded_shadow_replay_readiness_report(
        expanded_replay_eval=evaluation,
        output_root=local_project,
    )

    assert payload["schema_version"] == "expanded_shadow_replay_readiness_v1"
    assert payload["readiness_status"] == "PRIMARY_EVIDENCE_TOO_THIN"
    assert payload["overall_status"] == "EXPANDED_SHADOW_REPLAY_NOT_READY"
    assert payload["ready_for_expanded_shadow_replay"] is False
    assert payload["live_readiness_claimed"] is False
    assert payload["canary_readiness_claimed"] is False
    assert payload["live_trading_enabled"] is False
    assert payload["execution_authority"] == "NONE"
    assert "PRIMARY_ROWS_6_LT_20" in payload["blockers"]
    assert payload["autonomy_milestones"]["replay_evidence_expansion"] == "partial"
    assert payload["autonomy_milestones"]["expanded_shadow_replay"] == "blocked"
    assert (
        local_project
        / "reports"
        / "sequence38"
        / "expanded_shadow_replay_readiness"
        / "latest_expanded_shadow_replay_readiness.json"
    ).exists()
    assert (
        local_project
        / "reports"
        / "sequence38"
        / "autonomy_milestones"
        / "latest_autonomy_milestones.json"
    ).exists()


def test_sequence38_cli_commands_are_fixture_safe_and_non_executing(
    local_project: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = {
        **os.environ,
        "PYTHONPATH": str(repo_root / "src"),
    }
    commands = [
        [sys.executable, "-m", "quant_os.cli", "research", "pm-crypto-updown-expansion-plan"],
        [
            sys.executable,
            "-m",
            "quant_os.cli",
            "research",
            "pm-crypto-updown-manual-capture-plan",
        ],
        [sys.executable, "-m", "quant_os.cli", "research", "pm-crypto-updown-expanded-dataset"],
        [sys.executable, "-m", "quant_os.cli", "research", "pm-crypto-updown-evidence-quality"],
        [
            sys.executable,
            "-m",
            "quant_os.cli",
            "research",
            "pm-crypto-updown-expanded-replay-eval",
        ],
        [sys.executable, "-m", "quant_os.cli", "readiness", "expanded-shadow-replay"],
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


def test_sequence38_modules_do_not_add_auth_signing_order_cancel_or_evasion_paths() -> None:
    source_paths = [
        Path("src/quant_os/data/prediction_markets/pm_updown_capture_plan.py"),
        Path("src/quant_os/data/prediction_markets/pm_updown_manual_capture.py"),
        Path("src/quant_os/data/crypto_spot_manual_capture.py"),
        Path("src/quant_os/research/replay_candidates/pm_crypto_updown_expansion_plan.py"),
        Path("src/quant_os/research/replay_candidates/pm_crypto_updown_dataset_builder.py"),
        Path("src/quant_os/research/replay_candidates/pm_crypto_updown_evidence_quality.py"),
        Path("src/quant_os/research/replay_candidates/pm_crypto_updown_expanded_replay_eval.py"),
        Path("src/quant_os/readiness/expanded_shadow_replay_readiness.py"),
    ]
    forbidden_tokens = [
        "create_order",
        "cancel_order",
        "post_order",
        "private_key",
        "wallet_signer",
        "sign_order",
        "copy_wallet_trade",
        "captcha_bypass",
        "proxy_rotation",
        "stealth_evasion",
    ]

    for path in source_paths:
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        for token in forbidden_tokens:
            assert token not in lowered
