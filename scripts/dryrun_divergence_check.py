from __future__ import annotations

from rich import print

from quant_os.monitoring.divergence import check_dryrun_divergence

if __name__ == "__main__":
    print(check_dryrun_divergence())
