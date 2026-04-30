from __future__ import annotations

from quant_os.canary.permissions import evaluate_permission_manifest


def test_forbidden_permissions_block_readiness(local_project):
    payload = evaluate_permission_manifest({"scopes": ["read", "withdrawals", "margin"]})
    assert payload["status"] == "FAIL"
    assert "FORBIDDEN_PERMISSION_SCOPES_PRESENT" in payload["blockers"]


def test_credentials_in_permission_manifest_block(local_project):
    payload = evaluate_permission_manifest({"scopes": ["read"], "api_key": "not-allowed"})
    assert payload["status"] == "FAIL"
    assert "CREDENTIAL_FIELDS_PRESENT_IN_PERMISSION_MANIFEST" in payload["blockers"]
