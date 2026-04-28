from __future__ import annotations

from rich import print

from quant_os.integrations.freqtrade.artifact_scanner import scan_freqtrade_artifacts

if __name__ == "__main__":
    print(scan_freqtrade_artifacts())
