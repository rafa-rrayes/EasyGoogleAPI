"""Shared pytest fixtures for EasyGoogleAPI tests."""

from pathlib import Path

import pytest

# Path to test credentials
TESTS_DIR = Path(__file__).parent
CREDENTIALS_FILES = list(TESTS_DIR.glob("client_secret_*.json"))
CREDENTIALS_PATH = CREDENTIALS_FILES[0] if CREDENTIALS_FILES else None


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (require credentials)"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests (no credentials needed)"
    )


@pytest.fixture(scope="session")
def credentials_path() -> Path:
    """Get path to OAuth credentials file."""
    if not CREDENTIALS_PATH or not CREDENTIALS_PATH.exists():
        pytest.skip("No credentials file found in tests directory")
    return CREDENTIALS_PATH


@pytest.fixture(scope="session")
def google_calendar(credentials_path):
    """Create a GoogleService instance with calendar enabled."""
    from easygoogleapi import GoogleService

    return GoogleService(
        credentials_path=credentials_path,
        services=["calendar"],
    )


@pytest.fixture(scope="session")
def google_drive(credentials_path):
    """Create a GoogleService instance with drive enabled."""
    from easygoogleapi import GoogleService

    return GoogleService(
        credentials_path=credentials_path,
        services=["drive"],
    )


@pytest.fixture(scope="session")
def google_gmail(credentials_path):
    """Create a GoogleService instance with gmail enabled."""
    from easygoogleapi import GoogleService

    return GoogleService(
        credentials_path=credentials_path,
        services=["gmail"],
    )


@pytest.fixture(scope="session")
def google_sheets(credentials_path):
    """Create a GoogleService instance with sheets enabled."""
    from easygoogleapi import GoogleService

    return GoogleService(
        credentials_path=credentials_path,
        services=["sheets"],
    )


@pytest.fixture(scope="session")
def google_docs(credentials_path):
    """Create a GoogleService instance with docs enabled."""
    from easygoogleapi import GoogleService

    return GoogleService(
        credentials_path=credentials_path,
        services=["docs"],
    )


@pytest.fixture(scope="session")
def google_forms(credentials_path):
    """Create a GoogleService instance with forms enabled."""
    from easygoogleapi import GoogleService

    return GoogleService(
        credentials_path=credentials_path,
        services=["forms"],
    )


@pytest.fixture(scope="session")
def google_meet(credentials_path):
    """Create a GoogleService instance with meet enabled."""
    from easygoogleapi import GoogleService

    return GoogleService(
        credentials_path=credentials_path,
        services=["meet"],
    )


@pytest.fixture(scope="session")
def google_all(credentials_path):
    """Create a GoogleService instance with all services enabled."""
    from easygoogleapi import GoogleService

    return GoogleService(
        credentials_path=credentials_path,
        services=["calendar", "drive", "gmail", "sheets", "docs", "forms", "meet"],
    )
