from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_walk_forward_report(
    payload: dict[str, Any],
    *,
    output_root: str | Path = ".",
) -> dict[str, str]:
    root = Path(output_root) / "reports" / "sequence2" / "walk_forward"
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_walk_forward.json"
    md_path = root / "latest_walk_forward.md"
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    lines = [
        "# Sequence 2 Walk-Forward Validation",
        "",
        "Research evidence only. No live trading.",
        "",
        f"Status: {payload['status']}",
        f"Splits: {payload['split_count']}",
        f"Live trading enabled: {payload['live_trading_enabled']}",
        "",
        "## Warnings",
    ]
    lines.extend(f"- {item}" for item in (payload.get("warnings") or ["None"]))
    lines.extend(["", "## Splits"])
    for item in payload.get("splits", []):
        lines.append(
            "- split {split_id}: param={param:.2f} train={train:.4f} "
            "test={test:.4f}".format(
                split_id=item["split_id"],
                param=float(item["selected_min_edge_bps"]),
                train=float(item["train_metrics"]["expectancy_after_costs_bps"]),
                test=float(item["test_metrics"]["expectancy_after_costs_bps"]),
            )
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
