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
        # Create a dummy credentials file
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
        # This test just validates the service name check,
        # not actual auth (which would fail without real creds)
        creds = {"installed": {"client_id": "xxx", "client_secret": "yyy"}}
        creds_file = tmp_path / "creds.json"
        creds_file.write_text(json.dumps(creds))

        # Should not raise ValueError for service names
        # (will fail later during auth, but that's expected)
        try:
            GoogleService(
                credentials_path=creds_file,
                services=["calendar", "drive", "gmail", "sheets", "docs", "forms", "meet"],
            )
        except ValueError as e:
            if "Unknown services" in str(e):
                pytest.fail("Valid service names should be accepted")
            # Other ValueErrors are fine (e.g., from auth)
        except Exception:
            # Auth failures are expected without real credentials
            pass


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
        # Raw should have the calendarList method
        assert hasattr(raw, "calendarList")
