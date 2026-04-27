from __future__ import annotations

import json
from pathlib import Path

from quant_os.integrations.freqtrade.dry_run_adapter import FreqtradeDryRunAdapter


def write_freqtrade_status_report(
    output_dir: str | Path = "reports/freqtrade",
) -> dict[str, object]:
    adapter = FreqtradeDryRunAdapter()
    status = adapter.get_status()
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    (root / "latest_status.json").write_text(
        json.dumps(status, indent=2, sort_keys=True), encoding="utf-8"
    )
    lines = [
        "# Freqtrade Dry-Run Status",
        "",
        "Freqtrade integration is dry-run-only.",
        "No live trading is enabled.",
        "No exchange keys are present in generated config.",
        "",
        f"Generated config path: {adapter.config_path}",
        f"Generated strategy path: {adapter.strategy_path}",
        f"Safety guard passed: {status['safety_guard_passed']}",
        f"Docker available: {status['docker_available']}",
        f"Manual docker command preview: `{status['next_manual_command']}`",
        "",
        "Next steps: inspect generated config, validate safety, and only run the Docker profile manually if desired.",
    ]
    (root / "latest_status.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return status
