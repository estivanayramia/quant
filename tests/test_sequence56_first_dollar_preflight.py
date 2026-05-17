from __future__ import annotations

import subprocess
import sys
from pathlib import Path

FIXTURE_DIR = Path("tests/fixtures/profit_candidates/weather_iem_mos_kalshi_100")


def _run_canary_chain(output_root: Path) -> dict[str, object]:
    from quant_os.execution.weather_canary_reconciliation import (
        write_weather_canary_reconciliation_report,
    )
    from quant_os.execution.weather_dry_run_parity import write_weather_dry_run_parity_report
    from quant_os.proving.weather_bounded_shadow_rehearsal import (
        write_weather_bounded_shadow_rehearsal_report,
    )
    from quant_os.proving.weather_candidate_cost_fill_stress import (
        write_weather_candidate_cost_fill_stress_report,
    )
    from quant_os.proving.weather_candidate_replay_recompute import (
        write_weather_candidate_replay_recompute_report,
    )
    from quant_os.proving.weather_candidate_robustness import (
        write_weather_candidate_robustness_report,
    )
    from quant_os.readiness.paper_candidate_audit import write_paper_candidate_audit_report
    from quant_os.readiness.tiny_canary_readiness import write_tiny_canary_readiness_report
    from quant_os.readiness.weather_candidate_lineage_audit import (
        write_weather_candidate_lineage_audit_report,
    )
    from quant_os.readiness.weather_manual_canary_packet import (
        write_weather_manual_canary_packet_report,
    )
    from quant_os.risk.weather_canary_kill_switch import write_weather_canary_kill_switch_report
    from quant_os.risk.weather_tiny_canary_risk import write_weather_tiny_canary_risk_report

    write_paper_candidate_audit_report(output_root=output_root)
    write_weather_candidate_lineage_audit_report(output_root=output_root)
    write_weather_candidate_replay_recompute_report(output_root=output_root)
    write_weather_candidate_robustness_report(output_root=output_root)
    write_weather_candidate_cost_fill_stress_report(output_root=output_root)
    write_weather_bounded_shadow_rehearsal_report(output_root=output_root)
    write_weather_dry_run_parity_report(output_root=output_root)
    write_weather_tiny_canary_risk_report(output_root=output_root)
    write_weather_canary_kill_switch_report(output_root=output_root)
    write_weather_canary_reconciliation_report(output_root=output_root)
    write_weather_manual_canary_packet_report(output_root=output_root)
    return write_tiny_canary_readiness_report(output_root=output_root)


def test_sequence56_missing_local_only_candidate_artifacts_block_preflight(
    local_project: Path,
) -> None:
    from quant_os.readiness.first_dollar_preflight import write_first_dollar_preflight_report

    payload = write_first_dollar_preflight_report(output_root=local_project)

    assert payload["status"] == "FIRST_DOLLAR_PREFLIGHT_BLOCKED_BY_REPRODUCIBILITY"
    assert "reports/profit_campaign/latest_profit_campaign.json" in payload["missing_artifacts"]
    assert payload["live_trading_enabled"] is False
    assert payload["execution_authority"] == "NONE"


def test_sequence56_regenerates_candidate_artifacts_from_tracked_sanitized_fixture(
    local_project: Path,
) -> None:
    from quant_os.proving.profit_candidate_artifacts import (
        regenerate_profit_candidate_artifacts,
    )

    payload = regenerate_profit_candidate_artifacts(output_root=local_project)

    assert payload["status"] == "PROFIT_CANDIDATE_ARTIFACTS_REGENERATED"
    assert payload["strategy"] == "tracked_sanitized_fixture_regeneration"
    assert payload["proof_row_count"] == 100
    assert payload["raw_ignored_captures_required"] is False
    assert payload["public_network_required"] is False
    assert payload["artifact_statuses"]["dataset"] == "WEATHER_PROOF_ROWS_BUILT"
    assert payload["artifact_statuses"]["paper"] == "PAPER_PROFIT_CANDIDATE"
    assert payload["artifact_statuses"]["profit_campaign"] == "PAPER_PROFIT_CANDIDATE_FOUND"
    for relative_path in payload["generated_artifacts"]:
        assert (local_project / relative_path).exists()
    assert payload["live_trading_enabled"] is False
    assert payload["order_transmission_enabled"] is False
    assert payload["authenticated_requests_enabled"] is False


def test_sequence56_sanitized_fixture_contains_no_auth_keys_cookies_or_order_endpoints() -> None:
    text = "\n".join(path.read_text(encoding="utf-8") for path in FIXTURE_DIR.iterdir())
    forbidden = [
        "KALSHI-ACCESS-KEY",
        "KALSHI-ACCESS-SIGNATURE",
        "KALSHI-ACCESS-TIMESTAMP",
        "private_key",
        "load_private_key",
        "create_signature",
        "sign_request",
        "requests.post",
        "/portfolio/orders",
        "DELETE /portfolio/orders",
        "cookie=",
    ]

    assert not any(item in text for item in forbidden)


def test_sequence56_repair_report_is_deterministic_and_records_stable_hashes(
    local_project: Path,
) -> None:
    from quant_os.readiness.first_dollar_provenance_repair import (
        write_first_dollar_provenance_repair_report,
    )

    first = write_first_dollar_provenance_repair_report(output_root=local_project)
    second = write_first_dollar_provenance_repair_report(output_root=local_project)

    assert first["status"] == "PROVENANCE_REPAIR_PASSED"
    assert second["status"] == "PROVENANCE_REPAIR_PASSED"
    assert first["artifact_hashes"] == second["artifact_hashes"]
    assert first["raw_ignored_captures_required"] is False
    assert first["public_network_required"] is False
    assert first["fresh_worktree_can_reproduce"] is True


def test_sequence56_repaired_path_reproduces_paper_candidate_and_tiny_canary(
    local_project: Path,
) -> None:
    from quant_os.proving.profit_candidate_artifacts import (
        regenerate_profit_candidate_artifacts,
    )

    regenerate_profit_candidate_artifacts(output_root=local_project)
    payload = _run_canary_chain(local_project)

    assert payload["status"] == "TINY_CANARY_READY_FOR_MANUAL_ARMING"
    assert payload["live_trading_enabled"] is False
    assert payload["execution_authority"] == "NONE"
    assert payload["order_transmission_enabled"] is False
    assert payload["authenticated_requests_enabled"] is False
    assert payload["api_keys_loaded"] is False
    assert payload["private_keys_loaded"] is False
    assert payload["actual_order_count"] == 0
    assert payload["actual_cancel_count"] == 0


def test_sequence56_security_scan_blocks_executable_auth_or_order_path(
    local_project: Path,
) -> None:
    from quant_os.readiness.first_dollar_security_scan import evaluate_security_scan

    unsafe = local_project / "unsafe_order_path.py"
    unsafe.write_text(
        "import requests\n"
        "def send_order():\n"
        "    return requests.post('/portfolio/orders', json={})\n",
        encoding="utf-8",
    )

    payload = evaluate_security_scan(paths=[unsafe], output_root=local_project)

    assert payload["status"] == "FIRST_DOLLAR_SECURITY_SCAN_BLOCKED"
    assert "EXECUTABLE_ORDER_OR_AUTH_PATH" in payload["blockers"]


def test_sequence56_first_dollar_preflight_is_structurally_ready_without_current_market(
    local_project: Path,
) -> None:
    from quant_os.proving.profit_candidate_artifacts import (
        regenerate_profit_candidate_artifacts,
    )
    from quant_os.readiness.current_market_eligibility import (
        write_current_market_eligibility_report,
    )
    from quant_os.readiness.first_dollar_human_review import (
        write_first_dollar_human_review_report,
    )
    from quant_os.readiness.first_dollar_order_preview import (
        write_first_dollar_order_preview_report,
    )
    from quant_os.readiness.first_dollar_preflight import write_first_dollar_preflight_report
    from quant_os.readiness.first_dollar_provenance_audit import (
        write_first_dollar_provenance_audit_report,
    )
    from quant_os.readiness.first_dollar_provenance_repair import (
        write_first_dollar_provenance_repair_report,
    )
    from quant_os.readiness.first_dollar_security_scan import (
        write_first_dollar_security_scan_report,
    )

    regenerate_profit_candidate_artifacts(output_root=local_project)
    _run_canary_chain(local_project)
    write_first_dollar_provenance_audit_report(output_root=local_project)
    write_first_dollar_provenance_repair_report(output_root=local_project)
    write_first_dollar_security_scan_report(output_root=local_project)
    write_current_market_eligibility_report(output_root=local_project)
    write_first_dollar_order_preview_report(output_root=local_project)
    write_first_dollar_human_review_report(output_root=local_project)
    payload = write_first_dollar_preflight_report(output_root=local_project)

    assert payload["status"] == "FIRST_DOLLAR_PREFLIGHT_STRUCTURALLY_READY_NO_CURRENT_MARKET"
    assert payload["tiny_canary_readiness_status"] == "TINY_CANARY_READY_FOR_MANUAL_ARMING"
    assert payload["live_trading_enabled"] is False
    assert payload["execution_authority"] == "NONE"
    assert payload["order_transmission_enabled"] is False
    assert payload["authenticated_requests_enabled"] is False
    assert payload["api_keys_loaded"] is False
    assert payload["private_keys_loaded"] is False
    assert payload["actual_order_count"] == 0
    assert payload["actual_cancel_count"] == 0


def test_sequence56_cli_and_make_targets_are_fixture_safe(local_project: Path) -> None:
    commands = [
        [sys.executable, "-m", "quant_os.cli", "proving", "regenerate-profit-candidate-artifacts"],
        [sys.executable, "-m", "quant_os.cli", "readiness", "first-dollar-provenance-audit"],
        [sys.executable, "-m", "quant_os.cli", "readiness", "first-dollar-provenance-repair"],
        [sys.executable, "-m", "quant_os.cli", "readiness", "first-dollar-security-scan"],
        [sys.executable, "-m", "quant_os.cli", "readiness", "current-market-eligibility"],
        [sys.executable, "-m", "quant_os.cli", "readiness", "first-dollar-order-preview"],
        [sys.executable, "-m", "quant_os.cli", "readiness", "first-dollar-human-review"],
        [sys.executable, "-m", "quant_os.cli", "readiness", "first-dollar-preflight"],
    ]
    for command in commands:
        result = subprocess.run(
            command,
            cwd=local_project,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert "live_trading_enabled" in result.stdout

    make_cmd = (Path(__file__).resolve().parents[1] / "make.cmd").read_text(encoding="utf-8")
    assert 'if "%TARGET%"=="profit-candidate-artifacts-smoke"' in make_cmd
    assert 'if "%TARGET%"=="first-dollar-preflight-smoke"' in make_cmd
    assert 'if "%TARGET%"=="sequence56-smoke"' in make_cmd
