from __future__ import annotations

import yaml

from quant_os.live_canary.credential_loader import load_live_credentials


def test_prepare_blocks_without_credential_file(local_project):
    payload = load_live_credentials(repo_root=local_project)
    assert payload["status"] == "FAIL"
    assert "LIVE_CREDENTIAL_FILE_MISSING" in payload["blockers"]
    assert payload["secrets_returned"] is False


def test_prepare_blocks_if_credential_path_inside_repo(local_project):
    credential_path = local_project / "local.live-credentials.yaml"
    credential_path.write_text(
        yaml.safe_dump(
            {"exchange_name": "fake", "api_key": "abc123", "api_secret": "def456"}
        ),
        encoding="utf-8",
    )
    payload = load_live_credentials(credential_path, repo_root=local_project)
    assert payload["status"] == "FAIL"
    assert "LIVE_CREDENTIAL_PATH_INSIDE_REPO" in payload["blockers"]
    assert payload["metadata"]["api_key_masked"] == "ab***23"


def test_external_fake_credential_metadata_is_masked(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    credential_path = tmp_path / "outside.live-credentials.yaml"
    credential_path.write_text(
        yaml.safe_dump(
            {
                "exchange_name": "fake",
                "api_key": "abcdef123456",
                "api_secret": "secret-value",
                "account_label": "fixture",
            }
        ),
        encoding="utf-8",
    )
    payload = load_live_credentials(credential_path, repo_root=repo_root)
    assert payload["status"] == "PASS"
    assert payload["metadata"]["api_key_masked"] == "ab***56"
    assert payload["metadata"]["api_secret_present"] is True

