"""Test that all modules can be imported correctly."""


def test_import_google_service():
    """Test importing GoogleService."""
    from easygoogleapi import GoogleService
    assert GoogleService is not None


def test_import_service_classes():
    """Test importing all service classes."""
    from easygoogleapi import (
        CalendarService,
        DocsService,
        DriveService,
        FormsService,
        GmailService,
        MeetService,
        SheetsService,
    )
    assert all([
        CalendarService,
        DocsService,
        DriveService,
        FormsService,
        GmailService,
        MeetService,
        SheetsService,
    ])


def test_import_exceptions():
    """Test importing all exception classes."""
    from easygoogleapi import (
        EasyGoogleAPIError,
        AuthenticationError,
        InvalidCredentialsError,
        TokenExpiredError,
        TokenRevokedError,
        ServiceNotEnabledError,
        APIError,
    )
    assert all([
        EasyGoogleAPIError,
        AuthenticationError,
        InvalidCredentialsError,
        TokenExpiredError,
        TokenRevokedError,
        ServiceNotEnabledError,
        APIError,
    ])


def test_exception_hierarchy():
    """Test that exception hierarchy is correct."""
    from easygoogleapi import (
        EasyGoogleAPIError,
        AuthenticationError,
        InvalidCredentialsError,
        TokenExpiredError,
        TokenRevokedError,
        ServiceNotEnabledError,
        APIError,
    )

    assert issubclass(AuthenticationError, EasyGoogleAPIError)
    assert issubclass(InvalidCredentialsError, AuthenticationError)
    assert issubclass(TokenExpiredError, AuthenticationError)
    assert issubclass(TokenRevokedError, AuthenticationError)
    assert issubclass(ServiceNotEnabledError, EasyGoogleAPIError)
    assert issubclass(APIError, EasyGoogleAPIError)


def test_import_token_revoked_error():
    """Test importing TokenRevokedError."""
    from easygoogleapi import TokenRevokedError
    assert TokenRevokedError is not None

    err = TokenRevokedError()
    assert "revoked" in str(err).lower()


def test_import_django_model_token_store():
    """Test importing DjangoModelTokenStore."""
    from easygoogleapi import DjangoModelTokenStore
    assert DjangoModelTokenStore is not None


def test_import_token_stores():
    """Test importing all token store classes."""
    from easygoogleapi import (
        TokenStore,
        InMemoryTokenStore,
        FileTokenStore,
        JSONFileTokenStore,
        DjangoModelTokenStore,
    )
    assert all([
        TokenStore,
        InMemoryTokenStore,
        FileTokenStore,
        JSONFileTokenStore,
        DjangoModelTokenStore,
    ])


def test_version_is_1_0_0():
    """Test that version is 1.0.0."""
    from easygoogleapi import __version__
    assert __version__ == "1.0.0"
