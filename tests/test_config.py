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


class TestScopePresets:
    """Tests for scope presets (v2.0)."""

    def test_readonly_preset_has_expected_services(self):
        """Test that readonly preset covers expected services."""
        from easygoogleapi._types import SCOPE_PRESETS

        readonly = SCOPE_PRESETS["readonly"]
        assert "drive" in readonly
        assert "gmail" in readonly
        assert "calendar" in readonly
        assert "sheets" in readonly
        assert "docs" in readonly

    def test_full_preset_has_expected_services(self):
        """Test that full preset covers expected services."""
        from easygoogleapi._types import SCOPE_PRESETS

        full = SCOPE_PRESETS["full"]
        assert "drive" in full
        assert "gmail" in full
        assert "calendar" in full
        assert "sheets" in full
        assert "docs" in full
        assert "forms" in full
        assert "meet" in full

    def test_readonly_scopes_are_readonly(self):
        """Test that readonly preset uses readonly scope variants."""
        from easygoogleapi._types import SCOPE_PRESETS

        readonly = SCOPE_PRESETS["readonly"]
        for service, scopes in readonly.items():
            for scope in scopes:
                assert "readonly" in scope, (
                    f"Readonly preset for {service} should use readonly scopes, got: {scope}"
                )

    def test_full_scopes_are_not_readonly(self):
        """Test that full preset uses full-access scope variants."""
        from easygoogleapi._types import SCOPE_PRESETS

        full = SCOPE_PRESETS["full"]
        for service, scopes in full.items():
            for scope in scopes:
                assert "readonly" not in scope, (
                    f"Full preset for {service} should not use readonly scopes, got: {scope}"
                )

    def test_presets_contain_only_valid_keys(self):
        """Test that preset keys are 'readonly' and 'full'."""
        from easygoogleapi._types import SCOPE_PRESETS

        assert set(SCOPE_PRESETS.keys()) == {"readonly", "full"}
