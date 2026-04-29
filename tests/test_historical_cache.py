from __future__ import annotations

from pathlib import Path

import pytest

from quant_os.data.historical_cache import assert_safe_import_path


def test_secret_like_historical_file_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "exchange_secret_prices.csv"
    path.write_text("timestamp,symbol,open,high,low,close,volume\n", encoding="utf-8")
    with pytest.raises(ValueError, match="secret-like"):
        assert_safe_import_path(path, allow_external_path=True)
