"""EasyGoogleAPI - Simplified Python interface for Google APIs.

Example usage:
    from easygoogleapi import GoogleService

    google = GoogleService(
        credentials_path="credentials.json",
        services=["calendar", "drive", "gmail"]
    )

    # Access services as properties
    events = google.calendar.list_events()
    google.drive.upload_file("document.pdf")
    google.gmail.send(to="user@example.com", subject="Hello", body="World")
    
Multi-user usage:
    from easygoogleapi import GoogleService
    from easygoogleapi.token_store import SQLAlchemyTokenStore
    
    # Create GoogleService for a specific user
    google = GoogleService.for_user(
        user_id="user_123",
        token_store=SQLAlchemyTokenStore(db_session),
        credentials_path="oauth_credentials.json",
        services=["calendar", "gmail"]
    )
"""

from collections.abc import Sequence
from datetime import datetime
from functools import cached_property
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from ._auth import (
    credentials_to_dict,
    delete_token,
    delete_token_from_store,
    detect_credential_type,
    dict_to_credentials,
    exchange_code,
    get_auth_url,
    get_oauth_credentials,
    get_oauth_credentials_from_store,
    get_service_account_credentials,
    get_service_account_info,
    load_token,
    load_token_from_store,
    refresh_credentials,
    revoke_credentials,
    save_token,
    save_token_to_store,
)
from ._base import RetryConfig
from ._config import SERVICE_REGISTRY, get_scopes_for_services
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
    PermissionDeniedError,
    QuotaExceededError,
    RateLimitError,
    ServerError,
    ServiceNotEnabledError,
    TokenExpiredError,
    TransientError,
)
from ._token_store import FileTokenStore, InMemoryTokenStore, JSONFileTokenStore, TokenStore
from ._types import CredentialType, ServiceName
from .calendar import CalendarService
from .docs import DocsService
from .drive import DriveService
from .forms import FormsService
from .gmail import GmailService
from .meet import MeetService
from .sheets import SheetsService

__all__ = [
    # Main class
    "GoogleService",
    # Service classes (for type hints)
    "CalendarService",
    "DocsService",
    "DriveService",
    "FormsService",
    "GmailService",
    "MeetService",
    "SheetsService",
    # Token stores
    "TokenStore",
    "InMemoryTokenStore",
    "FileTokenStore",
    "JSONFileTokenStore",
    # Exceptions
    "EasyGoogleAPIError",
    "AuthenticationError",
    "InvalidCredentialsError",
    "TokenExpiredError",
    "ServiceNotEnabledError",
    "APIError",
    "TransientError",
    "RateLimitError",
    "ServerError",
    "BackendError",
    "PermissionDeniedError",
    "NotFoundError",
    "QuotaExceededError",
    "InvalidRequestError",
    "ConflictError",
    "MaxRetriesExceededError",
    # Configuration
    "RetryConfig",
    # Types
    "CredentialType",
    "ServiceName",
]

__version__ = "0.2.0"


class GoogleService:
    """Main entry point for EasyGoogleAPI.

    Handles authentication and provides access to Google API services
    through lazy-loaded properties.
    
    For backwards compatibility, the simple constructor is still supported:
        google = GoogleService(
            credentials_path="credentials.json",
            services=["calendar", "drive"]
        )
    
    For multi-user production applications, use factory methods:
        # OAuth with per-user tokens
        google = GoogleService.for_user(
            user_id="user_123",
            token_store=DatabaseTokenStore(session),
            credentials_path="oauth_client.json",
            services=["calendar"]
        )
        
        # Service account with domain delegation
        google = GoogleService.for_service_account(
            credentials_path="service_account.json",
            services=["drive"],
            impersonate_user="user@domain.com"
        )

    Args:
        credentials_path: Path to the credentials JSON file (OAuth or service account).
        services: List of services to enable (e.g., ['calendar', 'drive', 'gmail']).
        token_path: (Deprecated) Custom path for storing OAuth tokens.
                   Use token_store for production. Defaults to same directory as 
                   credentials with '_token.pickle' suffix.
        token_store: (New) Pluggable token storage. If not provided, falls back 
                    to file-based storage for backwards compatibility.
        user_id: (New) User identifier for multi-user scenarios. Auto-generated 
                from token_path if not provided.
        auto_auth: If True (default), authenticate immediately. If False, delay until
                   authenticate() is called or a service is accessed.
        oauth_port: Port for OAuth callback server (default: 8080). The redirect URI
                   will be http://localhost:{port}/
        retry_config: Configuration for retry behavior. Uses defaults if None.

    Example:
        >>> google = GoogleService(
        ...     credentials_path="credentials.json",
        ...     services=["calendar", "drive"]
        ... )
        >>> events = google.calendar.list_events()
    """

    def __init__(
        self,
        credentials_path: str | Path,
        services: Sequence[ServiceName],
        token_path: str | Path | None = None,
        token_store: TokenStore | None = None,
        user_id: str | None = None,
        auto_auth: bool = True,
        oauth_port: int = 8080,
        retry_config: RetryConfig | None = None,
    ):
        self._credentials_path = Path(credentials_path).expanduser().resolve()
        self._enabled_services: list[ServiceName] = list(services)
        self._credentials = None
        self._oauth_flow: InstalledAppFlow | None = None
        self._oauth_port = oauth_port
        self._retry_config = retry_config or RetryConfig()

        # Validate services
        invalid = set(services) - set(SERVICE_REGISTRY.keys())
        if invalid:
            raise ValueError(
                f"Unknown services: {invalid}. "
                f"Valid services: {list(SERVICE_REGISTRY.keys())}"
            )

        # Set up token storage
        if token_store is not None:
            # New multi-user mode
            self._token_store = token_store
            self._user_id = user_id
            if self._user_id is None:
                raise ValueError("user_id must be provided when using token_store")
            self._token_path = None  # Not used in new mode
        else:
            # Legacy single-user mode with file-based storage
            if token_path:
                self._token_path = Path(token_path).expanduser().resolve()
            else:
                # Default: credentials.json -> credentials_token.pickle
                self._token_path = self._credentials_path.with_name(
                    self._credentials_path.stem + "_token.pickle"
                )
            
            # Create FileTokenStore for backwards compatibility
            self._token_store = FileTokenStore(directory=self._token_path.parent)
            # Use token file stem as user_id for backwards compat
            self._user_id = user_id or self._token_path.stem

        # Get combined scopes and detect credential type
        self._scopes = get_scopes_for_services(self._enabled_services)
        self._credential_type = detect_credential_type(self._credentials_path)

        if auto_auth:
            self.authenticate()
    
    # =========================================================================
    # Factory Methods for Multi-User Support
    # =========================================================================
    
    @classmethod
    def for_user(
        cls,
        user_id: str,
        token_store: TokenStore,
        credentials_path: str | Path,
        services: Sequence[ServiceName],
        auto_auth: bool = True,
        oauth_port: int = 8080,
        retry_config: RetryConfig | None = None,
    ) -> "GoogleService":
        """Create GoogleService for a specific user with OAuth.
        
        Use this factory method for multi-user web applications where each
        user has their own OAuth token.
        
        Args:
            user_id: Unique identifier for the user.
            token_store: Token storage backend (database, Redis, etc.).
            credentials_path: Path to OAuth client credentials JSON.
            services: List of services to enable.
            auto_auth: If True, authenticate immediately.
            oauth_port: Port for OAuth callback (for initial auth).
            retry_config: Configuration for retry behavior.
            
        Returns:
            GoogleService instance configured for the user.
            
        Example:
            >>> from easygoogleapi import GoogleService
            >>> from easygoogleapi.token_store import SQLAlchemyTokenStore
            >>> 
            >>> store = SQLAlchemyTokenStore(db_session)
            >>> google = GoogleService.for_user(
            ...     user_id="user_123",
            ...     token_store=store,
            ...     credentials_path="oauth_client.json",
            ...     services=["calendar", "gmail"]
            ... )
            >>> events = google.calendar.list_events()
        """
        return cls(
            credentials_path=credentials_path,
            services=services,
            token_store=token_store,
            user_id=user_id,
            auto_auth=auto_auth,
            oauth_port=oauth_port,
            retry_config=retry_config,
        )
    
    @classmethod
    def for_service_account(
        cls,
        credentials_path: str | Path,
        services: Sequence[ServiceName],
        impersonate_user: str | None = None,
        retry_config: RetryConfig | None = None,
    ) -> "GoogleService":
        """Create GoogleService using a service account.
        
        Use this for server-to-server communication or when using domain
        delegation to access user data without user consent.
        
        Args:
            credentials_path: Path to service account JSON file.
            services: List of services to enable.
            impersonate_user: Email of user to impersonate (requires domain delegation).
            retry_config: Configuration for retry behavior.
            
        Returns:
            GoogleService instance using service account.
            
        Example:
            >>> google = GoogleService.for_service_account(
            ...     credentials_path="service_account.json",
            ...     services=["drive", "sheets"],
            ...     impersonate_user="user@domain.com"
            ... )
            >>> files = google.drive.list_files()
        """
        instance = cls(
            credentials_path=credentials_path,
            services=services,
            auto_auth=False,  # We'll handle auth manually
            retry_config=retry_config,
        )
        
        # Override with service account credentials
        instance._impersonate_user = impersonate_user
        instance._credentials = get_service_account_credentials(
            instance._credentials_path,
            instance._scopes,
            subject=impersonate_user,
        )
        
        return instance

    # =========================================================================
    # Authentication Control Methods
    # =========================================================================

    def authenticate(self, open_browser: bool = True, port: int | None = None) -> bool:
        """Perform authentication.

        Args:
            open_browser: If True, opens browser for OAuth flow. If False and no
                         valid token exists, raises AuthenticationError.
            port: Port for OAuth callback server. Defaults to oauth_port from constructor.

        Returns:
            True if authentication was successful.

        Raises:
            AuthenticationError: If authentication fails.
        """
        if self._credential_type == CredentialType.OAUTH:
            # Use token store for OAuth credentials
            self._credentials = get_oauth_credentials_from_store(
                self._credentials_path,
                self._token_store,
                self._user_id,
                self._scopes,
                open_browser=open_browser,
                port=port or self._oauth_port,
            )
        else:
            # Service accounts don't use token stores
            subject = getattr(self, '_impersonate_user', None)
            self._credentials = get_service_account_credentials(
                self._credentials_path,
                self._scopes,
                subject=subject,
            )
        return True

    @property
    def is_authenticated(self) -> bool:
        """Check if currently authenticated with valid credentials."""
        if self._credentials is None:
            return False

        if self._credential_type == CredentialType.SERVICE_ACCOUNT:
            return True  # Service accounts are always valid once loaded

        # For OAuth, check if token is valid and not expired
        return self._credentials.valid and not self._credentials.expired

    def get_auth_url(self, redirect_uri: str | None = None) -> str:
        """Get OAuth authorization URL without opening browser.

        Use this for custom OAuth flows where you handle the redirect yourself.
        After the user authorizes, call exchange_code() with the authorization code.

        Args:
            redirect_uri: Custom redirect URI. Defaults to OOB flow.

        Returns:
            The authorization URL to redirect the user to.

        Raises:
            AuthenticationError: If using service account credentials.
        """
        if self._credential_type == CredentialType.SERVICE_ACCOUNT:
            raise AuthenticationError(
                "get_auth_url() is only available for OAuth credentials"
            )

        uri = redirect_uri or "urn:ietf:wg:oauth:2.0:oob"
        auth_url, self._oauth_flow = get_auth_url(
            self._credentials_path, self._scopes, uri
        )
        return auth_url

    def exchange_code(self, code: str) -> bool:
        """Exchange authorization code for credentials.

        Use this after get_auth_url() when the user provides the authorization code.

        Args:
            code: The authorization code from the OAuth callback.

        Returns:
            True if exchange was successful.

        Raises:
            AuthenticationError: If no OAuth flow is active or exchange fails.
        """
        if self._oauth_flow is None:
            raise AuthenticationError(
                "No active OAuth flow. Call get_auth_url() first."
            )

        self._credentials = exchange_code(
            self._oauth_flow, code, self._token_path
        )
        self._oauth_flow = None
        return True

    def refresh_token(self) -> bool:
        """Force refresh the OAuth token.

        Returns:
            True if refresh was successful.

        Raises:
            AuthenticationError: If refresh fails or using service account.
        """
        if self._credential_type == CredentialType.SERVICE_ACCOUNT:
            raise AuthenticationError(
                "refresh_token() is only available for OAuth credentials"
            )

        if self._credentials is None:
            raise AuthenticationError("Not authenticated")

        self._credentials = refresh_credentials(self._credentials)
        save_token_to_store(self._token_store, self._user_id, self._credentials)
        return True

    def revoke(self) -> bool:
        """Revoke the current OAuth token and delete stored token.

        Returns:
            True if revocation was successful.

        Raises:
            AuthenticationError: If using service account credentials.
        """
        if self._credential_type == CredentialType.SERVICE_ACCOUNT:
            raise AuthenticationError(
                "revoke() is only available for OAuth credentials"
            )

        if self._credentials is None:
            return False

        success = revoke_credentials(self._credentials)
        delete_token_from_store(self._token_store, self._user_id)
        self._credentials = None

        # Clear cached services
        self._clear_service_cache()

        return success

    def logout(self) -> bool:
        """Delete stored token without revoking (local logout only).

        Returns:
            True if token was deleted.
        """
        if self._credential_type == CredentialType.SERVICE_ACCOUNT:
            raise AuthenticationError(
                "logout() is only available for OAuth credentials"
            )

        deleted = delete_token_from_store(self._token_store, self._user_id)
        self._credentials = None
        self._clear_service_cache()
        return deleted

    # =========================================================================
    # Token/Credential Info Properties
    # =========================================================================

    @property
    def token_expiry(self) -> datetime | None:
        """Get the token expiry datetime (OAuth only).

        Returns:
            The datetime when the token expires, or None for service accounts
            or if not authenticated.
        """
        if self._credentials is None:
            return None

        if self._credential_type == CredentialType.SERVICE_ACCOUNT:
            return None  # Service account tokens are managed automatically

        return self._credentials.expiry

    @property
    def user_email(self) -> str | None:
        """Get the authenticated user's email (OAuth only).

        Returns:
            The user's email address, or None if not available.
        """
        if self._credentials is None:
            return None

        if self._credential_type == CredentialType.SERVICE_ACCOUNT:
            # Service accounts have a service account email
            info = get_service_account_info(self._credentials_path)
            return info.get("client_email")

        # For OAuth, we need to get the user info from the token
        # The email might be in the id_token if available
        if hasattr(self._credentials, "_id_token") and self._credentials._id_token:
            return self._credentials._id_token.get("email")

        return None

    @property
    def project_id(self) -> str | None:
        """Get the project ID (service account only).

        Returns:
            The GCP project ID, or None for OAuth credentials.
        """
        if self._credential_type == CredentialType.OAUTH:
            return None

        info = get_service_account_info(self._credentials_path)
        return info.get("project_id")

    @property
    def service_account_email(self) -> str | None:
        """Get the service account email (service account only).

        Returns:
            The service account email, or None for OAuth credentials.
        """
        if self._credential_type == CredentialType.OAUTH:
            return None

        info = get_service_account_info(self._credentials_path)
        return info.get("client_email")

    @property
    def scopes(self) -> list[str]:
        """Get the list of OAuth scopes being used."""
        return self._scopes.copy()
    
    @property
    def user_id(self) -> str | None:
        """Get the user ID for this service instance.
        
        Returns None for legacy single-user mode or service accounts without impersonation.
        """
        return self._user_id

    @property
    def oauth_redirect_uri(self) -> str:
        """Get the OAuth redirect URI (for Google Cloud Console configuration)."""
        return f"http://localhost:{self._oauth_port}/"

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _ensure_authenticated(self) -> None:
        """Ensure we are authenticated before building services."""
        if self._credentials is None:
            self.authenticate()

    def _ensure_service_enabled(self, service_name: ServiceName) -> None:
        """Raise an error if the service was not enabled at initialization."""
        if service_name not in self._enabled_services:
            raise ServiceNotEnabledError(service_name, self._enabled_services)

    def _build_service(self, service_name: ServiceName):
        """Build a Google API service resource."""
        self._ensure_authenticated()
        config = SERVICE_REGISTRY[service_name]
        resource = build(
            config.api_name,
            config.api_version,
            credentials=self._credentials,
            **config.build_kwargs,
        )
        # Return resource wrapped in service class (which takes retry_config)
        return resource

    def _clear_service_cache(self) -> None:
        """Clear all cached service instances."""
        for service_name in SERVICE_REGISTRY.keys():
            try:
                delattr(self, service_name)
            except AttributeError:
                pass

    # =========================================================================
    # Service Properties
    # =========================================================================

    @cached_property
    def calendar(self) -> CalendarService:
        """Access the Google Calendar API."""
        self._ensure_service_enabled("calendar")
        return CalendarService(
            self._build_service("calendar"),
            retry_config=self._retry_config,
        )

    @cached_property
    def docs(self) -> DocsService:
        """Access the Google Docs API."""
        self._ensure_service_enabled("docs")
        return DocsService(
            self._build_service("docs"),
            retry_config=self._retry_config,
        )

    @cached_property
    def drive(self) -> DriveService:
        """Access the Google Drive API."""
        self._ensure_service_enabled("drive")
        return DriveService(
            self._build_service("drive"),
            retry_config=self._retry_config,
        )

    @cached_property
    def forms(self) -> FormsService:
        """Access the Google Forms API."""
        self._ensure_service_enabled("forms")
        return FormsService(
            self._build_service("forms"),
            retry_config=self._retry_config,
        )

    @cached_property
    def gmail(self) -> GmailService:
        """Access the Gmail API."""
        self._ensure_service_enabled("gmail")
        return GmailService(
            self._build_service("gmail"),
            retry_config=self._retry_config,
        )

    @cached_property
    def meet(self) -> MeetService:
        """Access the Google Meet API."""
        self._ensure_service_enabled("meet")
        return MeetService(
            self._build_service("meet"),
            retry_config=self._retry_config,
        )

    @cached_property
    def sheets(self) -> SheetsService:
        """Access the Google Sheets API."""
        self._ensure_service_enabled("sheets")
        return SheetsService(
            self._build_service("sheets"),
            retry_config=self._retry_config,
        )

    @property
    def enabled_services(self) -> list[ServiceName]:
        """List of services enabled for this instance."""
        return self._enabled_services.copy()

    @property
    def credential_type(self) -> CredentialType:
        """The type of credentials being used."""
        return self._credential_type
