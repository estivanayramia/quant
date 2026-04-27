from __future__ import annotations

from dataclasses import dataclass
from importlib.util import find_spec


@dataclass
class AlpacaPaperAdapter:
    paper_trading_enabled: bool = False
    mode: str = "paper"
    live_trading_allowed: bool = False

    def sdk_available(self) -> bool:
        return find_spec("alpaca") is not None

    def available(self) -> bool:
        return self.paper_trading_enabled and self.mode == "paper" and not self.live_trading_allowed

    def assert_safe(self) -> None:
        if self.live_trading_allowed or self.mode == "live":
            msg = "Alpaca scaffold rejects live mode."
            raise RuntimeError(msg)

    def submit_order(self, *_args, **_kwargs) -> None:
        self.assert_safe()
        msg = "Alpaca paper adapter is a scaffold and does not call the API in Milestone 2."
        raise RuntimeError(msg)
