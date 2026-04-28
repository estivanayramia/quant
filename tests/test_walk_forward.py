from __future__ import annotations

from pathlib import Path

from quant_os.research.walk_forward import run_walk_forward_validation, walk_forward_splits


def test_walk_forward_report_generated_or_safely_warns(local_project, spy_frame) -> None:
    assert walk_forward_splits(spy_frame)
    payload = run_walk_forward_validation()
    assert payload["status"] in {"PASS", "WARN", "UNAVAILABLE"}
    assert Path("reports/strategy/walk_forward/latest_walk_forward.json").exists()
