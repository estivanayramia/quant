from __future__ import annotations

from pathlib import Path

from quant_os.adapters.event_store_jsonl import JsonlEventStore
from quant_os.autonomy.tasks import run_drift_checks
from quant_os.data.demo_data import seed_demo_data
from quant_os.drift.data_drift import detect_data_drift


def test_drift_detectors_generate_report(local_project):
    store = JsonlEventStore()
    seed_demo_data(event_store=store)
    summary = run_drift_checks(store)
    assert summary["status"] in {"passed", "drift_detected"}
    assert Path("reports/drift/latest_drift.json").exists()


def test_data_drift_detects_large_volume_shift(spy_frame):
    shifted = spy_frame.copy()
    shifted.loc[len(shifted) // 2 :, "volume"] *= 100
    signal = detect_data_drift(shifted, volume_shift_pct_threshold=0.5)
    assert signal.detected
