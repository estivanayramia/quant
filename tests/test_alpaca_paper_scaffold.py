from __future__ import annotations

import pytest

from quant_os.integrations.alpaca.paper_adapter import AlpacaPaperAdapter


def test_alpaca_paper_scaffold_rejects_live_mode():
    adapter = AlpacaPaperAdapter(paper_trading_enabled=True, mode="live", live_trading_allowed=True)
    with pytest.raises(RuntimeError):
        adapter.assert_safe()


def test_alpaca_paper_scaffold_does_not_require_sdk():
    adapter = AlpacaPaperAdapter(paper_trading_enabled=False)
    assert adapter.available() is False
