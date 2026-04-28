from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.features.feature_store_local import write_feature_store


def write_feature_report() -> dict[str, Any]:
    summary = write_feature_store()
    lines = [
        "# Feature Build Report",
        "",
        "Deterministic research features only. No live trading.",
        "",
        f"Rows: {summary['rows']}",
        f"Symbols: {', '.join(summary['symbols'])}",
        f"Feature columns: {len(summary['columns'])}",
    ]
    path = Path("reports/features/latest_features.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    summary["report_path"] = str(path)
    return summary
