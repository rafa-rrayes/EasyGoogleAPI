"""Test authentication logic (v2.0)."""

import json
from pathlib import Path

import pytest

from easygoogleapi._auth import (
    create_oauth_flow,
    detect_credential_type,
    normalize_client_config,
)
from easygoogleapi._exceptions import InvalidCredentialsError
from easygoogleapi._types import CredentialType


class TestDetectCredentialType:
    """Tests for detect_credential_type function."""

    def test_detects_oauth_installed(self, tmp_path):
        """Test detection of OAuth installed app credentials."""
        creds = {"installed": {"client_id": "xxx", "client_secret": "yyy"}}
        creds_file = tmp_path / "creds.json"
        creds_file.write_text(json.dumps(creds))

        result = detect_credential_type(creds_file)
        assert result == CredentialType.OAUTH

    def test_detects_oauth_web(self, tmp_path):
        """Test detection of OAuth web app credentials."""
        creds = {"web": {"client_id": "xxx", "client_secret": "yyy"}}
        creds_file = tmp_path / "creds.json"
        creds_file.write_text(json.dumps(creds))

        result = detect_credential_type(creds_file)
        assert result == CredentialType.OAUTH

    def test_detects_service_account(self, tmp_path):
        """Test detection of service account credentials."""
        creds = {
            "type": "service_account",
            "project_id": "test-project",
            "private_key": "xxx",
        }
        creds_file = tmp_path / "creds.json"
        creds_file.write_text(json.dumps(creds))

        result = detect_credential_type(creds_file)
        assert result == CredentialType.SERVICE_ACCOUNT

    def test_raises_for_invalid_format(self, tmp_path):
        """Test that invalid format raises InvalidCredentialsError."""
        creds = {"unknown": "format"}
        creds_file = tmp_path / "creds.json"
        creds_file.write_text(json.dumps(creds))

        with pytest.raises(InvalidCredentialsError):
            detect_credential_type(creds_file)

    def test_raises_for_missing_file(self, tmp_path):
        """Test that missing file raises InvalidCredentialsError."""
        creds_file = tmp_path / "nonexistent.json"

        with pytest.raises(InvalidCredentialsError):
            detect_credential_type(creds_file)

    def test_raises_for_invalid_json(self, tmp_path):
        """Test that invalid JSON raises InvalidCredentialsError."""
        creds_file = tmp_path / "creds.json"
        creds_file.write_text("not valid json")

        with pytest.raises(InvalidCredentialsError):
            detect_credential_type(creds_file)

    # ---- Dict-based credential detection ----

    def test_detects_oauth_web_from_dict(self):
        """Test detection of OAuth web config from an in-memory dict."""
        config = {"web": {"client_id": "xxx", "client_secret": "yyy"}}
        result = detect_credential_type(config)
        assert result == CredentialType.OAUTH

    def test_detects_oauth_installed_from_dict(self):
        """Test detection of OAuth installed config from dict."""
        config = {"installed": {"client_id": "xxx", "client_secret": "yyy"}}
        result = detect_credential_type(config)
        assert result == CredentialType.OAUTH

    def test_detects_flat_shorthand_from_dict(self):
        """Test detection of flat shorthand (normalizes to web)."""
        config = {"client_id": "xxx", "client_secret": "yyy"}
        result = detect_credential_type(config)
        assert result == CredentialType.OAUTH

    def test_raises_for_invalid_dict(self):
        """Test that a dict without proper keys raises."""
        with pytest.raises(InvalidCredentialsError):
            detect_credential_type({"random_key": "value"})


class TestNormalizeClientConfig:
    """Tests for normalize_client_config."""

    def test_passthrough_web(self):
        """Standard web config is returned unchanged."""
        config = {"web": {"client_id": "a", "client_secret": "b"}}
        assert normalize_client_config(config) is config

    def test_passthrough_installed(self):
        """Standard installed config is returned unchanged."""
        config = {"installed": {"client_id": "a", "client_secret": "b"}}
        assert normalize_client_config(config) is config

    def test_flat_shorthand_to_web(self):
        """Flat shorthand becomes a web config."""
        result = normalize_client_config(
            {"client_id": "id", "client_secret": "secret"}
        )
        assert "web" in result
        assert result["web"]["client_id"] == "id"
        assert result["web"]["client_secret"] == "secret"
        assert "auth_uri" in result["web"]
        assert "token_uri" in result["web"]

    def test_flat_shorthand_custom_uris(self):
        """Flat shorthand preserves custom auth/token URIs."""
        result = normalize_client_config({
            "client_id": "id",
            "client_secret": "secret",
            "auth_uri": "https://custom/auth",
            "token_uri": "https://custom/token",
        })
        assert result["web"]["auth_uri"] == "https://custom/auth"
        assert result["web"]["token_uri"] == "https://custom/token"

    def test_service_account_passthrough(self):
        """Service account dicts are passed through."""
        config = {"type": "service_account", "project_id": "p"}
        assert normalize_client_config(config) is config

    def test_raises_for_invalid(self):
        """Dict without required keys raises."""
        with pytest.raises(InvalidCredentialsError):
            normalize_client_config({"bad": "data"})


class TestPKCE:
    """Tests for PKCE support in OAuth flows (v2.0)."""

    def test_pkce_enabled_by_default(self, tmp_path):
        """Test that PKCE is enabled by default (autogenerate_code_verifier=True)."""
        creds = {
            "installed": {
                "client_id": "xxx",
                "client_secret": "yyy",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }
        creds_file = tmp_path / "creds.json"
        creds_file.write_text(json.dumps(creds))

        flow = create_oauth_flow(
            creds_file,
            scopes=["https://www.googleapis.com/auth/calendar"],
        )
        assert flow.autogenerate_code_verifier is True

    def test_pkce_enabled_with_dict_config(self):
        """Test that PKCE is enabled when using dict config."""
        config = {
            "web": {
                "client_id": "xxx",
                "client_secret": "yyy",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }

        flow = create_oauth_flow(
            config,
            scopes=["https://www.googleapis.com/auth/drive"],
        )
        assert flow.autogenerate_code_verifier is True

    def test_pkce_can_be_disabled(self, tmp_path):
        """Test that PKCE can be explicitly disabled."""
        creds = {
            "installed": {
                "client_id": "xxx",
                "client_secret": "yyy",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }
        creds_file = tmp_path / "creds.json"
        creds_file.write_text(json.dumps(creds))

        flow = create_oauth_flow(
            creds_file,
            scopes=["https://www.googleapis.com/auth/calendar"],
            pkce=False,
        )
        # When pkce=False, autogenerate_code_verifier should not be True
        assert not getattr(flow, "autogenerate_code_verifier", False)
