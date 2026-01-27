"""Test authentication logic."""

import json
import tempfile
from pathlib import Path

import pytest

from easygoogleapi._auth import detect_credential_type
from easygoogleapi._types import CredentialType
from easygoogleapi._exceptions import InvalidCredentialsError


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
