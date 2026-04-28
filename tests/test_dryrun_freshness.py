from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from quant_os.monitoring.freshness import artifact_freshness


def test_freshness_reports_missing_artifact(local_project):
    payload = artifact_freshness("missing.json")
    assert payload["status"] == "UNAVAILABLE"


def test_freshness_warns_when_artifact_is_stale(local_project):
    path = Path("artifact.json")
    path.write_text("{}", encoding="utf-8")
    stale = datetime.now(UTC) - timedelta(hours=25)
    os.utime(path, (stale.timestamp(), stale.timestamp()))
    payload = artifact_freshness(path, warn_hours=24, fail_hours=72)
    assert payload["status"] == "WARN"
