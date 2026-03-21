"""Test that all v2.0 modules and symbols can be imported correctly."""

import pytest


class TestCoreImports:
    """Test importing core classes."""

    def test_import_google_service(self):
        """Test importing GoogleService."""
        from easygoogleapi import GoogleService
        assert GoogleService is not None

    def test_import_async_google_service(self):
        """Test importing AsyncGoogleService."""
        from easygoogleapi import AsyncGoogleService
        assert AsyncGoogleService is not None

    def test_import_page_iterator(self):
        """Test importing PageIterator."""
        from easygoogleapi import PageIterator
        assert PageIterator is not None

    def test_import_retry_config(self):
        """Test importing RetryConfig."""
        from easygoogleapi import RetryConfig
        assert RetryConfig is not None


class TestMiddlewareImports:
    """Test importing middleware types."""

    def test_import_middleware_chain(self):
        """Test importing MiddlewareChain."""
        from easygoogleapi import MiddlewareChain
        assert MiddlewareChain is not None

    def test_import_request_context(self):
        """Test importing RequestContext."""
        from easygoogleapi import RequestContext
        assert RequestContext is not None

    def test_import_response_context(self):
        """Test importing ResponseContext."""
        from easygoogleapi import ResponseContext
        assert ResponseContext is not None


class TestServiceImports:
    """Test importing all service classes."""

    def test_import_all_service_classes(self):
        """Test importing all service classes at once."""
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


class TestExceptionImports:
    """Test importing all exception classes."""

    def test_import_base_exceptions(self):
        """Test importing base exception classes."""
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

    def test_import_transient_errors(self):
        """Test importing transient error classes."""
        from easygoogleapi import (
            TransientError,
            RateLimitError,
            ServerError,
            BackendError,
        )
        assert all([TransientError, RateLimitError, ServerError, BackendError])

    def test_import_permanent_errors(self):
        """Test importing permanent error classes (new in v2.0)."""
        from easygoogleapi import (
            PermanentError,
            PermissionDeniedError,
            NotFoundError,
            QuotaExceededError,
            InvalidRequestError,
            ConflictError,
        )
        assert all([
            PermanentError,
            PermissionDeniedError,
            NotFoundError,
            QuotaExceededError,
            InvalidRequestError,
            ConflictError,
        ])

    def test_import_max_retries_exceeded_error(self):
        """Test importing MaxRetriesExceededError."""
        from easygoogleapi import MaxRetriesExceededError
        assert MaxRetriesExceededError is not None

    def test_permanent_error_is_exported(self):
        """Test that PermanentError is now exported (v2.0)."""
        from easygoogleapi import PermanentError
        assert PermanentError is not None


class TestExceptionHierarchy:
    """Test that exception hierarchy is correct in v2.0."""

    def test_base_hierarchy(self):
        """Test base exception hierarchy."""
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

    def test_transient_hierarchy(self):
        """Test transient error hierarchy."""
        from easygoogleapi import (
            APIError,
            TransientError,
            RateLimitError,
            ServerError,
            BackendError,
        )

        assert issubclass(TransientError, APIError)
        assert issubclass(RateLimitError, TransientError)
        assert issubclass(ServerError, TransientError)
        assert issubclass(BackendError, ServerError)

    def test_permanent_hierarchy(self):
        """Test permanent error hierarchy."""
        from easygoogleapi import (
            APIError,
            PermanentError,
            PermissionDeniedError,
            NotFoundError,
            QuotaExceededError,
            InvalidRequestError,
            ConflictError,
        )

        assert issubclass(PermanentError, APIError)
        assert issubclass(PermissionDeniedError, PermanentError)
        assert issubclass(NotFoundError, PermanentError)
        assert issubclass(QuotaExceededError, PermanentError)
        assert issubclass(InvalidRequestError, PermanentError)
        assert issubclass(ConflictError, PermanentError)

    def test_max_retries_exceeded_hierarchy(self):
        """Test MaxRetriesExceededError hierarchy."""
        from easygoogleapi import EasyGoogleAPIError, MaxRetriesExceededError
        assert issubclass(MaxRetriesExceededError, EasyGoogleAPIError)


class TestTokenStoreImports:
    """Test importing token store classes."""

    def test_import_token_stores(self):
        """Test importing all current token store classes."""
        from easygoogleapi import (
            TokenStore,
            InMemoryTokenStore,
            FileTokenStore,
            DjangoModelTokenStore,
        )
        assert all([
            TokenStore,
            InMemoryTokenStore,
            FileTokenStore,
            DjangoModelTokenStore,
        ])


class TestTypeImports:
    """Test importing type definitions."""

    def test_import_credential_type(self):
        """Test importing CredentialType."""
        from easygoogleapi import CredentialType
        assert CredentialType is not None

    def test_import_service_name(self):
        """Test importing ServiceName."""
        from easygoogleapi import ServiceName
        assert ServiceName is not None


class TestDeprecatedSymbolsRemoved:
    """Test that v1.0 symbols that were removed in v2.0 are not importable."""

    def test_json_file_token_store_not_importable(self):
        """Test that JSONFileTokenStore is no longer importable."""
        with pytest.raises(ImportError):
            from easygoogleapi import JSONFileTokenStore  # noqa: F401

    def test_load_token_not_importable(self):
        """Test that load_token is no longer importable from the package."""
        with pytest.raises(ImportError):
            from easygoogleapi import load_token  # noqa: F401

    def test_save_token_not_importable(self):
        """Test that save_token is no longer importable from the package."""
        with pytest.raises(ImportError):
            from easygoogleapi import save_token  # noqa: F401

    def test_delete_token_not_importable(self):
        """Test that delete_token is no longer importable from the package."""
        with pytest.raises(ImportError):
            from easygoogleapi import delete_token  # noqa: F401

    def test_get_oauth_credentials_not_importable(self):
        """Test that get_oauth_credentials is no longer importable from the package."""
        with pytest.raises(ImportError):
            from easygoogleapi import get_oauth_credentials  # noqa: F401


class TestAllExports:
    """Test that __all__ is complete and all symbols are importable."""

    def test_all_symbols_importable(self):
        """Test that every symbol in __all__ can be imported."""
        import easygoogleapi

        for name in easygoogleapi.__all__:
            obj = getattr(easygoogleapi, name, None)
            assert obj is not None, f"Symbol '{name}' in __all__ but not importable"

    def test_version_is_2_0_0(self):
        """Test that version is 2.0.0."""
        from easygoogleapi import __version__
        assert __version__ == "2.0.0"

    def test_import_token_revoked_error(self):
        """Test importing TokenRevokedError and its message."""
        from easygoogleapi import TokenRevokedError
        assert TokenRevokedError is not None

        err = TokenRevokedError()
        assert "revoked" in str(err).lower()

    def test_import_django_model_token_store(self):
        """Test importing DjangoModelTokenStore."""
        from easygoogleapi import DjangoModelTokenStore
        assert DjangoModelTokenStore is not None
