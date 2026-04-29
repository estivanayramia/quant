from __future__ import annotations

from pathlib import Path

from quant_os.autonomy.supervisor import Supervisor
from quant_os.data.historical_import import import_historical_csv
from quant_os.data.historical_manifest import build_historical_manifest
from quant_os.data.historical_normalize import normalize_latest_historical
from quant_os.data.historical_quality import run_historical_quality
from quant_os.data.provider_check import check_historical_providers
from quant_os.research.historical_evidence import (
    build_historical_splits,
    calculate_historical_evidence_score,
)
from quant_os.research.historical_research_report import write_historical_research_report
from quant_os.research.leaderboard import build_strategy_leaderboard

FIXTURES = Path(__file__).parent / "fixtures" / "historical"


def test_phase9_smoke_passes(local_project) -> None:
    assert check_historical_providers()["status"] == "PASS"
    assert import_historical_csv(FIXTURES / "sample_ohlcv_standard.csv")["rows"] == 10
    assert normalize_latest_historical()["rows"] == 10
    assert build_historical_manifest()["status"] == "PASS"
    assert run_historical_quality()["status"] in {"PASS", "WARN"}
    assert build_historical_splits()["status"] == "PASS"
    score = calculate_historical_evidence_score()
    assert score["live_promotion_status"] == "LIVE_BLOCKED"
    assert write_historical_research_report()["live_promotion_status"] == "LIVE_BLOCKED"
    leaderboard = build_strategy_leaderboard()
    assert "data_source_type" in leaderboard
    state = Supervisor().run_once()
    assert (
        state.historical_data_summary["historical_data"]["live_promotion_status"]
        == "LIVE_BLOCKED"
    )
