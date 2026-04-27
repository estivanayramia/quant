from __future__ import annotations

from quant_os.adapters.ai_mock import MockAIProvider
from quant_os.integrations.ai_providers.litellm_adapter import LiteLLMProvider


def test_ai_provider_mesh_uses_mock_without_network():
    assert "MOCK_CRITIQUE" in MockAIProvider().critique_strategy("s1", {"x": 1})
    assert (
        LiteLLMProvider(allow_real_provider_calls=False)
        .complete("hello")
        .startswith("MOCK_LITELLM_DISABLED")
    )
