"""Test configuration and service registry."""

import pytest


def test_service_registry_has_all_services():
    """Test that SERVICE_REGISTRY contains all expected services."""
    from easygoogleapi._config import SERVICE_REGISTRY

    expected = {"calendar", "drive", "gmail", "sheets", "docs", "forms", "meet"}
    assert set(SERVICE_REGISTRY.keys()) == expected


def test_service_config_has_required_fields():
    """Test that each ServiceConfig has required fields."""
    from easygoogleapi._config import SERVICE_REGISTRY

    for name, config in SERVICE_REGISTRY.items():
        assert config.name == name
        assert config.api_name
        assert config.api_version
        assert len(config.scopes) > 0


def test_forms_has_static_discovery_false():
    """Test that forms service has static_discovery=False."""
    from easygoogleapi._config import SERVICE_REGISTRY

    forms_config = SERVICE_REGISTRY["forms"]
    assert forms_config.build_kwargs.get("static_discovery") is False


def test_get_scopes_for_services():
    """Test scope aggregation for multiple services."""
    from easygoogleapi._config import get_scopes_for_services, SERVICE_REGISTRY

    scopes = get_scopes_for_services(["calendar", "drive"])

    calendar_scopes = set(SERVICE_REGISTRY["calendar"].scopes)
    drive_scopes = set(SERVICE_REGISTRY["drive"].scopes)

    assert set(scopes) == calendar_scopes | drive_scopes


def test_get_scopes_deduplicates():
    """Test that get_scopes_for_services removes duplicates."""
    from easygoogleapi._config import get_scopes_for_services

    # Request same service twice (via list)
    scopes = get_scopes_for_services(["calendar", "calendar"])

    # Should have no duplicates
    assert len(scopes) == len(set(scopes))
