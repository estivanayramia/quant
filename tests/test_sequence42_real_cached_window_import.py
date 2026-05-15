from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "replay_candidates" / "pm_crypto_updown"
REAL_CACHED_SAMPLE_ROOT = FIXTURE_ROOT / "real_cached_sample"


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _artifact(payload: dict[str, Any]) -> dict[str, Any]:
    item = {
        "capture_mode": "official_api_read_only",
        "source_note": "sequence42 fixture-safe public read-only artifact",
        "provenance": {
            "fixture": "sequence42_real_cached_window_import",
            "network_auth_used": False,
            "wallet_used": False,
            "order_endpoint_used": False,
            "live_trading_enabled": False,
            "execution_authority": "NONE",
        },
        "quality_flags": [
            "PHASE42_FIXTURE_SAFE_REAL_CACHED_IMPORT",
            "READ_ONLY_PUBLIC_DATA_SHAPE",
        ],
        **payload,
    }
    item["raw_hash"] = _hash({"raw": payload})
    item["normalized_hash"] = _hash({"normalized": item})
    return item


def _write_phase42_root(root: Path) -> Path:
    root.mkdir()
    artifacts = []
    base = datetime(2026, 5, 14, 12, 20, tzinfo=UTC)
    for index in range(5):
        start = base + timedelta(minutes=5 * index)
        event = start + timedelta(seconds=60)
        prior = event - timedelta(seconds=5)
        end = start + timedelta(minutes=5)
        slot = f"{index + 1:02d}"
        market_id = f"phase42_real_cached_market_{slot}"
        condition_id = f"phase42_condition_{slot}"
        slug = f"phase42-btc-updown-5m-{slot}"
        token_up = f"phase42_token_up_{slot}"
        token_down = f"phase42_token_down_{slot}"
        prior_price = 100000.0 + index
        event_price = prior_price * (1.0002 if index % 2 == 0 else 0.9998)
        resolved = "UP" if event_price >= prior_price else "DOWN"

        artifacts.append(
            _artifact(
                {
                    "artifact_type": "pm_market_window",
                    "source_id": f"phase42_market_{slot}",
                    "captured_at": _iso(event),
                    "event_ts": _iso(start),
                    "market_id": market_id,
                    "condition_id": condition_id,
                    "slug": slug,
                    "spot_symbol": "BTC-USD",
                    "window_start_ts": _iso(start),
                    "window_end_ts": _iso(end),
                    "tokens": [
                        {"token_id": token_up, "outcome": "UP"},
                        {"token_id": token_down, "outcome": "DOWN"},
                    ],
                }
            )
        )
        artifacts.append(
            _artifact(
                {
                    "artifact_type": "spot_snapshot",
                    "source_id": f"phase42_spot_prior_{slot}",
                    "captured_at": _iso(prior),
                    "event_ts": _iso(prior),
                    "spot_symbol": "BTC-USD",
                    "price": prior_price,
                }
            )
        )
        artifacts.append(
            _artifact(
                {
                    "artifact_type": "spot_snapshot",
                    "source_id": f"phase42_spot_event_{slot}",
                    "captured_at": _iso(event),
                    "event_ts": _iso(event),
                    "spot_symbol": "BTC-USD",
                    "price": event_price,
                }
            )
        )
        for outcome, token_id, bid, ask, last in (
            ("UP", token_up, 0.51, 0.53, 0.52),
            ("DOWN", token_down, 0.47, 0.49, 0.48),
        ):
            artifacts.append(
                _artifact(
                    {
                        "artifact_type": "pm_clob_snapshot",
                        "source_id": f"phase42_clob_{slot}_{outcome.lower()}",
                        "captured_at": _iso(event),
                        "event_ts": _iso(event),
                        "market_id": market_id,
                        "condition_id": condition_id,
                        "slug": slug,
                        "token_id": token_id,
                        "outcome": outcome,
                        "clob_snapshot_id": f"phase42_clob_{slot}_{outcome.lower()}_01",
                        "bid": bid,
                        "ask": ask,
                        "last_trade_price": last,
                        "volume": 1800.0 + index,
                        "liquidity": 950.0 + index,
                    }
                )
            )
        artifacts.append(
            _artifact(
                {
                    "artifact_type": "pm_window_label",
                    "source_id": f"phase42_label_{slot}",
                    "captured_at": _iso(end),
                    "event_ts": _iso(end),
                    "market_id": market_id,
                    "condition_id": condition_id,
                    "slug": slug,
                    "label_status": "RESOLVED",
                    "resolved_outcome": resolved,
                    "resolution_source_id": f"phase42_resolution_{slot}",
                }
            )
        )

    root.joinpath("artifacts.jsonl").write_text(
        "".join(json.dumps(item, sort_keys=True) + "\n" for item in artifacts),
        encoding="utf-8",
    )
    return root


def test_sequence42_importing_five_additional_windows_reaches_real_cached_gate(
    local_project: Path,
    tmp_path: Path,
) -> None:
    from quant_os.readiness.expanded_shadow_replay_readiness_report import (
        write_sequence41_expanded_shadow_replay_readiness_report,
    )
    from quant_os.research.replay_candidates.pm_crypto_updown_real_cached_import import (
        build_pm_crypto_updown_real_cached_source,
    )
    from quant_os.research.replay_candidates.pm_crypto_updown_real_cached_replay_eval import (
        write_pm_crypto_updown_sequence41_replay_eval_report,
    )
    from quant_os.research.replay_candidates.pm_crypto_updown_threshold_progress import (
        write_pm_crypto_updown_sequence41_threshold_progress_report,
    )

    phase42_root = _write_phase42_root(tmp_path / "phase42_real_cached")
    source = build_pm_crypto_updown_real_cached_source(import_root=phase42_root)
    roots = [REAL_CACHED_SAMPLE_ROOT, phase42_root]

    progress = write_pm_crypto_updown_sequence41_threshold_progress_report(
        fixture_root=FIXTURE_ROOT,
        real_cached_artifact_roots=roots,
        output_root=local_project,
    )
    evaluation = write_pm_crypto_updown_sequence41_replay_eval_report(
        fixture_root=FIXTURE_ROOT,
        real_cached_artifact_roots=roots,
        output_root=local_project,
    )
    readiness = write_sequence41_expanded_shadow_replay_readiness_report(
        real_cached_replay_eval=evaluation,
        output_root=local_project,
    )

    assert source["real_cached_replay_ready_row_count"] == 10
    assert progress["current_primary_row_count"] == 20
    assert progress["current_real_cached_row_count"] == 14
    assert progress["row_gap"] == 0
    assert progress["source_coverage"]["coverage_status"] == "REAL_CACHED_SOURCE_COVERAGE_SUFFICIENT"
    assert progress["rows_added_by_source_quality"] == {"real_cached": 10}
    assert evaluation["primary_evidence_row_count"] == 20
    assert evaluation["real_cached_replay_ready_row_count"] == 14
    assert readiness["primary_evidence_row_count"] == 20
    assert readiness["real_cached_replay_ready_row_count"] == 14
    assert readiness["readiness_status"] in {
        "READY_FOR_EXPANDED_SHADOW_REPLAY",
        "BASELINE_OR_PLACEBO_BLOCKED",
        "COST_FILL_BLOCKED",
    }
    assert all("PRIMARY_ROWS_" not in blocker for blocker in readiness["blockers"])
    assert "REAL_CACHED_COVERAGE_TOO_LOW" not in readiness["blockers"]


def test_sequence42_smoke_target_is_registered() -> None:
    make_cmd = Path("make.cmd").read_text(encoding="utf-8")
    assert 'if "%TARGET%"=="sequence42-smoke"' in make_cmd
    assert "tests/test_sequence42_real_cached_window_import.py" in make_cmd
