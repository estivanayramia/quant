from __future__ import annotations

from quant_os.autonomy.supervisor import Supervisor
from quant_os.features.feature_report import write_feature_report
from quant_os.research.leaderboard import build_strategy_leaderboard
from quant_os.research.overfit_checks import run_overfit_checks
from quant_os.research.regime_tests import run_regime_tests
from quant_os.research.research_report import run_strategy_research, write_strategy_research_report
from quant_os.research.strategy_ablation import run_strategy_ablation
from quant_os.research.walk_forward import run_walk_forward_validation


def test_phase7_smoke_passes(local_project) -> None:
    assert write_feature_report()["rows"] > 0
    assert run_strategy_research()["status"] == "PASS"
    assert run_strategy_ablation()["status"] == "PASS"
    assert run_walk_forward_validation()["status"] in {"PASS", "WARN", "UNAVAILABLE"}
    assert run_regime_tests()["status"] in {"PASS", "WARN"}
    assert run_overfit_checks()["status"] in {"PASS", "WARN"}
    assert build_strategy_leaderboard()["live_promotion_status"] == "TINY_LIVE_BLOCKED"
    assert write_strategy_research_report()["live_promotion_status"] == "TINY_LIVE_BLOCKED"
    state = Supervisor().run_once()
    assert state.strategy_research_summary["live_promotion_status"] == "TINY_LIVE_BLOCKED"
