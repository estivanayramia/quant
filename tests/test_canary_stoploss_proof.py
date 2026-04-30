from __future__ import annotations

from pathlib import Path

from quant_os.canary.stoploss_proof import build_stoploss_proof


def test_stoploss_proof_report_generated(local_project):
    payload = build_stoploss_proof()
    assert payload["status"] == "FUTURE_PROOF_REQUIRED"
    assert "STOPLOSS_ON_EXCHANGE_NOT_PROVEN" in payload["blockers"]
    assert Path("reports/canary/latest_stoploss_proof.json").exists()
