from __future__ import annotations

from quant_os.data.provider_check import check_historical_providers


def test_provider_check_does_not_require_network(local_project) -> None:
    payload = check_historical_providers()
    assert payload["status"] == "PASS"
    assert payload["internet_required"] is False
    assert payload["providers"]["LOCAL_FILE"]["status"] == "available"
    assert payload["providers"]["CCXT_PUBLIC"]["status"] == "disabled"
