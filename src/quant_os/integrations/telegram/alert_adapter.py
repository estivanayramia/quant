from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TelegramAlertAdapter:
    enabled: bool = False
    token: str = ""
    chat_id: str = ""
    sent_messages: list[str] = field(default_factory=list)

    def send_summary(self, message: str) -> bool:
        if not self.enabled:
            self.sent_messages.append(f"MOCK_TELEGRAM:{message}")
            return True
        if not self.token or not self.chat_id:
            msg = "Telegram is enabled but token/chat_id are missing."
            raise RuntimeError(msg)
        self.sent_messages.append(message)
        return True

    def send_failure(self, message: str) -> bool:
        return self.send_summary(f"FAILURE:{message}")

    def place_order(self, *_args, **_kwargs) -> None:
        raise PermissionError("Telegram alerts cannot place orders.")

    def change_risk_limit(self, *_args, **_kwargs) -> None:
        raise PermissionError("Telegram alerts cannot change risk limits.")

    def release_quarantine(self, *_args, **_kwargs) -> None:
        raise PermissionError("Telegram alerts cannot release quarantine.")

    def disable_kill_switch(self, *_args, **_kwargs) -> None:
        raise PermissionError("Telegram alerts cannot disable the kill switch.")
