"""Custom exceptions for EasyGoogleAPI."""


class EasyGoogleAPIError(Exception):
    """Base exception for all EasyGoogleAPI errors.
    
    Attributes:
        message: Human-readable error message.
        status_code: HTTP status code if applicable.
        retryable: Whether the operation can be retried.
        reason: Short reason/error code.
        request_id: Google API request ID for debugging.
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        retryable: bool = False,
        reason: str | None = None,
        request_id: str | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.retryable = retryable
        self.reason = reason
        self.request_id = request_id


class AuthenticationError(EasyGoogleAPIError):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str = "Authentication failed",
        **kwargs,
    ):
        super().__init__(message, retryable=False, **kwargs)


class InvalidCredentialsError(AuthenticationError):
    """Raised when credentials file is invalid or malformed."""

    def __init__(
        self,
        message: str = "Invalid credentials",
        **kwargs,
    ):
        super().__init__(message, **kwargs)


class TokenExpiredError(AuthenticationError):
    """Raised when token has expired and cannot be refreshed."""

    def __init__(
        self,
        message: str = "Token expired and cannot be refreshed",
        **kwargs,
    ):
        super().__init__(message, **kwargs)


class ServiceNotEnabledError(EasyGoogleAPIError):
    """Raised when accessing a service not specified at initialization."""

    def __init__(self, service_name: str, enabled_services: list[str]):
        self.service_name = service_name
        self.enabled_services = enabled_services
        message = (
            f"Service '{service_name}' was not enabled. "
            f"Enabled services: {enabled_services}. "
            f"Add '{service_name}' to the services list when creating GoogleService."
        )
        super().__init__(message, retryable=False)


class APIError(EasyGoogleAPIError):
    """Wrapper for Google API errors with additional context.
    
    Attributes:
        original_error: The underlying exception from Google API client.
    """

    def __init__(
        self,
        message: str,
        original_error: Exception | None = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.original_error = original_error


# Retryable errors


class TransientError(APIError):
    """Temporary error that can be retried.
    
    This includes network errors, temporary server issues, and rate limits.
    """

    def __init__(self, message: str, **kwargs):
        kwargs.setdefault("retryable", True)
        super().__init__(message, **kwargs)


class RateLimitError(TransientError):
    """Rate limit exceeded error.
    
    Google APIs return HTTP 429 when rate limits are hit. This error
    includes retry_after information when available.
    
    Attributes:
        retry_after: Seconds to wait before retrying (from Retry-After header).
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int | None = None,
        **kwargs,
    ):
        kwargs.setdefault("status_code", 429)
        kwargs.setdefault("reason", "rateLimitExceeded")
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class ServerError(TransientError):
    """Google API server error (5xx status codes).
    
    These are temporary failures on Google's side and are safe to retry.
    """

    def __init__(
        self,
        message: str = "Server error",
        **kwargs,
    ):
        super().__init__(message, **kwargs)


class BackendError(ServerError):
    """Backend error from Google API (503 Service Unavailable)."""

    def __init__(
        self,
        message: str = "Backend error",
        **kwargs,
    ):
        kwargs.setdefault("status_code", 503)
        kwargs.setdefault("reason", "backendError")
        super().__init__(message, **kwargs)


# Non-retryable errors


class PermanentError(APIError):
    """Permanent error that should not be retried.
    
    This includes authentication failures, permission errors, and invalid requests.
    """

    def __init__(self, message: str, **kwargs):
        kwargs.setdefault("retryable", False)
        super().__init__(message, **kwargs)


class PermissionDeniedError(PermanentError):
    """Insufficient permissions to perform the operation.
    
    The authenticated user does not have the required permissions.
    This requires granting additional scopes or permissions.
    """

    def __init__(
        self,
        message: str = "Permission denied",
        **kwargs,
    ):
        kwargs.setdefault("status_code", 403)
        kwargs.setdefault("reason", "forbidden")
        super().__init__(message, **kwargs)


class NotFoundError(PermanentError):
    """Requested resource was not found.
    
    The resource (file, event, etc.) does not exist or has been deleted.
    """

    def __init__(
        self,
        message: str = "Resource not found",
        **kwargs,
    ):
        kwargs.setdefault("status_code", 404)
        kwargs.setdefault("reason", "notFound")
        super().__init__(message, **kwargs)


class QuotaExceededError(PermanentError):
    """Quota limit reached.
    
    The request exceeded a quota limit. Unlike rate limits, quota errors
    typically require waiting for the quota to reset (daily, hourly, etc.)
    or upgrading the quota limit.
    
    Attributes:
        quota_type: Type of quota exceeded (e.g., 'queriesPerDay').
        limit: The quota limit, if available.
    """

    def __init__(
        self,
        message: str = "Quota exceeded",
        quota_type: str | None = None,
        limit: int | None = None,
        **kwargs,
    ):
        kwargs.setdefault("status_code", 429)
        kwargs.setdefault("reason", "quotaExceeded")
        super().__init__(message, **kwargs)
        self.quota_type = quota_type
        self.limit = limit


class InvalidRequestError(PermanentError):
    """Invalid request parameters.
    
    The request is malformed or contains invalid parameters.
    """

    def __init__(
        self,
        message: str = "Invalid request",
        **kwargs,
    ):
        kwargs.setdefault("status_code", 400)
        kwargs.setdefault("reason", "badRequest")
        super().__init__(message, **kwargs)


class ConflictError(PermanentError):
    """Request conflicts with current state.
    
    The operation cannot be completed due to a conflict with the current
    state of the resource (e.g., trying to create a resource that already exists).
    """

    def __init__(
        self,
        message: str = "Conflict",
        **kwargs,
    ):
        kwargs.setdefault("status_code", 409)
        kwargs.setdefault("reason", "conflict")
        super().__init__(message, **kwargs)


class MaxRetriesExceededError(EasyGoogleAPIError):
    """Maximum retry attempts exceeded.
    
    The operation was retried the maximum number of times but still failed.
    
    Attributes:
        attempts: Number of attempts made.
        last_error: The last error encountered.
    """

    def __init__(
        self,
        message: str = "Maximum retries exceeded",
        attempts: int | None = None,
        last_error: Exception | None = None,
    ):
        super().__init__(message, retryable=False)
        self.attempts = attempts
        self.last_error = last_error
