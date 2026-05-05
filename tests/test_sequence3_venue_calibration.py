from __future__ import annotations

from pathlib import Path

from quant_os.replay.venue_calibration import optional_ccxt_status, run_venue_calibration

FIXTURE = Path(__file__).parent / "fixtures" / "venue" / "binance_public_snapshot.json"


def test_venue_calibration_uses_fixture_without_network(local_project: Path) -> None:
    payload = run_venue_calibration(fixture_path=FIXTURE, output_root=local_project)

    assert payload["status"] == "WARN"
    assert payload["source_mode"] == "fixture"
    assert payload["network_fetch_allowed"] is False
    assert payload["live_trading_enabled"] is False
    assert payload["live_allowed"] is False
    assert payload["live_promotion_status"] == "LIVE_BLOCKED"
    assert len(payload["source_sha256"]) == 64
    assert payload["venue"] == "binance"
    assert payload["symbols"] == ["BTC/USDT", "ETH/USDT"]
    assert payload["observed"]["max_quote_age_ms"] > payload["policy"]["max_quote_age_ms"]
    assert "STALE_BOOK_OBSERVED" in payload["warnings"]
    assert "MISSING_INTERVALS_OBSERVED" in payload["warnings"]
    assert payload["suggested_replay_parameters"]["fee_bps"] >= 5.0
    assert payload["suggested_replay_parameters"]["slippage_bps"] > 0.0
    assert (
        local_project
        / "reports"
        / "sequence3"
        / "venue_calibration"
        / "latest_venue_calibration.json"
    ).exists()
    assert (
        local_project
        / "reports"
        / "sequence3"
        / "venue_calibration"
        / "latest_venue_calibration.md"
    ).exists()


def test_venue_calibration_refuses_network_without_explicit_permission(local_project: Path) -> None:
    payload = run_venue_calibration(
        fixture_path=FIXTURE,
        output_root=local_project,
        allow_network_fetch=True,
        explicit_network_fetch=False,
    )

    assert payload["status"] == "BLOCKED"
    assert "NETWORK_FETCH_REQUIRES_EXPLICIT_FLAG" in payload["blockers"]
    assert payload["network_fetch_allowed"] is False
    assert payload["live_promotion_status"] == "LIVE_BLOCKED"


def test_venue_calibration_explicit_network_request_remains_unimplemented_and_blocked(
    local_project: Path,
) -> None:
    payload = run_venue_calibration(
        fixture_path=FIXTURE,
        output_root=local_project,
        allow_network_fetch=True,
        explicit_network_fetch=True,
    )

    assert payload["status"] == "BLOCKED"
    assert "NETWORK_FETCH_NOT_IMPLEMENTED_IN_SEQUENCE3A" in payload["blockers"]
    assert payload["network_fetch_allowed"] is False
    assert payload["live_promotion_status"] == "LIVE_BLOCKED"


def test_venue_calibration_ccxt_is_optional_and_absent_safe() -> None:
    status = optional_ccxt_status()

    assert status["name"] == "ccxt"
    assert "installed" in status
    assert status["required"] is False
