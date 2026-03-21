"""Tests for authentication control methods."""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from easygoogleapi import GoogleService, AuthenticationError, TokenRevokedError
from easygoogleapi._token_store import InMemoryTokenStore
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

    # ---- New: client_config support ----

    def test_client_config_constructor(self):
        """Test constructing GoogleService with client_config dict."""
        google = GoogleService(
            client_config={"web": {"client_id": "x", "client_secret": "y"}},
            services=["drive"],
            auto_auth=False,
        )
        assert google.credential_type == CredentialType.OAUTH
        assert google._credentials_path is None

    def test_client_config_flat_shorthand(self):
        """Test flat shorthand client_config normalizes to web."""
        google = GoogleService(
            client_config={"client_id": "x", "client_secret": "y"},
            services=["drive"],
            auto_auth=False,
        )
        assert google.credential_type == CredentialType.OAUTH

    def test_get_auth_url_returns_tuple(self, tmp_path):
        """Test that get_auth_url returns (url, state) tuple."""
        creds = {"installed": {
            "client_id": "xxx",
            "client_secret": "yyy",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }}
        creds_file = tmp_path / "creds.json"
        creds_file.write_text(json.dumps(creds))

        google = GoogleService(
            credentials_path=creds_file,
            services=["calendar"],
            auto_auth=False,
        )

        result = google.get_auth_url(redirect_uri="http://localhost:3000/callback")
        assert isinstance(result, tuple)
        assert len(result) == 2
        url, state = result
        assert url.startswith("https://accounts.google.com/")
        assert isinstance(state, str)
        assert len(state) > 0

    def test_exchange_code_saves_to_store(self, tmp_path):
        """Test that exchange_code persists credentials to the token store."""
        creds = {"installed": {
            "client_id": "xxx",
            "client_secret": "yyy",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }}
        creds_file = tmp_path / "creds.json"
        creds_file.write_text(json.dumps(creds))

        store = InMemoryTokenStore()
        google = GoogleService(
            credentials_path=creds_file,
            services=["calendar"],
            token_store=store,
            user_id="test_user",
            auto_auth=False,
        )

        # Replace the flow with a fully mocked one after get_auth_url
        google.get_auth_url(redirect_uri="http://localhost:3000/callback")

        mock_creds = MagicMock()
        mock_creds.token = "fake_token"
        mock_creds.refresh_token = "fake_refresh"
        mock_creds.token_uri = "https://oauth2.googleapis.com/token"
        mock_creds.client_id = "xxx"
        mock_creds.client_secret = "yyy"
        mock_creds.scopes = None
        mock_creds.expiry = None

        mock_flow = MagicMock()
        mock_flow.credentials = mock_creds
        google._oauth_flow = mock_flow

        google.exchange_code("fake_code")

        mock_flow.fetch_token.assert_called_once_with(code="fake_code")
        # Token should be saved in the store
        assert store.get("test_user") is not None
        assert store.get("test_user")["token"] == "fake_token"

    def test_custom_scopes_list(self, tmp_path):
        """Test that custom scopes (list) override default scopes."""
        creds = {"installed": {"client_id": "xxx", "client_secret": "yyy"}}
        creds_file = tmp_path / "creds.json"
        creds_file.write_text(json.dumps(creds))

        custom = ["https://www.googleapis.com/auth/drive.readonly"]
        google = GoogleService(
            credentials_path=creds_file,
            services=["drive"],
            auto_auth=False,
            scopes=custom,
        )
        assert google.scopes == custom

    def test_custom_scopes_dict(self, tmp_path):
        """Test that custom scopes (dict) are merged correctly."""
        creds = {"installed": {"client_id": "xxx", "client_secret": "yyy"}}
        creds_file = tmp_path / "creds.json"
        creds_file.write_text(json.dumps(creds))

        custom = {
            "drive": ["https://www.googleapis.com/auth/drive.readonly"],
            "calendar": ["https://www.googleapis.com/auth/calendar.readonly"],
        }
        google = GoogleService(
            credentials_path=creds_file,
            services=["drive", "calendar"],
            auto_auth=False,
            scopes=custom,
        )
        assert set(google.scopes) == {
            "https://www.googleapis.com/auth/drive.readonly",
            "https://www.googleapis.com/auth/calendar.readonly",
        }

    def test_on_token_refresh_callback(self, tmp_path):
        """Test that on_token_refresh callback is called on refresh."""
        creds = {"installed": {"client_id": "xxx", "client_secret": "yyy"}}
        creds_file = tmp_path / "creds.json"
        creds_file.write_text(json.dumps(creds))

        callback = MagicMock()
        google = GoogleService(
            credentials_path=creds_file,
            services=["calendar"],
            auto_auth=False,
            on_token_refresh=callback,
        )

        # Manually set credentials that pretend to be valid
        mock_creds = MagicMock()
        mock_creds.refresh_token = "fake_refresh"
        mock_creds.token = "new_token"
        mock_creds.token_uri = "https://oauth2.googleapis.com/token"
        mock_creds.client_id = "xxx"
        mock_creds.client_secret = "yyy"
        mock_creds.scopes = None
        mock_creds.expiry = None
        google._credentials = mock_creds

        with patch("easygoogleapi._service.refresh_credentials", return_value=mock_creds):
            google.refresh_token()

        callback.assert_called_once_with(mock_creds)


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
        assert expiry is None or isinstance(expiry, datetime)

    @pytest.mark.integration
    def test_refresh_token_succeeds(self, credentials_path, token_path):
        """Test that refresh_token works."""
        google = GoogleService(
            credentials_path=credentials_path,
            services=["calendar"],
            token_path=token_path,
        )

        result = google.refresh_token()
        assert result is True

    @pytest.mark.integration
    def test_get_auth_url_returns_url_and_state(self, credentials_path, tmp_path):
        """Test that get_auth_url returns a valid (URL, state) tuple."""
        google = GoogleService(
            credentials_path=credentials_path,
            services=["calendar"],
            token_path=tmp_path / "token.pickle",
            auto_auth=False,
        )

        url, state = google.get_auth_url()
        assert url.startswith("https://accounts.google.com/")
        assert "client_id=" in url
        assert isinstance(state, str)

    @pytest.mark.integration
    def test_logout_deletes_token(self, credentials_path, tmp_path):
        """Test that logout deletes the token file."""
        token_path = tmp_path / "token.pickle"

        google = GoogleService(
            credentials_path=credentials_path,
            services=["calendar"],
            token_path=token_path,
        )

        assert token_path.exists()

        google.logout()
        assert not token_path.exists()
        assert not google.is_authenticated
