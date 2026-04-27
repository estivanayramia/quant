from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FreqtradeDryRunAdapter:
    enabled: bool = False
    mode: str = "dry_run_only"
    live_trading_allowed: bool = False

    def available(self) -> bool:
        return self.enabled and self.mode == "dry_run_only" and not self.live_trading_allowed

    def run(self) -> None:
        if not self.available():
            msg = "Freqtrade dry-run adapter is disabled or not in dry-run-only mode."
            raise RuntimeError(msg)
