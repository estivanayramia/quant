from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.validation.contracts import ValidationOutcome, ValidationScenario
from quant_os.validation.metrics import summarize_validation
from quant_os.validation.report import write_scenario_report, write_summary_report
from quant_os.validation.scenario_engine import SCENARIOS, execute_scenario


def list_scenarios() -> list[ValidationScenario]:
    return SCENARIOS.copy()


def run_scenario(scenario_id: str, *, output_root: str | Path = ".") -> ValidationOutcome:
    outcome = execute_scenario(scenario_id)
    write_scenario_report(outcome, output_root=output_root)
    return outcome


def run_all_scenarios(*, output_root: str | Path = ".") -> dict[str, Any]:
    outcomes = [run_scenario(scenario.scenario_id, output_root=output_root) for scenario in SCENARIOS]
    summary = summarize_validation(outcomes)
    summary["scenario_results"] = [outcome.model_dump(mode="json") for outcome in outcomes]
    write_summary_report(summary, output_root=output_root)
    return summary


def latest_validation_summary(*, output_root: str | Path = ".") -> dict[str, Any]:
    return run_all_scenarios(output_root=output_root)
