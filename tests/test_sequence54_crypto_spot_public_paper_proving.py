from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pandas as pd


def _reversion_frame(*, periods: int = 760, trending: bool = False) -> pd.DataFrame:
    timestamps = pd.date_range("2026-01-01T00:00:00Z", periods=periods, freq="4h")
    rows = []
    for symbol, base in {"BTC/USDT": 50_000.0, "ETH/USDT": 3_000.0}.items():
        price = base
        for index, timestamp in enumerate(timestamps):
            if trending:
                price *= 1.004
            elif index % 24 == 12:
                price *= 0.955
            elif index % 24 in {13, 14, 15, 16, 17, 18}:
                price *= 1.009
            else:
                price *= 1.0002 if index % 2 == 0 else 0.9998
            rows.append(
                {
                    "timestamp": timestamp,
                    "symbol": symbol,
                    "venue": "kraken",
                    "timeframe": "4h",
                    "open": price * 0.999,
                    "high": price * 1.004,
                    "low": price * 0.996,
                    "close": price,
                    "volume": 100.0 + index,
                    "source": "unit_public_replay_shape",
                }
            )
    return pd.DataFrame(rows)


def test_sequence54_fixture_safe_mode_cannot_promote(local_project: Path) -> None:
    from quant_os.proving.crypto_spot_public_paper_proving import (
        write_crypto_spot_public_paper_proving_report,
    )

    payload = write_crypto_spot_public_paper_proving_report(output_root=local_project)

    assert payload["capture_status"] == "PUBLIC_NETWORK_DISABLED"
    assert payload["source_quality_tier"] == "SYNTHETIC_ONLY"
    assert payload["paper_profit_candidate"] is False
    assert payload["profit_claim_guard"]["claim_status"] == "NO_PROFIT_CLAIM_ALLOWED"
    assert "SYNTHETIC_ONLY_DATA" in payload["profit_claim_guard"]["blockers"]
    assert payload["live_trading_enabled"] is False
    assert payload["execution_authority"] == "NONE"


def test_sequence54_public_replay_shape_can_pass_all_crypto_spot_gates(
    local_project: Path,
) -> None:
    from quant_os.proving.crypto_spot_public_paper_proving import (
        run_crypto_spot_public_paper_proving,
    )

    payload = run_crypto_spot_public_paper_proving(
        frame=_reversion_frame(),
        output_root=local_project,
        source_quality_tier="PUBLIC_REPLAY",
        capture_status="PUBLIC_TEST_REPLAY_SUPPLIED",
    )

    assert payload["readiness_status"] == "PAPER_PROFIT_CANDIDATE"
    assert payload["paper_profit_candidate"] is True
    assert payload["profit_claim_guard"]["claim_status"] == "PAPER_PROFIT_CANDIDATE"
    assert payload["costs_included"] is True
    assert payload["fill_assumptions_included"] is True
    assert payload["baseline_comparison"]["paper_beats_comparison"] is True
    assert payload["placebo_comparison"]["paper_beats_comparison"] is True
    assert payload["one_row_dominance"]["detected"] is False
    assert payload["oos_walk_forward_status"] == "OOS_WALK_FORWARD_AVAILABLE"
    assert payload["live_ready"] is False
    assert payload["canary_ready"] is False


def test_sequence54_buy_and_hold_dominance_blocks_candidate(local_project: Path) -> None:
    from quant_os.proving.crypto_spot_public_paper_proving import (
        run_crypto_spot_public_paper_proving,
    )

    payload = run_crypto_spot_public_paper_proving(
        frame=_reversion_frame(trending=True),
        output_root=local_project,
        source_quality_tier="PUBLIC_REPLAY",
        capture_status="PUBLIC_TEST_REPLAY_SUPPLIED",
    )

    assert payload["paper_profit_candidate"] is False
    assert payload["profit_claim_guard"]["claim_status"] == "NO_PROFIT_CLAIM_ALLOWED"
    assert "BASELINE_COMPARISON_NOT_BEATEN" in payload["profit_claim_guard"]["blockers"]


def test_sequence54_cli_make_target_is_fixture_safe(local_project: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = {
        **os.environ,
        "PYTHONPATH": str(repo_root / "src"),
    }
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "quant_os.cli",
            "proving",
            "crypto-spot-public-paper-proving",
        ],
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

    make_cmd = (repo_root / "make.cmd").read_text(encoding="utf-8")
    assert 'if "%TARGET%"=="crypto-spot-public-paper-proving-smoke"' in make_cmd
    assert 'if "%TARGET%"=="sequence54-smoke"' in make_cmd


def test_sequence54_public_network_retry_changes_crypto_blocker_signature() -> None:
    from quant_os.proving.relentless_profit_campaign_state import default_campaign_state
    from quant_os.research.lane_selection.relentless_profit_campaign_engine import select_next_lane
    from quant_os.research.lane_selection.relentless_profit_campaign_models import (
        build_initial_lane_universe,
    )

    state = default_campaign_state()
    state["lanes_attempted"] = ["crypto_spot_momentum_reversion_intraday"]
    state["lane_blocker_signatures"] = {
        "crypto_spot_momentum_reversion_intraday": "PUBLIC_SPOT_REPLAY_DATASET_MISSING"
    }

    selected = select_next_lane(
        build_initial_lane_universe(),
        state,
        retry_public_data_blockers=True,
    )

    assert selected is not None
    assert selected["lane_id"] == "crypto_spot_momentum_reversion_intraday"


def test_sequence54_public_replay_terminal_blocker_is_not_overwritten_by_fixture_retry() -> None:
    from quant_os.proving.relentless_profit_campaign_state import default_campaign_state
    from quant_os.research.lane_selection.relentless_profit_campaign_engine import select_next_lane
    from quant_os.research.lane_selection.relentless_profit_campaign_models import lane_by_id

    lane = lane_by_id("crypto_spot_momentum_reversion_intraday")
    state = default_campaign_state()
    state["lanes_attempted"] = [lane["lane_id"]]
    state["lane_blocker_signatures"] = {
        lane["lane_id"]: "PAPER_PROFIT_BLOCKED_BY_BASELINE"
    }

    assert select_next_lane([lane], state) is None
