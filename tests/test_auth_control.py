"""Tests for authentication control methods."""

import json
from datetime import datetime

import pytest

from easygoogleapi import GoogleService, AuthenticationError
from easygoogleapi._types import CredentialType


class TestAuthControlUnit:
    """Unit tests for auth control methods (no real credentials)."""

    def test_auto_auth_false_delays_authentication(self, tmp_path):
        """Test that auto_auth=False delays authentication."""
        creds = {"installed": {"client_id": "xxx", "client_secret": "yyy"}}
        creds_file = tmp_path / "creds.json"
        creds_file.write_text(json.dumps(creds))

        google = GoogleService(
            credentials_path=creds_file,
            services=["calendar"],
            auto_auth=False,
        )

        # Should not be authenticated yet
        assert not google.is_authenticated
        assert google._credentials is None

    def test_is_authenticated_false_when_no_credentials(self, tmp_path):
        """Test is_authenticated is False when not authenticated."""
        creds = {"installed": {"client_id": "xxx", "client_secret": "yyy"}}
        creds_file = tmp_path / "creds.json"
        creds_file.write_text(json.dumps(creds))

        google = GoogleService(
            credentials_path=creds_file,
            services=["calendar"],
            auto_auth=False,
        )

        assert google.is_authenticated is False

    def test_get_auth_url_raises_for_service_account(self, tmp_path):
        """Test that get_auth_url raises for service account credentials."""
        creds = {
            "type": "service_account",
            "project_id": "test-project",
            "private_key_id": "key123",
            "private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n-----END RSA PRIVATE KEY-----\n",
            "client_email": "test@test-project.iam.gserviceaccount.com",
            "client_id": "123456789",
        }
        creds_file = tmp_path / "creds.json"
        creds_file.write_text(json.dumps(creds))

        google = GoogleService(
            credentials_path=creds_file,
            services=["calendar"],
            auto_auth=False,
        )

        with pytest.raises(AuthenticationError, match="only available for OAuth"):
            google.get_auth_url()

    def test_refresh_token_raises_for_service_account(self, tmp_path):
        """Test that refresh_token raises for service account credentials."""
        creds = {
            "type": "service_account",
            "project_id": "test-project",
            "private_key_id": "key123",
            "private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n-----END RSA PRIVATE KEY-----\n",
            "client_email": "test@test-project.iam.gserviceaccount.com",
            "client_id": "123456789",
        }
        creds_file = tmp_path / "creds.json"
        creds_file.write_text(json.dumps(creds))

        google = GoogleService(
            credentials_path=creds_file,
            services=["calendar"],
            auto_auth=False,
        )

        with pytest.raises(AuthenticationError, match="only available for OAuth"):
            google.refresh_token()

    def test_revoke_raises_for_service_account(self, tmp_path):
        """Test that revoke raises for service account credentials."""
        creds = {
            "type": "service_account",
            "project_id": "test-project",
            "private_key_id": "key123",
            "private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n-----END RSA PRIVATE KEY-----\n",
            "client_email": "test@test-project.iam.gserviceaccount.com",
            "client_id": "123456789",
        }
        creds_file = tmp_path / "creds.json"
        creds_file.write_text(json.dumps(creds))

        google = GoogleService(
            credentials_path=creds_file,
            services=["calendar"],
            auto_auth=False,
        )

        with pytest.raises(AuthenticationError, match="only available for OAuth"):
            google.revoke()

    def test_exchange_code_raises_without_flow(self, tmp_path):
        """Test that exchange_code raises if no flow is active."""
        creds = {"installed": {"client_id": "xxx", "client_secret": "yyy"}}
        creds_file = tmp_path / "creds.json"
        creds_file.write_text(json.dumps(creds))

        google = GoogleService(
            credentials_path=creds_file,
            services=["calendar"],
            auto_auth=False,
        )

        with pytest.raises(AuthenticationError, match="No active OAuth flow"):
            google.exchange_code("some_code")

    def test_scopes_property(self, tmp_path):
        """Test that scopes property returns correct scopes."""
        creds = {"installed": {"client_id": "xxx", "client_secret": "yyy"}}
        creds_file = tmp_path / "creds.json"
        creds_file.write_text(json.dumps(creds))

        google = GoogleService(
            credentials_path=creds_file,
            services=["calendar", "drive"],
            auto_auth=False,
        )

        scopes = google.scopes
        assert "https://www.googleapis.com/auth/calendar" in scopes
        assert "https://www.googleapis.com/auth/drive" in scopes

    def test_scopes_returns_copy(self, tmp_path):
        """Test that scopes returns a copy."""
        creds = {"installed": {"client_id": "xxx", "client_secret": "yyy"}}
        creds_file = tmp_path / "creds.json"
        creds_file.write_text(json.dumps(creds))

        google = GoogleService(
            credentials_path=creds_file,
            services=["calendar"],
            auto_auth=False,
        )

        scopes = google.scopes
        scopes.append("fake_scope")
        assert "fake_scope" not in google.scopes


class TestCredentialInfoUnit:
    """Unit tests for credential info properties."""

    def test_project_id_for_oauth_returns_none(self, tmp_path):
        """Test that project_id returns None for OAuth credentials."""
        creds = {"installed": {"client_id": "xxx", "client_secret": "yyy"}}
        creds_file = tmp_path / "creds.json"
        creds_file.write_text(json.dumps(creds))

        google = GoogleService(
            credentials_path=creds_file,
            services=["calendar"],
            auto_auth=False,
        )

        assert google.project_id is None

    def test_service_account_email_for_oauth_returns_none(self, tmp_path):
        """Test that service_account_email returns None for OAuth credentials."""
        creds = {"installed": {"client_id": "xxx", "client_secret": "yyy"}}
        creds_file = tmp_path / "creds.json"
        creds_file.write_text(json.dumps(creds))

        google = GoogleService(
            credentials_path=creds_file,
            services=["calendar"],
            auto_auth=False,
        )

        assert google.service_account_email is None

    def test_token_expiry_none_when_not_authenticated(self, tmp_path):
        """Test that token_expiry is None when not authenticated."""
        creds = {"installed": {"client_id": "xxx", "client_secret": "yyy"}}
        creds_file = tmp_path / "creds.json"
        creds_file.write_text(json.dumps(creds))

        google = GoogleService(
            credentials_path=creds_file,
            services=["calendar"],
            auto_auth=False,
        )

        assert google.token_expiry is None

    def test_user_email_none_when_not_authenticated(self, tmp_path):
        """Test that user_email is None when not authenticated."""
        creds = {"installed": {"client_id": "xxx", "client_secret": "yyy"}}
        creds_file = tmp_path / "creds.json"
        creds_file.write_text(json.dumps(creds))

        google = GoogleService(
            credentials_path=creds_file,
            services=["calendar"],
            auto_auth=False,
        )

        assert google.user_email is None


class TestAuthControlIntegration:
    """Integration tests for auth control (require real credentials)."""

    @pytest.mark.integration
    def test_is_authenticated_true_after_auth(self, google_calendar):
        """Test is_authenticated is True after authentication."""
        assert google_calendar.is_authenticated is True

    @pytest.mark.integration
    def test_token_expiry_is_datetime(self, google_calendar):
        """Test that token_expiry returns a datetime."""
        expiry = google_calendar.token_expiry
        # OAuth tokens have expiry
        assert expiry is None or isinstance(expiry, datetime)

    @pytest.mark.integration
    def test_refresh_token_succeeds(self, credentials_path, token_path):
        """Test that refresh_token works."""
        google = GoogleService(
            credentials_path=credentials_path,
            services=["calendar"],
            token_path=token_path,
        )

        # This may or may not actually refresh depending on token state
        result = google.refresh_token()
        assert result is True

    @pytest.mark.integration
    def test_get_auth_url_returns_url(self, credentials_path, tmp_path):
        """Test that get_auth_url returns a valid URL."""
        google = GoogleService(
            credentials_path=credentials_path,
            services=["calendar"],
            token_path=tmp_path / "token.pickle",
            auto_auth=False,
        )

        url = google.get_auth_url()
        assert url.startswith("https://accounts.google.com/")
        assert "client_id=" in url

    @pytest.mark.integration
    def test_logout_deletes_token(self, credentials_path, tmp_path):
        """Test that logout deletes the token file."""
        token_path = tmp_path / "token.pickle"

        google = GoogleService(
            credentials_path=credentials_path,
            services=["calendar"],
            token_path=token_path,
        )

        # Token should exist after auth
        assert token_path.exists()

        # Logout should delete it
        google.logout()
        assert not token_path.exists()
        assert not google.is_authenticated
