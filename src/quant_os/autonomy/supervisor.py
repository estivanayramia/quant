from __future__ import annotations

from quant_os.autonomy.runbook import RunbookEngine
from quant_os.autonomy.state import AutonomousRunState


class Supervisor:
    def __init__(self, engine: RunbookEngine | None = None) -> None:
        self.engine = engine or RunbookEngine()

    def run_once(self, runbook: str = "full_safe_autonomous_cycle") -> AutonomousRunState:
        return self.engine.run(runbook)
