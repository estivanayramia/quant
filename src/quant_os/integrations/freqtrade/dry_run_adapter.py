from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from quant_os.integrations.freqtrade.config_writer import (
    DEFAULT_CONFIG_PATH,
    write_freqtrade_dry_run_config,
)
from quant_os.integrations.freqtrade.safety import FreqtradeSafetyResult, validate_freqtrade_config
from quant_os.integrations.freqtrade.strategy_exporter import (
    DEFAULT_STRATEGY_PATH,
    export_quant_os_strategy,
)


@dataclass
class FreqtradeDryRunAdapter:
    enabled: bool = False
    mode: str = "dry_run_only"
    live_trading_allowed: bool = False

    config_path: str = str(DEFAULT_CONFIG_PATH)
    strategy_path: str = str(DEFAULT_STRATEGY_PATH)

    def available(self) -> bool:
        return self.enabled and self.mode == "dry_run_only" and not self.live_trading_allowed

    def generate_config(self) -> Path:
        return write_freqtrade_dry_run_config(self.config_path)

    def validate_config(self) -> FreqtradeSafetyResult:
        return validate_freqtrade_config(self.config_path)

    def export_strategy(self) -> Path:
        return export_quant_os_strategy(self.strategy_path)

    def dry_run_available(self) -> bool:
        return Path(self.config_path).exists() and Path(self.strategy_path).exists()

    def get_status(self) -> dict[str, object]:
        config_present = Path(self.config_path).exists()
        strategy_present = Path(self.strategy_path).exists()
        safety_passed = False
        safety_reasons: list[str] = []
        if config_present:
            try:
                result = self.validate_config()
                safety_passed = result.passed
                safety_reasons = result.reasons
            except Exception as exc:
                safety_reasons = [str(exc)]
        return {
            "enabled": self.enabled,
            "mode": "dry_run",
            "live_trading_enabled": False,
            "dry_run_config_present": config_present,
            "strategy_exported": strategy_present,
            "safety_guard_passed": safety_passed,
            "safety_reasons": safety_reasons,
            "docker_available": shutil.which("docker") is not None,
            "next_manual_command": self.build_docker_command(),
        }

    def build_docker_command(self) -> str:
        return "docker compose --profile freqtrade-dry-run run --rm freqtrade-dry-run --help"

    def write_run_manifest(
        self,
        output_path: str | Path = "reports/freqtrade/latest_manifest.json",
    ) -> Path:
        status = self.get_status()
        payload = {
            "generated_config_path": self.config_path,
            "strategy_path": self.strategy_path,
            "docker_command_preview": self.build_docker_command(),
            "safety_status": status,
            "generated_at": datetime.now(UTC).isoformat(),
            "mode": "dry_run",
            "live_trading_enabled": False,
        }
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return path
