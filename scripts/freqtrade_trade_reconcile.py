from __future__ import annotations

from rich import print

from quant_os.integrations.freqtrade.trade_reconciliation import reconcile_freqtrade_trades

if __name__ == "__main__":
    print(reconcile_freqtrade_trades())
