from __future__ import annotations

from rich import print

from quant_os.integrations.freqtrade.trade_normalizer import ingest_trade_artifacts

if __name__ == "__main__":
    print(ingest_trade_artifacts())
