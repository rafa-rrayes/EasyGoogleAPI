"""Test GoogleService class."""

import json
from pathlib import Path

import pytest

from easygoogleapi import GoogleService, ServiceNotEnabledError
from easygoogleapi._types import CredentialType


class TestGoogleServiceValidation:
    """Tests for GoogleService initialization validation."""

    def test_raises_for_invalid_service_name(self, tmp_path):
        """Test that invalid service name raises ValueError."""
        creds = {"installed": {"client_id": "xxx", "client_secret": "yyy"}}
        creds_file = tmp_path / "creds.json"
        creds_file.write_text(json.dumps(creds))

        with pytest.raises(ValueError, match="Unknown services"):
            GoogleService(
                credentials_path=creds_file,
                services=["calendar", "invalid_service"],
            )

    def test_accepts_valid_service_names(self, tmp_path):
        """Test that all valid service names are accepted."""
        creds = {"installed": {"client_id": "xxx", "client_secret": "yyy"}}
        creds_file = tmp_path / "creds.json"
        creds_file.write_text(json.dumps(creds))

        try:
            GoogleService(
                credentials_path=creds_file,
                services=["calendar", "drive", "gmail", "sheets", "docs", "forms", "meet"],
            )
        except ValueError as e:
            if "Unknown services" in str(e):
                pytest.fail("Valid service names should be accepted")
        except Exception:
            pass

    def test_raises_when_both_credentials_path_and_client_config(self, tmp_path):
        """Test mutual exclusivity of credentials_path and client_config."""
        creds_file = tmp_path / "creds.json"
        creds_file.write_text(json.dumps({"installed": {"client_id": "x", "client_secret": "y"}}))

        with pytest.raises(ValueError, match="Cannot specify both"):
            GoogleService(
                credentials_path=creds_file,
                client_config={"web": {"client_id": "a", "client_secret": "b"}},
                services=["drive"],
                auto_auth=False,
            )

    def test_raises_when_neither_credentials_path_nor_client_config(self):
        """Test that omitting both raises."""
        with pytest.raises(ValueError, match="must be provided"):
            GoogleService(services=["drive"], auto_auth=False)

    def test_client_config_creates_instance(self):
        """Test that client_config can be used as sole credential source."""
        google = GoogleService(
            client_config={"web": {"client_id": "x", "client_secret": "y"}},
            services=["drive"],
            auto_auth=False,
        )
        assert google.credential_type == CredentialType.OAUTH
        assert google._credentials_path is None
        assert google._client_config is not None

    def test_client_config_with_token_store(self):
        """Test client_config with an explicit token store."""
        from easygoogleapi import InMemoryTokenStore

        store = InMemoryTokenStore()
        google = GoogleService(
            client_config={"web": {"client_id": "x", "client_secret": "y"}},
            services=["calendar"],
            token_store=store,
            user_id="u1",
            auto_auth=False,
        )
        assert google.user_id == "u1"
        assert google._token_store is store

    def test_client_config_defaults_to_in_memory_store(self):
        """Test that client_config without token_store uses InMemoryTokenStore."""
        from easygoogleapi import InMemoryTokenStore

        google = GoogleService(
            client_config={"web": {"client_id": "x", "client_secret": "y"}},
            services=["drive"],
            auto_auth=False,
        )
        assert isinstance(google._token_store, InMemoryTokenStore)


class TestServiceNotEnabled:
    """Tests for ServiceNotEnabledError."""

    def test_error_message_contains_service_name(self):
        """Test that error message contains the requested service name."""
        error = ServiceNotEnabledError("drive", ["calendar", "gmail"])
        assert "drive" in str(error)

    def test_error_message_contains_enabled_services(self):
        """Test that error message lists enabled services."""
        error = ServiceNotEnabledError("drive", ["calendar", "gmail"])
        assert "calendar" in str(error)
        assert "gmail" in str(error)

    def test_error_has_service_name_attribute(self):
        """Test that error has service_name attribute."""
        error = ServiceNotEnabledError("drive", ["calendar"])
        assert error.service_name == "drive"

    def test_error_has_enabled_services_attribute(self):
        """Test that error has enabled_services attribute."""
        error = ServiceNotEnabledError("drive", ["calendar", "gmail"])
        assert error.enabled_services == ["calendar", "gmail"]


class TestGoogleServiceIntegration:
    """Integration tests requiring real credentials."""

    @pytest.mark.integration
    def test_oauth_credential_detection(self, credentials_path, token_path):
        """Test that OAuth credentials are detected correctly."""
        google = GoogleService(
            credentials_path=credentials_path,
            services=["calendar"],
            token_path=token_path,
        )
        assert google.credential_type == CredentialType.OAUTH

    @pytest.mark.integration
    def test_enabled_services_property(self, credentials_path, token_path):
        """Test that enabled_services returns correct list."""
        google = GoogleService(
            credentials_path=credentials_path,
            services=["calendar", "drive"],
            token_path=token_path,
        )
        assert set(google.enabled_services) == {"calendar", "drive"}

    @pytest.mark.integration
    def test_enabled_services_is_copy(self, credentials_path, token_path):
        """Test that enabled_services returns a copy."""
        google = GoogleService(
            credentials_path=credentials_path,
            services=["calendar"],
            token_path=token_path,
        )
        services = google.enabled_services
        services.append("drive")
        assert "drive" not in google.enabled_services

    @pytest.mark.integration
    def test_accessing_disabled_service_raises(self, credentials_path, token_path):
        """Test that accessing a non-enabled service raises error."""
        google = GoogleService(
            credentials_path=credentials_path,
            services=["calendar"],
            token_path=token_path,
        )
        with pytest.raises(ServiceNotEnabledError):
            _ = google.drive

    @pytest.mark.integration
    def test_service_has_raw_property(self, google_calendar):
        """Test that service has raw property for direct API access."""
        raw = google_calendar.calendar.raw
        assert raw is not None
        assert hasattr(raw, "calendarList")
