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
        ServiceNotEnabledError,
        APIError,
    )
    assert all([
        EasyGoogleAPIError,
        AuthenticationError,
        InvalidCredentialsError,
        TokenExpiredError,
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
        ServiceNotEnabledError,
        APIError,
    )

    assert issubclass(AuthenticationError, EasyGoogleAPIError)
    assert issubclass(InvalidCredentialsError, AuthenticationError)
    assert issubclass(TokenExpiredError, AuthenticationError)
    assert issubclass(ServiceNotEnabledError, EasyGoogleAPIError)
    assert issubclass(APIError, EasyGoogleAPIError)
