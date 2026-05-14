from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.research.replay_candidates.pm_crypto_updown_alignment import (
    DEFAULT_FIXTURE_ROOT,
    build_pm_crypto_updown_dataset,
)
from quant_os.research.replay_candidates.pm_crypto_updown_baseline_prep import (
    prepare_pm_crypto_updown_baseline_rows,
)
from quant_os.research.replay_candidates.pm_crypto_updown_quality import (
    evaluate_pm_crypto_updown_quality,
)

REPORT_ROOT = Path("reports/sequence36/replay_dataset")


def write_pm_crypto_updown_dataset_report(
    *,
    fixture_root: str | Path = DEFAULT_FIXTURE_ROOT,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    dataset = build_pm_crypto_updown_dataset(fixture_root=fixture_root)
    quality = evaluate_pm_crypto_updown_quality(dataset)
    baseline_rows = prepare_pm_crypto_updown_baseline_rows(dataset["rows"])
    payload = {
        "schema_version": "pm_crypto_updown_dataset_report_v1",
        "sequence": "36",
        "candidate_id": dataset["candidate_id"],
        "readiness_status": quality["quality_status"],
        "rows": baseline_rows,
        "baseline_prep_rows": baseline_rows,
        **{
            key: value
            for key, value in quality.items()
            if key
            not in {
                "schema_version",
                "sequence",
                "candidate_id",
                "quality_status",
            }
        },
    }
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_pm_crypto_updown_dataset.json"
    md_path = root / "latest_pm_crypto_updown_dataset.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 36 PM Crypto UP/DOWN Replay Dataset",
        "",
        "Candidate-specific replay dataset shape. No execution authority and no profitability claim.",
        "",
        f"Status: {payload['readiness_status']}",
        f"Rows: {payload['row_count']}",
        f"Replay-ready rows: {payload['replay_ready_row_count']}",
        f"Markets: {payload['market_count']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        "",
        "## Blockers",
    ]
    lines.extend(f"- {item}" for item in (payload["blockers"] or ["None"]))
    lines.extend(["", "## Caveats"])
    lines.extend(f"- {item}" for item in (payload["caveats"] or ["None"]))
    lines.extend(["", "## Quality Counts"])
    lines.extend(
        [
            f"- CLOB coverage: {payload['clob_coverage']}",
            f"- Spot coverage: {payload['spot_coverage']}",
            f"- Wide spread rows: {payload['wide_spread_count']}",
            f"- Low liquidity rows: {payload['low_liquidity_count']}",
            f"- Unresolved label rows: {payload['unresolved_label_count']}",
        ]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
