from __future__ import annotations

from quant_os.integrations.freqtrade.trade_artifacts import ParsedTradeArtifact
from quant_os.integrations.freqtrade.trade_normalizer import normalize_trade_artifacts


def test_normalizer_maps_common_freqtrade_fields(local_project):
    parsed = ParsedTradeArtifact(
        source_file="fixture.json",
        artifact_type="json",
        records=[
            {
                "id": 1,
                "strategy": "QuantOSDryRunStrategy",
                "pair": "BTC/USDT",
                "open_rate": 50000,
                "close_rate": 50100,
                "stake_amount": 10,
                "profit_abs": 0.02,
                "dry_run": True,
            }
        ],
    )
    payload = normalize_trade_artifacts([parsed])
    record = payload["records"][0]
    assert record["pair"] == "BTC/USDT"
    assert record["symbol"] == "BTC-USDT"
    assert record["side"] == "long"
    assert record["raw_payload"]["inferred_side"] is True


def test_normalizer_preserves_unknown_fields(local_project):
    parsed = ParsedTradeArtifact(
        source_file="fixture.json",
        artifact_type="json",
        records=[{"pair": "BTC/USDT", "custom_field": "kept"}],
    )
    record = normalize_trade_artifacts([parsed])["records"][0]
    assert record["raw_payload"]["custom_field"] == "kept"


def test_normalizer_does_not_infer_shorts(local_project):
    parsed = ParsedTradeArtifact(
        source_file="fixture.json",
        artifact_type="json",
        records=[{"pair": "BTC/USDT", "side": "short"}],
    )
    record = normalize_trade_artifacts([parsed])["records"][0]
    assert record["side"] == "short"
    assert "inferred_side" not in record["raw_payload"]
