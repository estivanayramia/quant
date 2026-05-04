from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.validation.contracts import ValidationOutcome


def write_scenario_report(outcome: ValidationOutcome, *, output_root: str | Path = ".") -> None:
    scenario_dir = Path(output_root) / "reports" / "validation" / "scenarios"
    scenario_dir.mkdir(parents=True, exist_ok=True)
    payload = outcome.model_dump(mode="json")
    (scenario_dir / f"{outcome.scenario_id}.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    lines = [
        f"# Validation Scenario: {outcome.scenario_id}",
        "",
        f"Status: {outcome.status}",
        f"Action: {outcome.action}",
        f"Blocked correctly: {outcome.blocked_correctly}",
        f"Unsafe actions: {outcome.unsafe_action_count}",
        "",
        "## Reasons",
    ]
    lines.extend(f"- {reason}" for reason in (outcome.reason_codes or ["None"]))
    (scenario_dir / f"{outcome.scenario_id}.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def write_summary_report(summary: dict[str, Any], *, output_root: str | Path = ".") -> None:
    report_dir = Path(output_root) / "reports" / "validation"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "latest_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, default=str), encoding="utf-8"
    )
    lines = [
        "# Sequence 1 Validation Summary",
        "",
        f"Status: {summary['status']}",
        f"Scenarios: {summary['scenario_count']}",
        f"Unsafe action failures: {summary['unsafe_action_failure_count']}",
        f"Blocked correctly: {summary['blocked_correctly_count']}",
        f"Live trading enabled: {summary['live_trading_enabled']}",
    ]
    (report_dir / "latest_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
