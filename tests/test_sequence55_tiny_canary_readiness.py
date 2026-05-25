from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index in range(36):
        in_bucket = index % 6 == 0
        rows.append(
            {
                "candidate_id": "pm_weather_forecast_market_mismatch",
                "event_id": f"KXHIGHNY-26APR{29 + index // 12:02d}",
                "market_id": f"KXHIGHNY-26APR{29 + index // 12:02d}-B{60 + index}",
                "location": "Central Park, New York",
                "variable": "temperature_max_f",
                "bucket_range": f"{60 + index}_to_{61 + index}_f_inclusive",
                "forecast_source": "iem_mos_historical_forecast",
                "forecast_ts": "2026-04-28T12:00:00Z",
                "known_at_ts": "2026-04-28T12:00:00Z",
                "orderbook_ts": "2026-04-29T12:00:00Z",
                "resolution_ts": "2026-04-30T14:00:00Z",
                "forecast_value": 62.0,
                "resolution_value": 62.0,
                "forecast_probability": 0.82 if in_bucket else 0.20,
                "market_price": 0.10,
                "market_mid": 0.10,
                "spread": 0.01,
                "liquidity": 500.0,
                "resolution_label": "IN_BUCKET" if in_bucket else "OUT_OF_BUCKET",
                "proof_eligible": True,
                "fixture_only": False,
                "synthetic": False,
                "source_quality": "PUBLIC_READ_ONLY_ALLOWED",
                "source_ids": [
                    "kalshi_public_market_data",
                    "iem_mos_historical_forecast",
                    "nws_climatological_report",
                ],
                "provenance_hash": f"sha256:{index:064x}",
                "data_quality_flags": [],
            }
        )
    return rows


def _paper_report(**overrides: object) -> dict[str, object]:
    report: dict[str, object] = {
        "schema_version": "weather_market_batch_paper_proving_v1",
        "candidate_id": "pm_weather_forecast_market_mismatch",
        "lane_id": "pm_weather_forecast_market_mismatch",
        "readiness_status": "PAPER_PROFIT_CANDIDATE",
        "dataset_status": "WEATHER_MARKET_DATASET_READY",
        "source_quality_tier": "PUBLIC_REPLAY",
        "proof_row_count": 36,
        "row_count": 36,
        "trade_count": 36,
        "minimum_sample_size": 30,
        "labels_valid": True,
        "no_lookahead": True,
        "costs_included": True,
        "cost_model": {
            "fee_bps": 8.0,
            "spread_bps": 10.0,
            "slippage_bps": 15.0,
            "adverse_selection_bps": 20.0,
        },
        "fill_assumptions_included": True,
        "fill_model": {
            "max_spread": 0.12,
            "partial_fill_liquidity": 200.0,
            "partial_fill_fraction": 0.25,
            "target_size": 10.0,
        },
        "baseline_comparison": {"included": True, "paper_beats_comparison": True},
        "placebo_comparison": {"included": True, "paper_beats_comparison": True},
        "one_row_dominance": {"detected": False, "dominance_ratio": "0.12"},
        "oos_walk_forward_status": "OOS_WALK_FORWARD_AVAILABLE",
        "gross_simulated_pnl": "10.0",
        "net_simulated_pnl_after_costs": "9.0",
        "fill_adjusted_pnl": "8.0",
        "max_drawdown": "1.0",
        "paper_intents": [
            {
                "event_id": row["event_id"],
                "market_id": row["market_id"],
                "intent": "BUY_YES" if row["resolution_label"] == "IN_BUCKET" else "NO_TRADE",
                "edge_after_costs": "0.2",
                "net_paper_pnl": "1.0" if row["resolution_label"] == "IN_BUCKET" else "0",
                "fill_fraction": "0.25",
            }
            for row in _rows()
        ],
        "simulated_trades": [],
        "synthetic_rows_counted_as_profit_evidence": False,
        "requires_private_or_authenticated_data": False,
        "copy_trading_enabled": False,
        "wallet_signing_enabled": False,
        "requires_leverage": False,
        "requires_futures_or_margin": False,
        "requires_options": False,
        "live_trading_enabled": False,
        "execution_authority": "NONE",
        "reproducible_commands": [
            "python -m quant_os.cli proving weather-batch-paper-proving"
        ],
        "blockers": [],
    }
    report.update(overrides)
    return report


def _dataset_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "candidate_id": "pm_weather_forecast_market_mismatch",
        "dataset_status": "WEATHER_PROOF_ROWS_BUILT",
        "row_count": 36,
        "proof_row_count": 36,
        "real_public_row_count": 36,
        "fixture_row_count": 0,
        "no_lookahead": True,
        "rows": _rows(),
        "blockers": [],
        "live_trading_enabled": False,
        "execution_authority": "NONE",
    }
    payload.update(overrides)
    return payload


def _profit_campaign_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "campaign_status": "PAPER_PROFIT_CANDIDATE_FOUND",
        "paper_profit_status": "PAPER_PROFIT_CANDIDATE_FOUND",
        "best_candidate_so_far": {
            "lane_id": "pm_weather_forecast_market_mismatch",
            "status": "PAPER_PROFIT_CANDIDATE",
            "profit_claim_status": "PAPER_PROFIT_CANDIDATE",
        },
        "attempts": [
            {
                "lane_id": "pm_weather_forecast_market_mismatch",
                "status": "PAPER_PROFIT_CANDIDATE_FOUND",
                "paper_status": "PAPER_PROFIT_CANDIDATE",
                "proof_rows_created": 36,
                "capture_status": "WEATHER_HISTORICAL_FORECASTS_CAPTURED",
                "report_paths": {
                    "json": "reports/sequence52/weather_batch_readiness/latest_weather_batch_readiness.json",
                    "markdown": "reports/sequence52/weather_batch_readiness/latest_weather_batch_readiness.md",
                },
            }
        ],
        "live_trading_enabled": False,
        "execution_authority": "NONE",
    }
    payload.update(overrides)
    return payload


def _all_gate_payloads() -> dict[str, dict[str, object]]:
    return {
        "paper_candidate_audit": {"status": "PAPER_CANDIDATE_AUDIT_PASSED"},
        "lineage_audit": {"status": "LINEAGE_AUDIT_PASSED"},
        "replay_recompute": {"status": "REPLAY_RECOMPUTE_MATCHED"},
        "robustness": {"status": "ROBUSTNESS_PASSED"},
        "cost_fill_stress": {"status": "COST_FILL_STRESS_PASSED"},
        "shadow_rehearsal": {"status": "BOUNDED_SHADOW_REHEARSAL_PASSED"},
        "dry_run_parity": {"status": "DRY_RUN_PARITY_PASSED"},
        "risk": {"status": "TINY_CANARY_RISK_PASSED"},
        "kill_switch": {"status": "KILL_SWITCH_PROOF_PASSED"},
        "reconciliation": {"status": "RECONCILIATION_PROOF_PASSED"},
        "manual_packet": {"status": "MANUAL_CANARY_PACKET_READY"},
    }


def test_sequence55_paper_profit_candidate_must_exist_before_gates(local_project: Path) -> None:
    from quant_os.readiness.paper_candidate_audit import evaluate_paper_candidate_audit

    payload = evaluate_paper_candidate_audit(
        output_root=local_project,
        profit_campaign_payload={"campaign_status": "CAMPAIGN_CHECKPOINTED_NOT_COMPLETE"},
        dataset_payload=_dataset_payload(),
        paper_payload=_paper_report(),
    )

    assert payload["status"] == "PAPER_CANDIDATE_NOT_REPRODUCIBLE"
    assert "PAPER_PROFIT_CANDIDATE_FOUND_MISSING" in payload["blockers"]


def test_sequence55_paper_candidate_audit_fails_if_reports_missing(local_project: Path) -> None:
    from quant_os.readiness.paper_candidate_audit import write_paper_candidate_audit_report

    payload = write_paper_candidate_audit_report(output_root=local_project)

    assert payload["status"] == "PAPER_CANDIDATE_NOT_REPRODUCIBLE"
    assert "MISSING_PROFIT_CAMPAIGN_REPORT" in payload["blockers"]


def test_sequence55_paper_candidate_audit_passes_candidate(local_project: Path) -> None:
    from quant_os.readiness.paper_candidate_audit import evaluate_paper_candidate_audit

    payload = evaluate_paper_candidate_audit(
        output_root=local_project,
        profit_campaign_payload=_profit_campaign_payload(),
        dataset_payload=_dataset_payload(),
        paper_payload=_paper_report(),
    )

    assert payload["status"] == "PAPER_CANDIDATE_AUDIT_PASSED"
    assert payload["candidate_id"] == "pm_weather_forecast_market_mismatch"
    assert payload["proof_row_count"] == 36
    assert payload["live_trading_enabled"] is False
    assert payload["execution_authority"] == "NONE"


def test_sequence55_lineage_audit_blocks_lookahead(local_project: Path) -> None:
    from quant_os.readiness.weather_candidate_lineage_audit import (
        evaluate_weather_candidate_lineage_audit,
    )

    rows = _rows()
    rows[0]["known_at_ts"] = "2026-05-01T00:00:00Z"
    payload = evaluate_weather_candidate_lineage_audit(rows=rows, output_root=local_project)

    assert payload["status"] == "TIMESTAMP_ALIGNMENT_FAILED"
    assert "TIMESTAMP_ORDER_INVALID" in payload["blockers"]


def test_sequence55_lineage_audit_blocks_realized_weather_as_forecast(local_project: Path) -> None:
    from quant_os.readiness.weather_candidate_lineage_audit import (
        evaluate_weather_candidate_lineage_audit,
    )

    rows = _rows()
    rows[0]["forecast_source"] = "realized_weather_resolution"
    rows[0]["uses_resolution_as_forecast"] = True
    payload = evaluate_weather_candidate_lineage_audit(rows=rows, output_root=local_project)

    assert payload["status"] == "LOOKAHEAD_RISK_BLOCKED"
    assert "REALIZED_WEATHER_USED_AS_FORECAST" in payload["blockers"]


def test_sequence55_replay_recompute_detects_mismatch(local_project: Path) -> None:
    from quant_os.proving.weather_candidate_replay_recompute import evaluate_replay_recompute

    payload = evaluate_replay_recompute(
        rows=_rows(),
        expected_paper_payload=_paper_report(net_simulated_pnl_after_costs="999"),
        output_root=local_project,
    )

    assert payload["status"] == "REPLAY_RECOMPUTE_MISMATCH"
    assert "NET_PNL_MISMATCH" in payload["blockers"]


def test_sequence55_robustness_blocks_one_row_dominance(local_project: Path) -> None:
    from quant_os.proving.weather_candidate_robustness import evaluate_weather_candidate_robustness

    payload = evaluate_weather_candidate_robustness(
        paper_payload=_paper_report(one_row_dominance={"detected": True}),
        output_root=local_project,
    )

    assert payload["status"] == "ONE_ROW_DOMINANCE_BLOCKED"


def test_sequence55_robustness_blocks_failed_placebos(local_project: Path) -> None:
    from quant_os.proving.weather_candidate_robustness import evaluate_weather_candidate_robustness

    payload = evaluate_weather_candidate_robustness(
        paper_payload=_paper_report(
            placebo_comparison={"included": True, "paper_beats_comparison": False}
        ),
        output_root=local_project,
    )

    assert payload["status"] == "OVERFIT_RISK_BLOCKED"
    assert "PLACEBO_FAILED" in payload["blockers"]


def test_sequence55_cost_fill_blocks_edge_erased_by_worse_fills(local_project: Path) -> None:
    from quant_os.proving.weather_candidate_cost_fill_stress import evaluate_cost_fill_stress

    payload = evaluate_cost_fill_stress(
        paper_payload=_paper_report(net_simulated_pnl_after_costs="0.01", trade_count=20),
        output_root=local_project,
    )

    assert payload["status"] == "COSTS_ERASE_EDGE"
    assert "WORSE_ENTRY_5C_ERASES_EDGE" in payload["blockers"]


def test_sequence55_bounded_shadow_rehearsal_emits_only_offline_intents(local_project: Path) -> None:
    from quant_os.proving.weather_bounded_shadow_rehearsal import run_bounded_shadow_rehearsal

    payload = run_bounded_shadow_rehearsal(
        rows=_rows(),
        paper_payload=_paper_report(),
        output_root=local_project,
    )

    assert payload["status"] == "BOUNDED_SHADOW_REHEARSAL_PASSED"
    assert payload["order_transmission_enabled"] is False
    assert payload["actual_order_count"] == 0
    assert all(event["offline_only"] is True for event in payload["event_ledger"])


def test_sequence55_dry_run_parity_cannot_send_orders(local_project: Path) -> None:
    from quant_os.execution.weather_dry_run_parity import evaluate_dry_run_parity

    payload = evaluate_dry_run_parity(
        rows=_rows(),
        paper_payload=_paper_report(),
        transmit_requested=True,
        output_root=local_project,
    )

    assert payload["status"] == "UNSAFE_ORDER_INTENT_BLOCKED"
    assert payload["order_transmission_enabled"] is False
    assert payload["actual_order_count"] == 0


def test_sequence55_dry_run_parity_blocks_missing_evidence_hash(local_project: Path) -> None:
    from quant_os.execution.weather_dry_run_parity import evaluate_dry_run_parity

    rows = _rows()
    rows[0]["provenance_hash"] = ""
    payload = evaluate_dry_run_parity(
        rows=rows,
        paper_payload=_paper_report(),
        output_root=local_project,
    )

    assert payload["status"] == "UNSAFE_ORDER_INTENT_BLOCKED"
    assert "MISSING_EVIDENCE_HASH" in payload["blockers"]


def test_sequence55_risk_envelope_caps_to_one_tiny_order(local_project: Path) -> None:
    from quant_os.risk.weather_tiny_canary_risk import evaluate_tiny_canary_risk

    payload = evaluate_tiny_canary_risk(output_root=local_project)

    assert payload["status"] == "TINY_CANARY_RISK_PASSED"
    assert payload["risk_envelope"]["max_canary_orders"] == 1
    assert payload["risk_envelope"]["max_contracts"] == 1
    assert payload["manual_arming_required"] is True


def test_sequence55_risk_envelope_blocks_venue_minimum_above_cap(local_project: Path) -> None:
    from quant_os.risk.weather_tiny_canary_risk import evaluate_tiny_canary_risk

    payload = evaluate_tiny_canary_risk(venue_minimum_exposure_usd=2.0, output_root=local_project)

    assert payload["status"] == "VENUE_MINIMUM_EXCEEDS_LIMIT"


def test_sequence55_kill_switch_disables_on_stale_data(local_project: Path) -> None:
    from quant_os.risk.weather_canary_kill_switch import evaluate_kill_switch

    payload = evaluate_kill_switch(stale_data=True, output_root=local_project)

    assert payload["status"] == "KILL_SWITCH_PROOF_PASSED"
    assert payload["disable_matrix"]["stale_data"]["disables"] is True


def test_sequence55_kill_switch_disables_on_wide_spread(local_project: Path) -> None:
    from quant_os.risk.weather_canary_kill_switch import evaluate_kill_switch

    payload = evaluate_kill_switch(spread=0.25, output_root=local_project)

    assert payload["disable_matrix"]["spread_too_wide"]["disables"] is True


def test_sequence55_kill_switch_disables_on_missing_reconciliation(local_project: Path) -> None:
    from quant_os.risk.weather_canary_kill_switch import evaluate_kill_switch

    payload = evaluate_kill_switch(reconciliation_present=False, output_root=local_project)

    assert payload["disable_matrix"]["reconciliation_missing"]["disables"] is True


def test_sequence55_ledger_proof_enforces_idempotency(local_project: Path) -> None:
    from quant_os.execution.weather_canary_reconciliation import evaluate_reconciliation_proof

    payload = evaluate_reconciliation_proof(
        evidence_hash="sha256:abc",
        duplicate_idempotency_key=True,
        output_root=local_project,
    )

    assert payload["status"] == "RECONCILIATION_PROOF_FAILED"
    assert "DUPLICATE_IDEMPOTENCY_KEY" in payload["blockers"]


def test_sequence55_manual_packet_contains_no_signing_or_order_transmission_code(
    local_project: Path,
) -> None:
    from quant_os.readiness.weather_manual_canary_packet import build_manual_canary_packet

    payload = build_manual_canary_packet(
        gate_payloads=_all_gate_payloads(),
        output_root=local_project,
    )

    text = json.dumps(payload)
    assert payload["status"] == "MANUAL_CANARY_PACKET_READY"
    assert "This packet does not place or authorize an order." in text
    assert "POST /portfolio/orders" not in text
    assert "DELETE /portfolio/orders" not in text
    assert "private key" not in text.lower()


def test_sequence55_final_readiness_requires_all_gates(local_project: Path) -> None:
    from quant_os.readiness.tiny_canary_readiness import evaluate_tiny_canary_readiness

    gates = _all_gate_payloads()
    gates["robustness"] = {"status": "ROBUSTNESS_FAILED"}
    payload = evaluate_tiny_canary_readiness(gate_payloads=gates, output_root=local_project)

    assert payload["status"] == "TINY_CANARY_BLOCKED_BY_ROBUSTNESS"


def test_sequence55_final_readiness_keeps_live_disabled_and_execution_none(
    local_project: Path,
) -> None:
    from quant_os.readiness.tiny_canary_readiness import evaluate_tiny_canary_readiness

    payload = evaluate_tiny_canary_readiness(
        gate_payloads=_all_gate_payloads(),
        output_root=local_project,
    )

    assert payload["status"] == "TINY_CANARY_READY_FOR_MANUAL_ARMING"
    assert payload["live_trading_enabled"] is False
    assert payload["execution_authority"] == "NONE"
    assert payload["order_transmission_enabled"] is False


def test_sequence55_final_readiness_blocks_api_and_private_key_loading(
    local_project: Path,
) -> None:
    from quant_os.readiness.tiny_canary_readiness import evaluate_tiny_canary_readiness

    payload = evaluate_tiny_canary_readiness(
        gate_payloads=_all_gate_payloads(),
        api_keys_loaded=True,
        private_keys_loaded=True,
        output_root=local_project,
    )

    assert payload["status"] == "NEEDS_HUMAN_APPROVAL_FOR_FIRST_DOLLAR_TRADE"
    assert payload["api_keys_loaded"] is False
    assert payload["private_keys_loaded"] is False


def test_sequence55_final_readiness_records_zero_orders_and_cancels(local_project: Path) -> None:
    from quant_os.readiness.tiny_canary_readiness import evaluate_tiny_canary_readiness

    payload = evaluate_tiny_canary_readiness(
        gate_payloads=_all_gate_payloads(),
        output_root=local_project,
    )

    assert payload["actual_order_count"] == 0
    assert payload["actual_cancel_count"] == 0


def test_sequence55_no_forbidden_auth_signing_order_cancel_wallet_copytrade_or_evasion_path() -> None:
    paths = [
        Path("src/quant_os/readiness/paper_candidate_audit.py"),
        Path("src/quant_os/readiness/weather_candidate_lineage_audit.py"),
        Path("src/quant_os/proving/weather_candidate_replay_recompute.py"),
        Path("src/quant_os/proving/weather_candidate_robustness.py"),
        Path("src/quant_os/proving/weather_candidate_cost_fill_stress.py"),
        Path("src/quant_os/proving/weather_bounded_shadow_rehearsal.py"),
        Path("src/quant_os/execution/weather_dry_run_order_intents.py"),
        Path("src/quant_os/execution/weather_dry_run_parity.py"),
        Path("src/quant_os/risk/weather_tiny_canary_risk.py"),
        Path("src/quant_os/risk/weather_canary_kill_switch.py"),
        Path("src/quant_os/execution/weather_canary_ledger.py"),
        Path("src/quant_os/execution/weather_canary_reconciliation.py"),
        Path("src/quant_os/readiness/weather_manual_canary_packet.py"),
        Path("src/quant_os/readiness/tiny_canary_readiness.py"),
    ]
    forbidden = [
        "POST /portfolio/orders",
        "DELETE /portfolio/orders",
        "requests.post",
        "requests.delete",
        "sign(",
        "wallet",
        "copy_trade",
        "captcha",
        "proxy",
    ]
    joined = "\n".join(path.read_text(encoding="utf-8") for path in paths if path.exists())

    assert not any(item in joined for item in forbidden)


def test_sequence55_cli_and_make_targets_are_fixture_safe(local_project: Path) -> None:
    commands = [
        [sys.executable, "-m", "quant_os.cli", "readiness", "paper-candidate-audit"],
        [sys.executable, "-m", "quant_os.cli", "readiness", "weather-lineage-audit"],
        [sys.executable, "-m", "quant_os.cli", "proving", "weather-replay-recompute"],
        [sys.executable, "-m", "quant_os.cli", "proving", "weather-robustness"],
        [sys.executable, "-m", "quant_os.cli", "proving", "weather-cost-fill-stress"],
        [sys.executable, "-m", "quant_os.cli", "proving", "weather-bounded-shadow-rehearsal"],
        [sys.executable, "-m", "quant_os.cli", "execution", "weather-dry-run-parity"],
        [sys.executable, "-m", "quant_os.cli", "risk", "weather-tiny-canary-risk"],
        [sys.executable, "-m", "quant_os.cli", "risk", "weather-canary-kill-switch"],
        [sys.executable, "-m", "quant_os.cli", "execution", "weather-canary-reconciliation"],
        [sys.executable, "-m", "quant_os.cli", "readiness", "weather-manual-canary-packet"],
        [sys.executable, "-m", "quant_os.cli", "readiness", "tiny-canary-readiness"],
    ]
    for command in commands:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        assert result.returncode == 0, result.stderr
        assert "live_trading_enabled" in result.stdout

    make_cmd = (Path(__file__).resolve().parents[1] / "make.cmd").read_text(encoding="utf-8")
    assert 'if "%TARGET%"=="canary-readiness-smoke"' in make_cmd
    assert 'if "%TARGET%"=="sequence55-smoke"' in make_cmd
