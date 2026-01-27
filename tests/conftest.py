"""Shared pytest fixtures for EasyGoogleAPI tests."""

import os
from pathlib import Path

import pytest

# Path to test credentials
TESTS_DIR = Path(__file__).parent
CREDENTIALS_FILES = list(TESTS_DIR.glob("client_secret_*.json"))
CREDENTIALS_PATH = CREDENTIALS_FILES[0] if CREDENTIALS_FILES else None
TOKEN_PATH = TESTS_DIR / "test_token.pickle"


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (require credentials)"
    )


@pytest.fixture(scope="session")
def credentials_path() -> Path:
    """Get path to OAuth credentials file."""
    if not CREDENTIALS_PATH or not CREDENTIALS_PATH.exists():
        pytest.skip("No credentials file found in tests directory")
    return CREDENTIALS_PATH


@pytest.fixture(scope="session")
def token_path() -> Path:
    """Get path for storing OAuth tokens during tests."""
    return TOKEN_PATH


@pytest.fixture(scope="session")
def google_calendar(credentials_path, token_path):
    """Create a GoogleService instance with calendar enabled."""
    from easygoogleapi import GoogleService

    return GoogleService(
        credentials_path=credentials_path,
        services=["calendar"],
        token_path=token_path,
    )


@pytest.fixture(scope="session")
def google_drive(credentials_path, token_path):
    """Create a GoogleService instance with drive enabled."""
    from easygoogleapi import GoogleService

    return GoogleService(
        credentials_path=credentials_path,
        services=["drive"],
        token_path=token_path,
    )


@pytest.fixture(scope="session")
def google_gmail(credentials_path, token_path):
    """Create a GoogleService instance with gmail enabled."""
    from easygoogleapi import GoogleService

    return GoogleService(
        credentials_path=credentials_path,
        services=["gmail"],
        token_path=token_path,
    )


@pytest.fixture(scope="session")
def google_sheets(credentials_path, token_path):
    """Create a GoogleService instance with sheets enabled."""
    from easygoogleapi import GoogleService

    return GoogleService(
        credentials_path=credentials_path,
        services=["sheets"],
        token_path=token_path,
    )


@pytest.fixture(scope="session")
def google_docs(credentials_path, token_path):
    """Create a GoogleService instance with docs enabled."""
    from easygoogleapi import GoogleService

    return GoogleService(
        credentials_path=credentials_path,
        services=["docs"],
        token_path=token_path,
    )


@pytest.fixture(scope="session")
def google_forms(credentials_path, token_path):
    """Create a GoogleService instance with forms enabled."""
    from easygoogleapi import GoogleService

    return GoogleService(
        credentials_path=credentials_path,
        services=["forms"],
        token_path=token_path,
    )


@pytest.fixture(scope="session")
def google_meet(credentials_path, token_path):
    """Create a GoogleService instance with meet enabled."""
    from easygoogleapi import GoogleService

    return GoogleService(
        credentials_path=credentials_path,
        services=["meet"],
        token_path=token_path,
    )


@pytest.fixture(scope="session")
def google_all(credentials_path, token_path):
    """Create a GoogleService instance with all services enabled."""
    from easygoogleapi import GoogleService

    return GoogleService(
        credentials_path=credentials_path,
        services=["calendar", "drive", "gmail", "sheets", "docs", "forms", "meet"],
        token_path=token_path,
    )
