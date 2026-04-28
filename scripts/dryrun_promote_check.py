from __future__ import annotations

from rich import print

from quant_os.monitoring.promotion_readiness import check_promotion_readiness

if __name__ == "__main__":
    print(check_promotion_readiness())
