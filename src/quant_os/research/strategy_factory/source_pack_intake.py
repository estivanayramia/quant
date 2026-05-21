from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Any

from quant_os.research.strategy_factory.campaign_common import (
    RESUME_COMMAND,
    load_report,
    safe_payload,
    stable_id,
    write_campaign_state,
    write_json_md,
)

DEFAULT_PRIMARY_SOURCE_PACK = Path(
    "C:/Users/estiv/Downloads/quant_project_source_pack_20260520_v4_github_repo_research.zip"
)
DEFAULT_SUPPORTING_SOURCE_PACK = Path(
    "C:/Users/estiv/Downloads/quant_project_source_pack_20260520_v3_media_researched.zip"
)


def build_source_pack_intake(
    *,
    primary_source_pack: str | Path = DEFAULT_PRIMARY_SOURCE_PACK,
    supporting_source_pack: str | Path | None = DEFAULT_SUPPORTING_SOURCE_PACK,
    output_root: str | Path = ".",
) -> dict[str, Any]:
    primary = Path(primary_source_pack)
    supporting = Path(supporting_source_pack) if supporting_source_pack else None
    primary_docs = _read_pack_docs(primary)
    supporting_docs = _read_pack_docs(supporting) if supporting and supporting.exists() else {}
    combined_text = "\n".join(primary_docs.values())

    ideas = _build_ideas(combined_text)
    state = load_report(
        output_root=output_root,
        report_dir="state",
        json_name="latest_state.json",
    )
    readiness_status = state.get("money_worthy_readiness_status", "MONEY_WORTHY_NOT_PROVEN")
    blockers = list(state.get("blockers") or ["PUBLIC_FORWARD_EVIDENCE_NOT_PROVEN"])

    return safe_payload(
        status="SOURCE_PACK_INTAKE_READY" if primary.exists() else "SOURCE_PACK_INTAKE_MISSING_PRIMARY",
        schema_version="source_pack_intake_v1",
        primary_source_pack=str(primary),
        supporting_source_pack=str(supporting) if supporting else None,
        primary_file_count=len(primary_docs),
        supporting_file_count=len(supporting_docs),
        source_pack_files_used=_selected_source_files(primary_docs),
        social_or_repo_claims_are_proof=False,
        proof_status_changed=False,
        money_worthy_readiness_status=readiness_status,
        existing_blockers_preserved=blockers,
        accepted_idea_count=sum(1 for idea in ideas if idea["decision"] == "ACCEPT"),
        deferred_idea_count=sum(1 for idea in ideas if idea["decision"] == "DEFER"),
        rejected_idea_count=sum(1 for idea in ideas if idea["decision"] == "REJECT"),
        ideas=ideas,
        safety_notes=[
            "source packs are hypothesis and repo-research input only",
            "PnL screenshots, stars, popularity, claims, and engagement are never proof",
            "no dependency or API is adopted without license/source/security review",
            "all accepted ideas require public read-only data and fake-money replay",
        ],
        next_action="Use source-backed tranche plan before generating more campaign variants.",
        exact_resume_command=RESUME_COMMAND,
    )


def write_source_pack_intake_report(
    *,
    output_root: str | Path = ".",
    primary_source_pack: str | Path = DEFAULT_PRIMARY_SOURCE_PACK,
    supporting_source_pack: str | Path | None = DEFAULT_SUPPORTING_SOURCE_PACK,
) -> dict[str, Any]:
    payload = build_source_pack_intake(
        primary_source_pack=primary_source_pack,
        supporting_source_pack=supporting_source_pack,
        output_root=output_root,
    )
    write_campaign_state(
        output_root=output_root,
        source_pack_intake_status=payload["status"],
        source_pack_ideas_accepted=payload["accepted_idea_count"],
        source_pack_ideas_rejected=payload["rejected_idea_count"],
        source_pack_ideas_deferred=payload["deferred_idea_count"],
        blockers=payload["existing_blockers_preserved"],
        next_action=payload["next_action"],
        exact_resume_command=payload["exact_resume_command"],
    )
    lines = [
        "Source packs are hypothesis inputs only; no proof status changed.",
        f"Status: {payload['status']}",
        f"Primary files read: {payload['primary_file_count']}",
        f"Accepted ideas: {payload['accepted_idea_count']}",
        f"Deferred ideas: {payload['deferred_idea_count']}",
        f"Rejected ideas: {payload['rejected_idea_count']}",
        f"Money-worthy readiness remains: {payload['money_worthy_readiness_status']}",
    ]
    for idea in payload["ideas"]:
        lines.append(
            f"- {idea['decision']}: {idea['strategy_family']} "
            f"({idea['reason_code']}) -> {idea['minimum_viable_test']}"
        )
    return write_json_md(
        payload,
        output_root=output_root,
        report_dir="source_pack_intake",
        json_name="latest_source_pack_intake.json",
        md_name="latest_source_pack_intake.md",
        title="Source Pack Intake",
        lines=lines,
    )


def _read_pack_docs(path: Path | None) -> dict[str, str]:
    if path is None or not path.exists():
        return {}
    docs: dict[str, str] = {}
    if path.is_dir():
        for child in path.rglob("*"):
            if child.is_file() and child.suffix.lower() in {".md", ".csv", ".json", ".jsonl", ".txt"}:
                docs[str(child.relative_to(path))] = _safe_read_text(child)
        return docs
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                lower = name.lower()
                if lower.endswith((".md", ".csv", ".json", ".jsonl", ".txt")) and _is_useful_source_doc(lower):
                    with archive.open(name) as handle:
                        docs[name] = handle.read().decode("utf-8", errors="replace")
        return docs
    return {path.name: _safe_read_text(path)}


def _safe_read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _is_useful_source_doc(name: str) -> bool:
    return any(
        token in name
        for token in [
            "priority_repo_decisions",
            "repo_relevance_matrix",
            "repo_research_backlog",
            "github_repo_research_addendum",
            "web_researched_notes",
            "repo_cards/",
            "source_audit",
            "discarded_themes",
        ]
    )


def _selected_source_files(docs: dict[str, str]) -> list[str]:
    priority = [
        name
        for name in docs
        if any(
            token in name.lower()
            for token in ["priority_repo_decisions", "repo_relevance_matrix", "repo_research_backlog"]
        )
    ]
    return sorted(priority)[:25]


def _build_ideas(text: str) -> list[dict[str, Any]]:
    lower = text.lower()
    specs = [
        {
            "trigger": ["py-clob-client-v2", "poly_data", "clob"],
            "source_pack_file_or_card": "github_repo_research/priority_repo_decisions.md",
            "source_type": "v4_repo_research_primary",
            "strategy_family": "prediction_market_read_only_clob_replay",
            "required_public_data": [
                "public market metadata",
                "public CLOB snapshots",
                "public trades/order-filled events",
                "resolved outcomes",
            ],
            "minimum_viable_test": "offline schema fixture plus freshness, stale-book, and resolved-label checks",
            "validation_blocker": "PUBLIC_PREDICTION_MARKET_DATA_LANE_NOT_BUILT",
            "expected_failure_mode": "stale snapshots or missing resolution labels create fantasy fills",
            "repo_module_affected": "src/quant_os/research/prediction_markets/; src/quant_os/data/; src/quant_os/replay/",
            "changes_variant_generation": True,
            "changes_public_forward_collection": True,
            "changes_overfit_repeatability_capacity_validation": True,
            "decision": "ACCEPT",
            "reason_code": "SOURCE_BACKED_PUBLIC_REPLAY_LANE",
        },
        {
            "trigger": ["prediction-market-backtesting", "nautilus_trader", "partial-fill"],
            "source_pack_file_or_card": "github_repo_research/repo_research_backlog.md",
            "source_type": "v4_repo_research_primary",
            "strategy_family": "replay_realism_veto_layer",
            "required_public_data": ["orderbook depth", "spread", "latency timestamp", "future public mark"],
            "minimum_viable_test": "stale book, adverse selection, partial-fill, spread, and latency stress fixtures",
            "validation_blocker": "REPLAY_REALISM_STRESS_NOT_APPLIED",
            "expected_failure_mode": "OHLC-only or guaranteed fills overstate edge",
            "repo_module_affected": "src/quant_os/replay/; src/quant_os/risk/; src/quant_os/validation/",
            "changes_variant_generation": True,
            "changes_public_forward_collection": False,
            "changes_overfit_repeatability_capacity_validation": True,
            "decision": "ACCEPT",
            "reason_code": "REPLAY_REALISM_BEFORE_EDGE",
        },
        {
            "trigger": ["binance-public-data", "ccxt", "freqtrade"],
            "source_pack_file_or_card": "github_repo_research/priority_repo_decisions.md",
            "source_type": "v4_repo_research_primary",
            "strategy_family": "crypto_public_data_quality_filtered_momentum",
            "required_public_data": ["public candles", "public spread/depth proxy", "future public marks"],
            "minimum_viable_test": "Kraken/Binance-compatible replay with stricter data provenance and cost stress",
            "validation_blocker": "PUBLIC_FORWARD_EVIDENCE_NOT_PROVEN",
            "expected_failure_mode": "generic crypto drift disappears after costs and forward replay",
            "repo_module_affected": "src/quant_os/research/crypto/; src/quant_os/data/; src/quant_os/replay/",
            "changes_variant_generation": True,
            "changes_public_forward_collection": True,
            "changes_overfit_repeatability_capacity_validation": True,
            "decision": "ACCEPT",
            "reason_code": "CRYPTO_DATA_PROVENANCE_TIGHTENING",
        },
        {
            "trigger": ["source ingestion", "trafilatura", "docling", "files-to-prompt", "firecrawl"],
            "source_pack_file_or_card": "project_sources/08_GITHUB_REPO_RESEARCH_ADDENDUM.md",
            "source_type": "v4_repo_research_primary",
            "strategy_family": "source_quality_filtering_and_evidence_pack",
            "required_public_data": ["source URL", "retrieval timestamp", "content hash", "license/security note"],
            "minimum_viable_test": "compact evidence-card fixture with hashes and explicit proof/non-proof labels",
            "validation_blocker": "SOURCE_PROVENANCE_NOT_RECORDED",
            "expected_failure_mode": "untrusted social/media text accidentally becomes strategy evidence",
            "repo_module_affected": "src/quant_os/research/strategy_factory/; reports/thousand_strategy_campaign/",
            "changes_variant_generation": True,
            "changes_public_forward_collection": False,
            "changes_overfit_repeatability_capacity_validation": True,
            "decision": "ACCEPT",
            "reason_code": "SOURCE_QUALITY_BEFORE_VARIANT_EXPANSION",
        },
        {
            "trigger": ["validation", "walk-forward", "qlib", "lean", "overfit"],
            "source_pack_file_or_card": "github_repo_research/repo_relevance_matrix.csv",
            "source_type": "v4_repo_research_primary",
            "strategy_family": "calibration_holdout_walk_forward_protocol",
            "required_public_data": ["pre-registered split", "holdout window", "purged labels", "placebo seed"],
            "minimum_viable_test": "holdout/walk-forward fixture that blocks neighboring-parameter fragility",
            "validation_blocker": "HOLDOUT_OR_FORWARD_WINDOW_NOT_PROVEN",
            "expected_failure_mode": "broad variant search finds a false discovery",
            "repo_module_affected": "src/quant_os/proving/; src/quant_os/validation/",
            "changes_variant_generation": True,
            "changes_public_forward_collection": False,
            "changes_overfit_repeatability_capacity_validation": True,
            "decision": "ACCEPT",
            "reason_code": "MULTIPLE_TESTING_AND_CALIBRATION_HARDENING",
        },
        {
            "trigger": ["polybench", "market metadata", "resolved outcomes", "mutually exclusive"],
            "source_pack_file_or_card": "github_repo_research/repo_research_backlog.md",
            "source_type": "v4_repo_research_primary",
            "strategy_family": "prediction_market_structural_consistency_checks",
            "required_public_data": [
                "mutually exclusive market set",
                "negation pair metadata",
                "best bid/ask",
                "resolution rule",
            ],
            "minimum_viable_test": "fixture that proves basket/negation mispricing is net of spread and settlement risk",
            "validation_blocker": "PREDICTION_MARKET_STRUCTURE_NOT_REPLAYABLE",
            "expected_failure_mode": "apparent arbitrage disappears after fees, spread, or settlement-rule mismatch",
            "repo_module_affected": "src/quant_os/research/prediction_markets/; src/quant_os/risk/",
            "changes_variant_generation": True,
            "changes_public_forward_collection": True,
            "changes_overfit_repeatability_capacity_validation": True,
            "decision": "ACCEPT",
            "reason_code": "STRUCTURAL_EDGE_REQUIRES_LOCKED_PUBLIC_REPLAY",
        },
        {
            "trigger": ["license", "security", "dependency", "adopt"],
            "source_pack_file_or_card": "github_repo_research/priority_repo_decisions.md",
            "source_type": "v4_repo_research_primary",
            "strategy_family": "dependency_license_security_gate",
            "required_public_data": ["repo URL", "license", "maintenance signal", "security review note"],
            "minimum_viable_test": "dependency intake card blocks adoption until source/license/security review passes",
            "validation_blocker": "DEPENDENCY_REVIEW_NOT_COMPLETED",
            "expected_failure_mode": "repo pattern or client adopted before safe public-data review",
            "repo_module_affected": "src/quant_os/data/; src/quant_os/research/; reports/research/",
            "changes_variant_generation": False,
            "changes_public_forward_collection": False,
            "changes_overfit_repeatability_capacity_validation": True,
            "decision": "ACCEPT",
            "reason_code": "NO_DEPENDENCY_ADOPTION_WITHOUT_REVIEW",
        },
        {
            "trigger": ["veto", "no-trade", "conflict", "adverse selection", "stale"],
            "source_pack_file_or_card": "github_repo_research/repo_research_backlog.md",
            "source_type": "v4_repo_research_primary",
            "strategy_family": "source_backed_no_trade_veto_behavior",
            "required_public_data": ["source freshness", "spread cap", "cross-market agreement", "execution uncertainty"],
            "minimum_viable_test": "candidate is blocked when expected edge is smaller than replay uncertainty",
            "validation_blocker": "CONFLICT_DETECTOR_NOT_SOURCE_BACKED",
            "expected_failure_mode": "more indicators add noise instead of blocking false entries",
            "repo_module_affected": "src/quant_os/risk/strategy_conflict_detector.py",
            "changes_variant_generation": True,
            "changes_public_forward_collection": True,
            "changes_overfit_repeatability_capacity_validation": True,
            "decision": "ACCEPT",
            "reason_code": "FEWER_HIGHER_QUALITY_TRADES",
        },
        {
            "trigger": ["weather", "polyweather", "temperature"],
            "source_pack_file_or_card": "github_repo_research/repo_cards/yangyuan-zhen__PolyWeather.md",
            "source_type": "v4_repo_card_reference",
            "strategy_family": "weather_forecast_market_calibration",
            "required_public_data": ["issue-time forecast", "market bucket price", "resolved weather observation"],
            "minimum_viable_test": "single-city fixture with issue-time forecast alignment and resolved outcome labels",
            "validation_blocker": "WEATHER_OUTCOME_DATA_PATH_NOT_READY",
            "expected_failure_mode": "forecast timestamps leak resolution-period information",
            "repo_module_affected": "src/quant_os/research/prediction_markets/; src/quant_os/validation/",
            "changes_variant_generation": True,
            "changes_public_forward_collection": False,
            "changes_overfit_repeatability_capacity_validation": True,
            "decision": "DEFER",
            "reason_code": "NEEDS_PUBLIC_OUTCOME_ALIGNMENT",
        },
        {
            "trigger": [
                "copy trade",
                "wallet mirror",
                "trade-copier",
                "arbitrage-bot",
                "betting-bot",
            ],
            "source_pack_file_or_card": "github_repo_research/priority_repo_decisions.md",
            "source_type": "v4_repo_research_primary",
            "strategy_family": "copy_trading_wallet_mirroring",
            "required_public_data": ["not applicable"],
            "minimum_viable_test": "none; unsafe execution logic rejected",
            "validation_blocker": "UNSAFE_COPY_TRADING_WALLET_MIRRORING",
            "expected_failure_mode": "unverifiable social claims and unsafe wallet-following behavior",
            "repo_module_affected": "none",
            "changes_variant_generation": True,
            "changes_public_forward_collection": False,
            "changes_overfit_repeatability_capacity_validation": False,
            "decision": "REJECT",
            "reason_code": "UNSAFE_COPY_TRADING_REJECTED",
        },
        {
            "trigger": ["cloakb", "anti-bot", "captcha", "proxy"],
            "source_pack_file_or_card": "github_repo_research/priority_repo_decisions.md",
            "source_type": "v4_repo_research_primary",
            "strategy_family": "stealth_scraping_or_anti_bot_collection",
            "required_public_data": ["not applicable"],
            "minimum_viable_test": "none; stealth collection rejected",
            "validation_blocker": "STEALTH_BROWSER_OR_ANTI_BOT_TOOLING",
            "expected_failure_mode": "policy-unsafe data acquisition path",
            "repo_module_affected": "none",
            "changes_variant_generation": True,
            "changes_public_forward_collection": False,
            "changes_overfit_repeatability_capacity_validation": False,
            "decision": "REJECT",
            "reason_code": "STEALTH_TOOLING_REJECTED",
        },
    ]
    ideas = []
    for spec in specs:
        if any(token in lower for token in spec.pop("trigger")):
            idea = dict(spec)
            idea["id"] = stable_id("spi", idea, length=12)
            idea["accept_reject_defer_decision"] = idea["decision"]
            ideas.append(idea)
    if not ideas:
        ideas.append(
            {
                "id": "spi_no_usable_leads",
                "source_pack_file_or_card": "source_pack",
                "source_type": "source_pack",
                "strategy_family": "none",
                "required_public_data": [],
                "minimum_viable_test": "none",
                "validation_blocker": "NO_SOURCE_BACKED_PUBLIC_DATA_PATH",
                "expected_failure_mode": "source pack did not contain usable public-data leads",
                "repo_module_affected": "none",
                "changes_variant_generation": False,
                "changes_public_forward_collection": False,
                "changes_overfit_repeatability_capacity_validation": False,
                "decision": "DEFER",
                "accept_reject_defer_decision": "DEFER",
                "reason_code": "NO_USABLE_SOURCE_BACKED_LEADS",
            }
        )
    return ideas
