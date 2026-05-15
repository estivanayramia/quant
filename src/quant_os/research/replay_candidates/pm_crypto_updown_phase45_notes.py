from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quant_os.research.replay_candidates.pm_crypto_updown_schema import CANDIDATE_ID
from quant_os.research.social_intake.social_capture_models import SOCIAL_INTAKE_SAFETY

REPORT_ROOT = Path("reports/sequence45/reference_notes")


def build_pm_crypto_updown_phase45_reference_notes() -> dict[str, Any]:
    return {
        "schema_version": "pm_crypto_updown_phase45_reference_notes_v1",
        "sequence": "45",
        "candidate_id": CANDIDATE_ID,
        "candidate_backlog_families": [
            "pm_lp_refresh_lag_arbitrage",
            "pm_stale_lp_quote_arbitrage",
        ],
        "backlog_summary": (
            "Public social artifacts can inspire replayable stale-quote hypotheses, "
            "but they are not proof and must not become execution logic."
        ),
        "allowed_backlog_use": [
            "candidate backlog",
            "arbitrage-family registry",
            "discriminator inspiration",
            "future replay-candidate pack",
            "failure-mode checklist",
        ],
        "forbidden_backlog_use": [
            "copy trading",
            "wallet mirroring",
            "live order logic",
            "assuming claimed profit and loss is real",
            "using wallet labels without replayable evidence",
        ],
        "potential_future_features": [
            "execution rate",
            "trade density",
            "inter-trade interval",
            "two-sided quoting ratio",
            "spread maintenance",
            "quote refresh delay",
            "market underreaction gap",
            "taker burst confirmation",
            "directional spot trigger",
            "liquidity reward concentration",
            "stale opposite-side quote window",
        ],
        "kelly_sizing_policy": {
            "sizing_enabled": False,
            "note": (
                "No Kelly sizing until candidate beats baselines/placebos, passes anti-overfit, "
                "survives cost/fill, and has calibrated probabilities from sufficient evidence."
            ),
            "future_only": [
                "fractional Kelly cap concept",
                "bankroll and risk-of-ruin framing",
                "calibrated probability requirement",
            ],
        },
        "social_intake_warning_categories": ["LLM_DISCRETIONARY_TRADING_PROMPT"],
        "llm_discretionary_trading_prompt_policy": {
            "allowed": [
                "feature translation",
                "hypothesis generation",
                "converting vague chart language into deterministic measurable features",
            ],
            "forbidden": [
                "direct buy/sell/wait decisions",
                "portfolio advice",
                "direct execution",
                "signal promotion without replay/OOS validation",
            ],
        },
        "agent_feedback_loop_note": (
            "Agents need feedback loops, not static perfect prompts; durable instruction changes "
            "should be reviewed like code through pull requests."
        ),
        "reference_only_external_repos": {
            "google_skills": {
                "use": "skill organization inspiration",
                "vendor_or_install": False,
                "cloud_infra_added": False,
            },
            "scenario_lab": {
                "use": "future evidence packets, approval steps, local corpus, scenario families, calibrated confidence labels",
                "vendor_or_install": False,
                "monte_carlo_added": False,
            },
        },
        "network_fetch_attempted": False,
        **SOCIAL_INTAKE_SAFETY,
        "live_allowed": False,
        "live_promotion_status": "LIVE_BLOCKED",
        "evidence_only": True,
    }


def write_pm_crypto_updown_phase45_reference_notes(
    *,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    payload = build_pm_crypto_updown_phase45_reference_notes()
    payload["report_paths"] = _write_report(payload, output_root=output_root)
    return payload


def _write_report(payload: dict[str, Any], *, output_root: str | Path) -> dict[str, str]:
    root = Path(output_root) / REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "latest_phase45_reference_notes.json"
    md_path = root / "latest_phase45_reference_notes.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Sequence 45 Reference Notes",
        "",
        "Reference-only notes. No execution logic, sizing, wallet workflow, or live authority.",
        "",
        "## Backlog Families",
    ]
    lines.extend(f"- {item}" for item in payload["candidate_backlog_families"])
    lines.extend(
        [
            "",
            "## Kelly Policy",
            payload["kelly_sizing_policy"]["note"],
            "",
            "## Warning Categories",
        ]
    )
    lines.extend(f"- {item}" for item in payload["social_intake_warning_categories"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}
