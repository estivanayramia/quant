from __future__ import annotations

from pathlib import Path

from quant_os.canary.checklist import build_canary_checklist


def test_canary_checklist_generated(local_project):
    payload = build_canary_checklist()
    assert payload["status"] == "FAIL"
    assert "HUMAN_APPROVAL_MISSING" in payload["blockers"]
    assert Path("reports/canary/latest_checklist.md").exists()
