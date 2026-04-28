from __future__ import annotations

from quant_os.integrations.freqtrade.runner import FreqtradeRunner

if __name__ == "__main__":
    print(FreqtradeRunner().start().to_dict())
