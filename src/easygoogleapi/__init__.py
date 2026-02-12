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

    google = GoogleService.for_user(
        user_id="user_123",
        token_store=my_token_store,
        credentials_path="oauth_credentials.json",
        services=["calendar", "gmail"]
    )

In-memory client config (no files on disk):
    from easygoogleapi import GoogleService

    google = GoogleService(
        client_config={"web": {"client_id": "...", "client_secret": "..."}},
        services=["drive"],
        token_store=my_store,
        user_id="user_123",
        auto_auth=False,
    )
"""

from collections.abc import Callable, Sequence
from datetime import datetime
from functools import cached_property
from pathlib import Path

from google.auth.exceptions import RefreshError
from google_auth_oauthlib.flow import Flow, InstalledAppFlow
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
    normalize_client_config,
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
    TokenRevokedError,
    TransientError,
)
from ._token_store import FileTokenStore, InMemoryTokenStore, JSONFileTokenStore, TokenStore
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
    "DjangoModelTokenStore",
    # Exceptions
    "EasyGoogleAPIError",
    "AuthenticationError",
    "InvalidCredentialsError",
    "TokenExpiredError",
    "TokenRevokedError",
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

__version__ = "1.0.0"


class GoogleService:
    """Main entry point for EasyGoogleAPI.

    Handles authentication and provides access to Google API services
    through lazy-loaded properties.

    Simple usage:
        google = GoogleService(
            credentials_path="credentials.json",
            services=["calendar", "drive"]
        )

    In-memory client config (no files on disk):
        google = GoogleService(
            client_config={"web": {"client_id": "...", "client_secret": "..."}},
            services=["drive"],
            token_store=my_store,
            user_id="user_123",
            auto_auth=False,
        )

    Multi-user applications:
        google = GoogleService.for_user(
            user_id="user_123",
            token_store=DatabaseTokenStore(session),
            credentials_path="oauth_client.json",
            services=["calendar"]
        )

    Service account with domain delegation:
        google = GoogleService.for_service_account(
            credentials_path="service_account.json",
            services=["drive"],
            impersonate_user="user@domain.com"
        )

    Args:
        credentials_path: Path to the credentials JSON file (OAuth or service account).
            Mutually exclusive with ``client_config``.
        client_config: In-memory OAuth client configuration dict. Accepts the
            standard Google format (``{"web": {...}}`` / ``{"installed": {...}}``)
            or a flat shorthand ``{"client_id": "...", "client_secret": "..."}``.
            Mutually exclusive with ``credentials_path``.
        services: List of services to enable (e.g., ``['calendar', 'drive', 'gmail']``).
        scopes: Custom OAuth scopes. Can be a flat ``list[str]`` applied to all
            services, or a ``dict[str, list[str]]`` mapping service names to
            per-service scopes. If ``None`` (default), scopes are derived
            automatically from the enabled services.
        token_path: Custom path for storing OAuth tokens. Defaults to same
            directory as credentials with ``_token.pickle`` suffix.
        token_store: Pluggable token storage backend. If not provided, uses
            file-based storage.
        user_id: User identifier for multi-user scenarios. Auto-generated
            from ``token_path`` if not provided.
        auto_auth: If ``True`` (default), authenticate immediately. If ``False``,
            delay until ``authenticate()`` is called or a service is accessed.
        oauth_port: Port for OAuth callback server (default: 8080).
        retry_config: Configuration for retry behavior. Uses defaults if None.
        on_token_refresh: Callback invoked after a token is successfully refreshed.
            Receives the ``Credentials`` object as its only argument.
        on_token_expired: Callback invoked when a refresh token has been revoked
            or is otherwise permanently invalid. Receives the raised
            ``TokenRevokedError`` as its only argument.
    """

    def __init__(
        self,
        credentials_path: str | Path | None = None,
        services: Sequence[ServiceName] = (),
        token_path: str | Path | None = None,
        token_store: TokenStore | None = None,
        user_id: str | None = None,
        auto_auth: bool = True,
        oauth_port: int = 8080,
        retry_config: RetryConfig | None = None,
        *,
        client_config: dict | None = None,
        scopes: list[str] | dict[str, list[str]] | None = None,
        on_token_refresh: Callable | None = None,
        on_token_expired: Callable | None = None,
    ):
        # ------------------------------------------------------------------
        # Credential source validation
        # ------------------------------------------------------------------
        if credentials_path is not None and client_config is not None:
            raise ValueError(
                "Cannot specify both 'credentials_path' and 'client_config'. "
                "Use one or the other."
            )
        if credentials_path is None and client_config is None:
            raise ValueError(
                "One of 'credentials_path' or 'client_config' must be provided."
            )

        if credentials_path is not None:
            self._credentials_path: Path | None = Path(credentials_path).expanduser().resolve()
            self._client_config: dict | None = None
        else:
            self._credentials_path = None
            self._client_config = normalize_client_config(client_config)

        self._enabled_services: list[ServiceName] = list(services)
        self._credentials = None
        self._oauth_flow: Flow | InstalledAppFlow | None = None
        self._oauth_state: str | None = None
        self._oauth_port = oauth_port
        self._retry_config = retry_config or RetryConfig()
        self._on_token_refresh = on_token_refresh
        self._on_token_expired = on_token_expired

        # Validate services
        invalid = set(services) - set(SERVICE_REGISTRY.keys())
        if invalid:
            raise ValueError(
                f"Unknown services: {invalid}. "
                f"Valid services: {list(SERVICE_REGISTRY.keys())}"
            )

        # ------------------------------------------------------------------
        # Token storage setup
        # ------------------------------------------------------------------
        if token_store is not None:
            self._token_store = token_store
            self._user_id = user_id
            if self._user_id is None:
                raise ValueError("user_id must be provided when using token_store")
            self._token_path = None
        elif self._credentials_path is not None:
            # Legacy single-user mode with file-based storage
            if token_path:
                self._token_path = Path(token_path).expanduser().resolve()
            else:
                self._token_path = self._credentials_path.with_name(
                    self._credentials_path.stem + "_token.pickle"
                )
            self._token_store = FileTokenStore(directory=self._token_path.parent)
            self._user_id = user_id or self._token_path.stem
        else:
            # client_config without explicit token_store → in-memory store
            self._token_path = None
            self._token_store = InMemoryTokenStore()
            self._user_id = user_id or "default"

        # ------------------------------------------------------------------
        # Scopes
        # ------------------------------------------------------------------
        if scopes is not None:
            if isinstance(scopes, dict):
                combined: set[str] = set()
                for svc, svc_scopes in scopes.items():
                    combined.update(svc_scopes)
                self._scopes = list(combined)
            else:
                self._scopes = list(scopes)
        else:
            self._scopes = get_scopes_for_services(self._enabled_services)

        # ------------------------------------------------------------------
        # Credential type detection
        # ------------------------------------------------------------------
        cred_source = self._credentials_path or self._client_config
        self._credential_type = detect_credential_type(cred_source)

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
        credentials_path: str | Path | None = None,
        services: Sequence[ServiceName] = (),
        auto_auth: bool = True,
        oauth_port: int = 8080,
        retry_config: RetryConfig | None = None,
        *,
        client_config: dict | None = None,
        scopes: list[str] | dict[str, list[str]] | None = None,
        on_token_refresh: Callable | None = None,
        on_token_expired: Callable | None = None,
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
            client_config: In-memory client config (alternative to credentials_path).
            scopes: Custom OAuth scopes.
            on_token_refresh: Callback after successful token refresh.
            on_token_expired: Callback when refresh token is revoked.

        Returns:
            GoogleService instance configured for the user.
        """
        return cls(
            credentials_path=credentials_path,
            services=services,
            token_store=token_store,
            user_id=user_id,
            auto_auth=auto_auth,
            oauth_port=oauth_port,
            retry_config=retry_config,
            client_config=client_config,
            scopes=scopes,
            on_token_refresh=on_token_refresh,
            on_token_expired=on_token_expired,
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
        """
        instance = cls(
            credentials_path=credentials_path,
            services=services,
            auto_auth=False,
            retry_config=retry_config,
        )

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
        cred_source = self._credentials_path or self._client_config

        if self._credential_type == CredentialType.OAUTH:
            self._credentials = get_oauth_credentials_from_store(
                cred_source,
                self._token_store,
                self._user_id,
                self._scopes,
                open_browser=open_browser,
                port=port or self._oauth_port,
            )
        else:
            subject = getattr(self, "_impersonate_user", None)
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
            return True

        return self._credentials.valid and not self._credentials.expired

    def get_auth_url(self, redirect_uri: str | None = None) -> tuple[str, str]:
        """Get OAuth authorization URL without opening browser.

        Use this for custom OAuth flows where you handle the redirect yourself.
        After the user authorizes, call ``exchange_code()`` with the authorization code.

        Args:
            redirect_uri: Custom redirect URI. Defaults to OOB flow.

        Returns:
            Tuple of ``(authorization_url, state)``. The state value should be
            verified in the OAuth callback for CSRF protection.

        Raises:
            AuthenticationError: If using service account credentials.
        """
        if self._credential_type == CredentialType.SERVICE_ACCOUNT:
            raise AuthenticationError(
                "get_auth_url() is only available for OAuth credentials"
            )

        uri = redirect_uri or "urn:ietf:wg:oauth:2.0:oob"
        cred_source = self._credentials_path or self._client_config
        auth_url, self._oauth_flow, state = get_auth_url(
            cred_source, self._scopes, uri
        )
        self._oauth_state = state
        return auth_url, state

    def exchange_code(self, code: str) -> bool:
        """Exchange authorization code for credentials.

        Use this after ``get_auth_url()`` when the user provides the authorization code.
        The resulting credentials are automatically persisted to the token store.

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

        self._credentials = exchange_code(self._oauth_flow, code)
        # Persist to token store
        save_token_to_store(self._token_store, self._user_id, self._credentials)
        self._oauth_flow = None
        self._oauth_state = None
        return True

    def refresh_token(self) -> bool:
        """Force refresh the OAuth token.

        Returns:
            True if refresh was successful.

        Raises:
            AuthenticationError: If refresh fails or using service account.
            TokenRevokedError: If the refresh token has been revoked.
        """
        if self._credential_type == CredentialType.SERVICE_ACCOUNT:
            raise AuthenticationError(
                "refresh_token() is only available for OAuth credentials"
            )

        if self._credentials is None:
            raise AuthenticationError("Not authenticated")

        try:
            self._credentials = refresh_credentials(self._credentials)
        except AuthenticationError as exc:
            if "invalid_grant" in str(exc):
                revoked = TokenRevokedError()
                if self._on_token_expired:
                    self._on_token_expired(revoked)
                raise revoked from exc
            raise

        save_token_to_store(self._token_store, self._user_id, self._credentials)
        if self._on_token_refresh:
            self._on_token_refresh(self._credentials)
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
        """Get the token expiry datetime (OAuth only)."""
        if self._credentials is None:
            return None
        if self._credential_type == CredentialType.SERVICE_ACCOUNT:
            return None
        return self._credentials.expiry

    @property
    def user_email(self) -> str | None:
        """Get the authenticated user's email (OAuth only)."""
        if self._credentials is None:
            return None

        if self._credential_type == CredentialType.SERVICE_ACCOUNT:
            info = get_service_account_info(self._credentials_path)
            return info.get("client_email")

        if hasattr(self._credentials, "_id_token") and self._credentials._id_token:
            return self._credentials._id_token.get("email")

        return None

    @property
    def project_id(self) -> str | None:
        """Get the project ID (service account only)."""
        if self._credential_type == CredentialType.OAUTH:
            return None
        info = get_service_account_info(self._credentials_path)
        return info.get("project_id")

    @property
    def service_account_email(self) -> str | None:
        """Get the service account email (service account only)."""
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
        """Get the user ID for this service instance."""
        return self._user_id

    @property
    def oauth_redirect_uri(self) -> str:
        """Get the OAuth redirect URI (for Google Cloud Console configuration)."""
        return f"http://localhost:{self._oauth_port}/"

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _ensure_authenticated(self) -> None:
        """Ensure we are authenticated before building services.

        For OAuth credentials this also handles transparent token refresh
        and fires the ``on_token_refresh`` / ``on_token_expired`` callbacks.
        """
        if self._credentials is None:
            self.authenticate()
            return

        # For OAuth, attempt transparent refresh when token is expired
        if (
            self._credential_type == CredentialType.OAUTH
            and self._credentials.expired
            and self._credentials.refresh_token
        ):
            try:
                self._credentials = refresh_credentials(self._credentials)
                save_token_to_store(
                    self._token_store, self._user_id, self._credentials
                )
                if self._on_token_refresh:
                    self._on_token_refresh(self._credentials)
            except AuthenticationError as exc:
                if "invalid_grant" in str(exc):
                    revoked = TokenRevokedError()
                    if self._on_token_expired:
                        self._on_token_expired(revoked)
                    raise revoked from exc
                raise

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
        """Access the Google Meet API (gRPC-based)."""
        self._ensure_service_enabled("meet")
        self._ensure_authenticated()
        return MeetService(credentials=self._credentials)

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
