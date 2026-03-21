"""EasyGoogleAPI — Simplified Python interface for Google APIs."""

from ._base import RetryConfig
from ._pagination import PageIterator
from ._exceptions import (
    APIError,
    AuthenticationError,
    BackendError,
    ConflictError,
    EasyGoogleAPIError,
    InvalidCredentialsError,
    InvalidRequestError,
    MaxRetriesExceededError,
    NotFoundError,
    PermanentError,
    PermissionDeniedError,
    QuotaExceededError,
    RateLimitError,
    ServerError,
    ServiceNotEnabledError,
    TokenExpiredError,
    TokenRevokedError,
    TransientError,
)
from ._async_service import AsyncGoogleService
from ._middleware import MiddlewareChain, RequestContext, ResponseContext
from ._service import GoogleService
from ._token_store import FileTokenStore, InMemoryTokenStore, TokenStore
from ._types import CredentialType, ServiceName
from .calendar import CalendarService
from .contrib.django import DjangoModelTokenStore
from .docs import DocsService
from .drive import DriveService
from .forms import FormsService
from .gmail import GmailService
from .meet import MeetService
from .sheets import SheetsService

__all__ = [
    "GoogleService",
    "AsyncGoogleService",
    "CalendarService",
    "DocsService",
    "DriveService",
    "FormsService",
    "GmailService",
    "MeetService",
    "SheetsService",
    "TokenStore",
    "InMemoryTokenStore",
    "FileTokenStore",
    "DjangoModelTokenStore",
    "EasyGoogleAPIError",
    "AuthenticationError",
    "InvalidCredentialsError",
    "TokenExpiredError",
    "TokenRevokedError",
    "ServiceNotEnabledError",
    "APIError",
    "TransientError",
    "PermanentError",
    "RateLimitError",
    "ServerError",
    "BackendError",
    "PermissionDeniedError",
    "NotFoundError",
    "QuotaExceededError",
    "InvalidRequestError",
    "ConflictError",
    "MaxRetriesExceededError",
    "RetryConfig",
    "PageIterator",
    "MiddlewareChain",
    "RequestContext",
    "ResponseContext",
    "CredentialType",
    "ServiceName",
]

__version__ = "2.0.0"
