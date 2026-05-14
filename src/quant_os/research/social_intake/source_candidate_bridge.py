from __future__ import annotations

from typing import Any


def propose_read_only_source_candidates(*, tasks: dict[str, Any]) -> list[dict[str, Any]]:
    proposals = []
    for task in tasks["tasks"]:
        if task["source_post_id"] == "financialdatasets_mcp":
            proposals.append(
                {
                    "candidate_id": "social_financialdatasets_mcp",
                    "source_post_id": task["source_post_id"],
                    "proposal_type": "read_only_source_registry_candidate",
                    "required_checks": [
                        "license_check",
                        "cost_check",
                        "coverage_check",
                        "offline_fixture_check",
                    ],
                    "auto_register": False,
                    "requires_credentials": "unknown_do_not_assume",
                    "network_required_for_tests": False,
                }
            )
    return proposals
