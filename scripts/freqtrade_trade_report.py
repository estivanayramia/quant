from __future__ import annotations

from rich import print

from quant_os.integrations.freqtrade.trade_reporting import write_freqtrade_trade_report

if __name__ == "__main__":
    print(write_freqtrade_trade_report())
