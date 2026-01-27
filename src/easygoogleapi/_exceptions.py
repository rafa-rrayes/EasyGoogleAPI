"""Custom exceptions for EasyGoogleAPI."""


class EasyGoogleAPIError(Exception):
    """Base exception for all EasyGoogleAPI errors."""

    pass


class AuthenticationError(EasyGoogleAPIError):
    """Raised when authentication fails."""

    pass


class InvalidCredentialsError(AuthenticationError):
    """Raised when credentials file is invalid or malformed."""

    pass


class TokenExpiredError(AuthenticationError):
    """Raised when token has expired and cannot be refreshed."""

    pass


class ServiceNotEnabledError(EasyGoogleAPIError):
    """Raised when accessing a service not specified at initialization."""

    def __init__(self, service_name: str, enabled_services: list[str]):
        self.service_name = service_name
        self.enabled_services = enabled_services
        super().__init__(
            f"Service '{service_name}' was not enabled. "
            f"Enabled services: {enabled_services}. "
            f"Add '{service_name}' to the services list when creating GoogleService."
        )


class APIError(EasyGoogleAPIError):
    """Wrapper for Google API errors with additional context."""

    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(message)
        self.original_error = original_error
