from __future__ import annotations

import pandas as pd

from quant_os.features.sessions import add_session_features, session_bucket


def test_session_labels_are_deterministic(spy_frame) -> None:
    assert session_bucket(pd.Timestamp("2025-01-01T01:00:00Z")) == "asia"
    assert session_bucket(pd.Timestamp("2025-01-01T08:00:00Z")) == "london"
    assert session_bucket(pd.Timestamp("2025-01-01T15:00:00Z")) == "new_york"
    first = add_session_features(spy_frame)
    second = add_session_features(spy_frame)
    assert first["session"].tolist() == second["session"].tolist()
    assert "session_high_so_far" in first.columns
