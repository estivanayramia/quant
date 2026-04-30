from __future__ import annotations

from pathlib import Path

import yaml

from quant_os.security.live_canary_guard import live_canary_guard


def test_live_canary_guard_blocks_enabled_live_flags(local_project):
    Path("configs/live_canary.yaml").write_text(
        yaml.safe_dump(
            {
                "enabled": True,
                "live_trading_allowed": True,
                "dry_run_required": True,
                "human_approval_required": True,
                "exchange_keys_allowed": False,
                "withdrawal_permissions_allowed": False,
            }
        ),
        encoding="utf-8",
    )
    result = live_canary_guard()
    assert not result.passed
    assert "CANARY_ENABLED_TRUE" in result.reasons
    assert "CANARY_LIVE_TRADING_ALLOWED_TRUE" in result.reasons
