from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "replay_candidates" / "pm_crypto_updown"


def test_sequence36_candidate_dataset_schema_validates_required_fields() -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_schema import (
        REQUIRED_PM_CRYPTO_UPDOWN_FIELDS,
        PmCryptoUpDownReplayRow,
    )

    payload = {
        "candidate_id": "pm_crypto_updown_repricing_lag",
        "market_id": "pm_btc_updown_20260513_1200",
        "condition_id": "cond_1200",
        "slug": "btc-up-or-down-may-13-1200",
        "token_id": "token_up_1200",
        "outcome": "UP",
        "window_start_ts": "2026-05-13T12:00:00Z",
        "window_end_ts": "2026-05-13T12:01:00Z",
        "event_ts": "2026-05-13T12:00:45Z",
        "seconds_to_window_end": 15.0,
        "spot_symbol": "BTC-USD",
        "spot_price": 100050.0,
        "spot_return_1s": 0.00009996,
        "spot_return_5s": 0.00019994,
        "spot_return_15s": 0.00029994,
        "market_bid": 0.54,
        "market_ask": 0.56,
        "market_mid": 0.55,
        "market_spread": 0.02,
        "market_last_trade_price": 0.55,
        "market_volume": 1200.0,
        "market_liquidity": 800.0,
        "clob_snapshot_id": "clob_1200_up_01",
        "source_ids": ["fixture_spot", "fixture_clob", "fixture_resolution"],
        "provenance_hash": "abc123",
        "data_quality_flags": [],
        "label_status": "RESOLVED",
        "resolved_outcome": "UP",
    }

    row = PmCryptoUpDownReplayRow.model_validate(payload)

    assert set(REQUIRED_PM_CRYPTO_UPDOWN_FIELDS).issubset(row.model_dump())
    assert row.window_start_ts.endswith("Z")
    assert row.event_ts.endswith("Z")

    invalid = dict(payload)
    invalid.pop("market_id")
    with pytest.raises(ValidationError):
        PmCryptoUpDownReplayRow.model_validate(invalid)


def test_sequence36_fixture_loaders_are_deterministic() -> None:
    from quant_os.data.crypto_spot_snapshots import load_crypto_spot_snapshots
    from quant_os.data.prediction_markets.clob_snapshots import load_clob_snapshots
    from quant_os.data.prediction_markets.updown_market_windows import load_updown_market_windows
    from quant_os.data.prediction_markets.window_labels import load_window_labels

    spot_first = load_crypto_spot_snapshots(FIXTURE_ROOT / "spot_snapshots.csv")
    spot_second = load_crypto_spot_snapshots(FIXTURE_ROOT / "spot_snapshots.csv")
    clob_first = load_clob_snapshots(FIXTURE_ROOT / "clob_snapshots.json")
    clob_second = load_clob_snapshots(FIXTURE_ROOT / "clob_snapshots.json")
    windows_first = load_updown_market_windows(FIXTURE_ROOT / "market_windows.json")
    windows_second = load_updown_market_windows(FIXTURE_ROOT / "market_windows.json")
    labels_first = load_window_labels(FIXTURE_ROOT / "window_labels.json")
    labels_second = load_window_labels(FIXTURE_ROOT / "window_labels.json")

    assert spot_first == spot_second
    assert clob_first == clob_second
    assert windows_first == windows_second
    assert labels_first == labels_second
    assert len(spot_first) == 12
    assert len(clob_first) == 4
    assert len(windows_first) == 2
    assert labels_first["pm_btc_updown_20260513_1200"]["resolved_outcome"] == "UP"


def test_sequence36_alignment_prevents_lookahead_and_calculates_market_fields() -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_alignment import (
        build_pm_crypto_updown_dataset,
    )

    dataset = build_pm_crypto_updown_dataset(fixture_root=FIXTURE_ROOT)
    row = next(item for item in dataset["rows"] if item["clob_snapshot_id"] == "clob_1200_up_01")

    assert dataset["candidate_id"] == "pm_crypto_updown_repricing_lag"
    assert row["spot_price"] == 100050.0
    assert row["spot_price"] != 100500.0
    assert "LOOKAHEAD_PREVENTED" in row["data_quality_flags"]
    assert row["seconds_to_window_end"] == 15.0
    assert row["market_mid"] == 0.55
    assert row["market_spread"] == pytest.approx(0.02)
    assert row["spot_return_1s"] == pytest.approx((100050.0 / 100040.0) - 1.0)
    assert row["spot_return_5s"] == pytest.approx((100050.0 / 100030.0) - 1.0)
    assert row["spot_return_15s"] == pytest.approx((100050.0 / 100020.0) - 1.0)
    assert row["provenance_hash"]


def test_sequence36_alignment_flags_stale_missing_and_low_quality_rows() -> None:
    from quant_os.data.crypto_spot_snapshots import load_crypto_spot_snapshots
    from quant_os.data.prediction_markets.clob_snapshots import load_clob_snapshots
    from quant_os.data.prediction_markets.updown_market_windows import load_updown_market_windows
    from quant_os.data.prediction_markets.window_labels import load_window_labels
    from quant_os.research.replay_candidates.pm_crypto_updown_alignment import (
        align_pm_crypto_updown_rows,
    )

    rows = align_pm_crypto_updown_rows(
        spot_snapshots=load_crypto_spot_snapshots(FIXTURE_ROOT / "spot_snapshots.csv"),
        market_windows=load_updown_market_windows(FIXTURE_ROOT / "market_windows.json"),
        clob_snapshots=load_clob_snapshots(FIXTURE_ROOT / "clob_snapshots.json"),
        window_labels=load_window_labels(FIXTURE_ROOT / "window_labels.json"),
    )
    stale = next(item for item in rows if item["clob_snapshot_id"] == "clob_1201_up_01")

    assert "WIDE_SPREAD" in stale["data_quality_flags"]
    assert "LOW_LIQUIDITY" in stale["data_quality_flags"]
    assert "LABEL_UNRESOLVED" in stale["data_quality_flags"]

    missing_clob = align_pm_crypto_updown_rows(
        spot_snapshots=load_crypto_spot_snapshots(FIXTURE_ROOT / "spot_snapshots.csv"),
        market_windows=load_updown_market_windows(FIXTURE_ROOT / "market_windows.json"),
        clob_snapshots=[],
        window_labels=load_window_labels(FIXTURE_ROOT / "window_labels.json"),
    )
    assert any("MISSING_CLOB_SNAPSHOT" in item["data_quality_flags"] for item in missing_clob)

    missing_spot = align_pm_crypto_updown_rows(
        spot_snapshots=[],
        market_windows=load_updown_market_windows(FIXTURE_ROOT / "market_windows.json"),
        clob_snapshots=load_clob_snapshots(FIXTURE_ROOT / "clob_snapshots.json"),
        window_labels=load_window_labels(FIXTURE_ROOT / "window_labels.json"),
    )
    assert any("MISSING_SPOT_SNAPSHOT" in item["data_quality_flags"] for item in missing_spot)


def test_sequence36_quality_report_is_conservative_and_writes_replay_rows(
    local_project: Path,
) -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_dataset_report import (
        write_pm_crypto_updown_dataset_report,
    )

    payload = write_pm_crypto_updown_dataset_report(
        fixture_root=FIXTURE_ROOT,
        output_root=local_project,
    )

    assert payload["schema_version"] == "pm_crypto_updown_dataset_report_v1"
    assert payload["readiness_status"] == "REPLAY_DATASET_READY_FOR_CANDIDATE_TEST"
    assert payload["row_count"] == 4
    assert payload["market_count"] == 2
    assert payload["resolved_label_count"] == 2
    assert payload["clob_coverage"] == 1.0
    assert payload["spot_coverage"] == 1.0
    assert payload["wide_spread_count"] == 2
    assert payload["low_liquidity_count"] == 2
    assert payload["unresolved_label_count"] == 2
    assert payload["replay_ready_row_count"] == 2
    assert payload["blockers"] == []
    assert "UNRESOLVED_LABELS_PRESENT" in payload["caveats"]
    assert (
        local_project
        / "reports"
        / "sequence36"
        / "replay_dataset"
        / "latest_pm_crypto_updown_dataset.json"
    ).exists()


def test_sequence36_baseline_prep_fields_do_not_claim_profitability() -> None:
    from quant_os.research.replay_candidates.pm_crypto_updown_alignment import (
        build_pm_crypto_updown_dataset,
    )
    from quant_os.research.replay_candidates.pm_crypto_updown_baseline_prep import (
        prepare_pm_crypto_updown_baseline_rows,
    )

    dataset = build_pm_crypto_updown_dataset(fixture_root=FIXTURE_ROOT)
    rows = prepare_pm_crypto_updown_baseline_rows(dataset["rows"])

    assert len(rows) == len(dataset["rows"])
    first = rows[0]
    assert "market_probability_baseline" in first
    assert "no_skill_baseline" in first
    assert "spot_lag_heuristic_candidate" in first
    assert "timestamp_shift_placebo_candidate" in first
    assert "cost_spread_burden" in first
    assert "fill_caveat" in first
    assert first["profitability_claimed"] is False
    assert first["direct_execution_allowed"] is False


def test_sequence36_readiness_gate_blocks_incomplete_and_allows_candidate_testing(
    local_project: Path,
) -> None:
    from quant_os.readiness.replay_dataset_readiness import evaluate_replay_dataset_readiness
    from quant_os.readiness.replay_dataset_readiness_report import (
        write_replay_dataset_readiness_report,
    )
    from quant_os.research.replay_candidates.pm_crypto_updown_dataset_report import (
        write_pm_crypto_updown_dataset_report,
    )

    report = write_pm_crypto_updown_dataset_report(
        fixture_root=FIXTURE_ROOT,
        output_root=local_project,
    )
    readiness = write_replay_dataset_readiness_report(
        dataset_report=report,
        output_root=local_project,
    )
    assert readiness["readiness_status"] == "REPLAY_DATASET_READY_FOR_CANDIDATE_TEST"
    assert readiness["ready_for_phase37_candidate_replay"] is True
    assert readiness["not_shadow_trading_readiness"] is True

    missing_clob = dict(report)
    missing_clob["clob_coverage"] = 0.0
    missing_clob["row_count"] = 0
    blocked = evaluate_replay_dataset_readiness(dataset_report=missing_clob)
    assert blocked["readiness_status"] == "REPLAY_DATASET_BLOCKED_MISSING_CLOB"

    ready_report = dict(report)
    ready_report["readiness_status"] = "REPLAY_DATASET_READY_FOR_CANDIDATE_TEST"
    ready_report["unresolved_label_count"] = 0
    ready_report["wide_spread_count"] = 0
    ready_report["low_liquidity_count"] = 0
    ready_report["replay_ready_row_count"] = 4
    ready_report["blockers"] = []
    ready = evaluate_replay_dataset_readiness(dataset_report=ready_report)
    assert ready["readiness_status"] == "REPLAY_DATASET_READY_FOR_CANDIDATE_TEST"
    assert ready["ready_for_phase37_candidate_replay"] is True
    assert ready["live_trading_enabled"] is False


def test_sequence36_cli_commands_are_fixture_safe_and_non_executing(
    local_project: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = {
        **os.environ,
        "PYTHONPATH": str(repo_root / "src"),
    }
    commands = [
        [sys.executable, "-m", "quant_os.cli", "research", "pm-crypto-updown-dataset"],
        [sys.executable, "-m", "quant_os.cli", "research", "pm-crypto-updown-quality"],
        [sys.executable, "-m", "quant_os.cli", "readiness", "replay-dataset-readiness"],
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


def test_sequence36_modules_do_not_add_live_wallet_or_order_paths() -> None:
    source_paths = [
        Path("src/quant_os/research/replay_candidates/pm_crypto_updown_schema.py"),
        Path("src/quant_os/research/replay_candidates/pm_crypto_updown_alignment.py"),
        Path("src/quant_os/research/replay_candidates/pm_crypto_updown_quality.py"),
        Path("src/quant_os/research/replay_candidates/pm_crypto_updown_baseline_prep.py"),
        Path("src/quant_os/readiness/replay_dataset_readiness.py"),
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
