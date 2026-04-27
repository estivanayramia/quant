from __future__ import annotations

import pandas as pd


def attach_event_flags(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["event_flag"] = False
    return result
