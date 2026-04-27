from __future__ import annotations

from quant_os.adapters.ai_mock import MockAIProvider


def test_mock_ai_provider_returns_deterministic_output():
    provider = MockAIProvider()
    first = provider.critique_strategy("s1", {"b": 2, "a": 1})
    second = provider.critique_strategy("s1", {"a": 1, "b": 2})
    assert first == second
