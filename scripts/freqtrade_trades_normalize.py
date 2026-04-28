from __future__ import annotations

from rich import print

from quant_os.integrations.freqtrade.trade_normalizer import normalize_trade_artifacts

if __name__ == "__main__":
    print(normalize_trade_artifacts())
