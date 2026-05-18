from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.research.strategy_factory.strategy_variant_generator import (
    write_strategy_variants_report,
)


def write_strategy_variant_registry(
    *,
    output_root: str | Path = ".",
    target_count: int = 1000,
) -> dict[str, Any]:
    return write_strategy_variants_report(output_root=output_root, target_count=target_count)
