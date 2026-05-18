from __future__ import annotations

from pathlib import Path
from typing import Any

from quant_os.research.strategy_factory.campaign_common import safe_payload, write_json_md


def write_thousand_strategy_fresh_repro_report(*, output_root: str | Path = ".") -> dict[str, Any]:
    payload = safe_payload(
        status="FRESH_REPRO_BLOCKED",
        audit_worktree="C:/Users/estiv/quant-thousand-strategy-audit",
        blockers=["FRESH_WORKTREE_REPRO_NOT_RUN"],
        required_reports=[
            "social_hypotheses",
            "research",
            "variants",
            "tournament",
            "overfit",
            "conflict_detector",
            "repeatability",
            "capacity",
            "final",
            "manual_canary_packet",
        ],
    )
    return write_json_md(
        payload,
        output_root=output_root,
        report_dir="fresh_repro",
        json_name="latest_fresh_repro.json",
        md_name="latest_fresh_repro.md",
        title="Fresh Worktree Reproducibility",
        lines=[f"Status: {payload['status']}", "Fresh worktree audit has not passed."],
    )
