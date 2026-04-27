from __future__ import annotations


class LiteLLMProvider:
    def __init__(self, allow_real_provider_calls: bool = False) -> None:
        self.allow_real_provider_calls = allow_real_provider_calls

    def complete(self, prompt: str) -> str:
        if not self.allow_real_provider_calls:
            return f"MOCK_LITELLM_DISABLED:{prompt[:40]}"
        msg = "Real LiteLLM calls are not implemented in Milestone 2."
        raise RuntimeError(msg)
