from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.autonomy.live_market_sim_common import load_json
from quant_os.autonomy.multi_market_live_sim_common import ROOT, mm_hash, safe_report_payload
from quant_os.readiness.canary_readiness_common import write_json_markdown_report

REPORT_DIR = ROOT / "crypto_spot"


def build_crypto_spot_live_sim_ledger(
    *,
    output_root: str | Path = ".",
    fills_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    fills_payload = fills_payload or load_json(
        "reports/multi_market_live_sim/crypto_spot/latest_crypto_fills.json",
        output_root=output_root,
    ) or {}
    entries = []
    for fill in list(fills_payload.get("fake_fills", []) or []):
        entries.append(
            {
                "ledger_entry_id": f"csll_{mm_hash(fill)}",
                **fill,
                "position_state": "OPEN_THEN_MARKED_FAKE",
                "no_transmit": True,
                "fake_money": True,
                "actual_order_count": 0,
                "actual_cancel_count": 0,
            }
        )
    return safe_report_payload(
        schema_version="crypto_spot_live_sim_ledger_v1",
        status="CRYPTO_LIVE_SIM_LEDGER_UPDATED",
        position_state="FAKE_POSITIONS_TRACKED" if entries else "NO_FAKE_POSITION",
        ledger_entries=entries,
        fake_fill_count=len(entries),
        blockers=[],
        next_action="Mark fake crypto positions from future public prices." if entries else "Collect more fake fills.",
    )


def write_crypto_spot_live_sim_ledger_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = build_crypto_spot_live_sim_ledger(output_root=output_root)
    payload["report_paths"] = write_json_markdown_report(
        payload,
        output_root=output_root,
        report_dir=REPORT_DIR,
        json_name="latest_crypto_ledger.json",
        md_name="latest_crypto_ledger.md",
        title="Crypto Spot Live Sim Ledger",
        summary="Fake ledger for no-transmit crypto spot simulated positions.",
    )
    return payload
