from __future__ import annotations

from typing import Any

from quant_os.monitoring.dryrun_history import append_history_record, build_history_record


def append_freqtrade_dryrun_history(source: str = "freqtrade") -> dict[str, Any]:
    return append_history_record(build_history_record(source=source))
