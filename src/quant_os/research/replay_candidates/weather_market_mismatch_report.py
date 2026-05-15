from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.research.replay_candidates.weather_market_mismatch_candidate import (
    write_weather_market_mismatch_candidate_report,
)


def write_weather_market_mismatch_report(
    *,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    return write_weather_market_mismatch_candidate_report(output_root=output_root)

