from __future__ import annotations

from pathlib import Path

from quant_os.canary.permissions_import import import_permission_manifest


def test_permission_manifest_import_report_generated(local_project, tmp_path: Path):
    path = tmp_path / "permission_manifest.yaml"
    path.write_text(
        "\n".join(
            [
                "exchange_name: rehearsal",
                "scope_list:",
                "  - trade_spot_only",
                "  - read_balances_optional",
                "withdrawal_enabled: false",
            ]
        ),
        encoding="utf-8",
    )
    payload = import_permission_manifest(path)
    assert payload["status"] == "PASS"
    assert "trade_spot_only" in payload["normalized_scope_list"]
    assert Path("reports/canary/latest_permission_manifest.json").exists()


def test_forbidden_scope_blocks_manifest_validation(local_project, tmp_path: Path):
    path = tmp_path / "permission_manifest.yaml"
    path.write_text(
        "exchange_name: rehearsal\nscope_list:\n  - withdraw\nwithdrawal_enabled: true\n",
        encoding="utf-8",
    )
    payload = import_permission_manifest(path)
    assert payload["status"] == "FAIL"
    assert "FORBIDDEN_PERMISSION_SCOPES_PRESENT" in payload["blockers"]
    assert "WITHDRAWAL_ENABLED_TRUE" in payload["blockers"]
