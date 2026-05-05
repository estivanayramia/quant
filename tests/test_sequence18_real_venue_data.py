from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from quant_os.data.venue_capture import capture_public_venue_snapshot
from quant_os.replay.venue_calibration import run_venue_calibration
from quant_os.research.crypto.calibrated_edge_report import write_calibrated_edge_report


def test_capture_absent_safe(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Simulate ccxt not being installed
    monkeypatch.setattr("importlib.util.find_spec", lambda name: None if name == "ccxt" else MagicMock())
    with pytest.raises(RuntimeError, match="ccxt optional dependency is not installed"):
        capture_public_venue_snapshot(output_dir=tmp_path)


def test_capture_offline_safe_and_defaults(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Simulate ccxt is installed
    monkeypatch.setattr("importlib.util.find_spec", lambda name: MagicMock())

    # Mock CCXT Exchange
    mock_ccxt = MagicMock()
    mock_exchange = MagicMock()
    mock_exchange.fetch_ticker.return_value = {
        "bid": 64200.0,
        "bidVolume": 1.5,
        "ask": 64201.0,
        "askVolume": 0.8,
        "datetime": "2026-05-05T00:00:00Z",
    }
    mock_exchange.fetch_ohlcv.return_value = [
        [1777938900000, 64200, 64250, 64180, 64210, 100]
    ]
    mock_exchange_cls = MagicMock(return_value=mock_exchange)
    mock_ccxt.kraken = mock_exchange_cls

    monkeypatch.setattr("importlib.import_module", lambda name: mock_ccxt if name == "ccxt" else MagicMock())

    result = capture_public_venue_snapshot(
        exchange_id="kraken",
        symbols=["BTC/USDT"],
        output_dir=tmp_path,
    )

    assert result["status"] == "PASS"
    assert result["venue"] == "kraken"
    assert "file_path" in result

    # Verify JSON output
    file_path = Path(result["file_path"])
    assert file_path.exists()
    payload = json.loads(file_path.read_text("utf-8"))
    assert payload["venue"] == "kraken"
    assert payload["source"] == "kraken_public_capture"
    assert "BTCUSDT" in payload["symbols"]
    assert payload["symbols"]["BTCUSDT"]["book_ticker"]["bidPrice"] == "64200.0"


def test_venue_recalibration_from_cached_data(local_project: Path) -> None:
    # Generate a dummy cached file
    cached_dir = local_project / "data" / "venue_capture"
    cached_dir.mkdir(parents=True)
    cached_file = cached_dir / "kraken_public_snapshot_test.json"
    cached_file.write_text(
        json.dumps({
            "source": "kraken_public_capture",
            "venue": "kraken",
            "timeframe": "1m",
            "captured_at": "2026-05-05T00:00:00Z",
            "symbols": {
                "BTCUSDT": {
                    "book_ticker": {
                        "symbol": "BTCUSDT",
                        "bidPrice": "64000",
                        "bidQty": "1",
                        "askPrice": "64010",
                        "askQty": "1",
                    },
                    "klines": []
                }
            }
        }),
        encoding="utf-8"
    )

    result = run_venue_calibration(
        fixture_path=cached_file,
        output_root=local_project,
    )

    assert result["source_mode"] == "cached_real"
    assert result["sequence"] == "18"
    assert result["venue"] == "kraken"
    assert result["live_promotion_status"] == "LIVE_BLOCKED"


def test_real_data_calibrated_edge_report(local_project: Path, spy_frame: Any) -> None:
    # Pass a dummy frame and dummy calibration summary
    calibration_summary = {
        "status": "PASS",
        "generated_at": "2026-05-05T00:00:00Z",
        "sequence": "18",
        "source_mode": "cached_real",
        "suggested_replay_parameters": {"fee_bps": 500.0, "slippage_bps": 400.0},
        "warnings": [],
    }

    result = write_calibrated_edge_report(
        frame=spy_frame,
        calibration_summary=calibration_summary,
        output_root=local_project,
    )

    assert result["sequence"] == "18"
    # The default baseline strategies won't beat 9.0 bps costs
    assert result["credibility_status"] == "NOT_CREDIBLE_AFTER_CALIBRATION"
    assert result["status"] == "BLOCKED"
    assert "CALIBRATED_OOS_EXPECTANCY_BELOW_THRESHOLD" in result["blockers"]
    assert result["live_promotion_status"] == "LIVE_BLOCKED"
