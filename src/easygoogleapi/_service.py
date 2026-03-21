"""GoogleService — main entry point for EasyGoogleAPI."""

from collections.abc import Callable, Sequence
from datetime import datetime
from functools import cached_property
from pathlib import Path
from typing import Any

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow, InstalledAppFlow
from googleapiclient.discovery import build

from ._auth import (
    delete_token_from_store,
    detect_credential_type,
    exchange_code as _exchange_code,
    get_auth_url as _get_auth_url,
    get_oauth_credentials_from_store,
    get_service_account_credentials,
    get_service_account_info,
    normalize_client_config,
    refresh_credentials,
    revoke_credentials,
    save_token_to_store,
)
from ._base import RetryConfig
from ._config import SERVICE_REGISTRY
from ._middleware import MiddlewareChain
from ._exceptions import (
    AuthenticationError,
    ServiceNotEnabledError,
    TokenRevokedError,
)
from ._token_store import FileTokenStore, InMemoryTokenStore, TokenStore
from ._types import SCOPE_PRESETS, CredentialType, ServiceName
from .calendar import CalendarService
from .docs import DocsService
from .drive import DriveService
from .forms import FormsService
from .gmail import GmailService
from .meet import MeetService
from .sheets import SheetsService


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
            automatically from the enabled services using ``scope_preset``.
        scope_preset: Scope preset to use when ``scopes`` is ``None``.
            ``"full"`` (default) uses full-access scopes.
            ``"readonly"`` uses read-only scopes where available.
        token_store: Pluggable token storage backend. If not provided, uses
            JSON file-based storage in the same directory as credentials.
        user_id: User identifier for multi-user scenarios. Auto-generated
            from credentials path if not provided.
        auto_auth: If ``True`` (default), authenticate immediately. If ``False``,
            delay until ``authenticate()`` is called or a service is accessed.
        oauth_port: Port for OAuth callback server (default: 8080).
        retry_config: Configuration for retry behavior. Uses defaults if None.
        middleware: Optional ``MiddlewareChain`` with before/after request hooks.
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
        token_store: TokenStore | None = None,
        user_id: str | None = None,
        auto_auth: bool = True,
        oauth_port: int = 8080,
        retry_config: RetryConfig | None = None,
        middleware: MiddlewareChain | None = None,
        *,
        client_config: dict[str, Any] | None = None,
        scopes: list[str] | dict[str, list[str]] | None = None,
        scope_preset: str = "full",
        on_token_refresh: Callable[[Credentials], None] | None = None,
        on_token_expired: Callable[[TokenRevokedError], None] | None = None,
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
            self._client_config: dict[str, Any] | None = None
        else:
            self._credentials_path = None
            self._client_config = normalize_client_config(client_config)  # type: ignore[arg-type]

        self._enabled_services: list[ServiceName] = list(services)
        self._credentials: Credentials | None = None
        self._oauth_flow: Flow | InstalledAppFlow | None = None
        self._oauth_state: str | None = None
        self._oauth_port = oauth_port
        self._retry_config = retry_config or RetryConfig()
        self._middleware = middleware
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
        elif self._credentials_path is not None:
            self._token_store = FileTokenStore(
                directory=self._credentials_path.parent
            )
            self._user_id = user_id or self._credentials_path.stem
        else:
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
            if scope_preset not in SCOPE_PRESETS:
                raise ValueError(
                    f"Unknown scope_preset: '{scope_preset}'. "
                    f"Valid presets: {list(SCOPE_PRESETS.keys())}"
                )
            preset = SCOPE_PRESETS[scope_preset]
            scope_set: set[str] = set()
            for svc in self._enabled_services:
                if svc in preset:
                    scope_set.update(preset[svc])
                else:
                    scope_set.update(SERVICE_REGISTRY[svc].scopes)
            self._scopes = list(scope_set)

        # ------------------------------------------------------------------
        # Credential type detection
        # ------------------------------------------------------------------
        cred_source = self._credentials_path or self._client_config
        self._credential_type = detect_credential_type(cred_source)  # type: ignore[arg-type]

        if auto_auth:
            self.authenticate()

    # =========================================================================
    # Factory Methods
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
        client_config: dict[str, Any] | None = None,
        scopes: list[str] | dict[str, list[str]] | None = None,
        scope_preset: str = "full",
        on_token_refresh: Callable[[Credentials], None] | None = None,
        on_token_expired: Callable[[TokenRevokedError], None] | None = None,
    ) -> "GoogleService":
        """Create GoogleService for a specific user with OAuth."""
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
            scope_preset=scope_preset,
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
        """Create GoogleService using a service account."""
        instance = cls(
            credentials_path=credentials_path,
            services=services,
            auto_auth=False,
            retry_config=retry_config,
        )

        instance._impersonate_user = impersonate_user  # type: ignore[attr-defined]
        instance._credentials = get_service_account_credentials(
            instance._credentials_path,
            instance._scopes,
            subject=impersonate_user,
        )

        return instance

    # =========================================================================
    # Authentication Control
    # =========================================================================

    def authenticate(self, open_browser: bool = True, port: int | None = None) -> bool:
        """Perform authentication."""
        cred_source = self._credentials_path or self._client_config

        if self._credential_type == CredentialType.OAUTH:
            self._credentials = get_oauth_credentials_from_store(
                cred_source,  # type: ignore[arg-type]
                self._token_store,
                self._user_id,  # type: ignore[arg-type]
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

        PKCE is enabled by default. After the user authorizes, call
        ``exchange_code()`` with the authorization code.

        Returns:
            Tuple of ``(authorization_url, state)``.
        """
        if self._credential_type == CredentialType.SERVICE_ACCOUNT:
            raise AuthenticationError(
                "get_auth_url() is only available for OAuth credentials"
            )

        uri = redirect_uri or "urn:ietf:wg:oauth:2.0:oob"
        cred_source = self._credentials_path or self._client_config
        auth_url, self._oauth_flow, state = _get_auth_url(
            cred_source, self._scopes, uri  # type: ignore[arg-type]
        )
        self._oauth_state = state
        return auth_url, state

    def exchange_code(self, code: str) -> bool:
        """Exchange authorization code for credentials."""
        if self._oauth_flow is None:
            raise AuthenticationError(
                "No active OAuth flow. Call get_auth_url() first."
            )

        self._credentials = _exchange_code(self._oauth_flow, code)
        save_token_to_store(self._token_store, self._user_id, self._credentials)  # type: ignore[arg-type]
        self._oauth_flow = None
        self._oauth_state = None
        return True

    def refresh_token(self) -> bool:
        """Force refresh the OAuth token."""
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

        save_token_to_store(self._token_store, self._user_id, self._credentials)  # type: ignore[arg-type]
        if self._on_token_refresh:
            self._on_token_refresh(self._credentials)
        return True

    def revoke(self) -> bool:
        """Revoke the current OAuth token and delete stored token."""
        if self._credential_type == CredentialType.SERVICE_ACCOUNT:
            raise AuthenticationError(
                "revoke() is only available for OAuth credentials"
            )
        if self._credentials is None:
            return False

        success = revoke_credentials(self._credentials)
        delete_token_from_store(self._token_store, self._user_id)  # type: ignore[arg-type]
        self._credentials = None
        self._clear_service_cache()
        return success

    def logout(self) -> bool:
        """Delete stored token without revoking (local logout only)."""
        if self._credential_type == CredentialType.SERVICE_ACCOUNT:
            raise AuthenticationError(
                "logout() is only available for OAuth credentials"
            )
        deleted = delete_token_from_store(self._token_store, self._user_id)  # type: ignore[arg-type]
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
        """Get the authenticated user's email."""
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
        """Get the OAuth redirect URI."""
        return f"http://localhost:{self._oauth_port}/"

    @property
    def enabled_services(self) -> list[ServiceName]:
        """List of services enabled for this instance."""
        return self._enabled_services.copy()

    @property
    def credential_type(self) -> CredentialType:
        """The type of credentials being used."""
        return self._credential_type

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _ensure_authenticated(self) -> None:
        """Ensure authenticated, handling transparent token refresh."""
        if self._credentials is None:
            self.authenticate()
            return

        if (
            self._credential_type == CredentialType.OAUTH
            and self._credentials.expired
            and self._credentials.refresh_token
        ):
            try:
                self._credentials = refresh_credentials(self._credentials)
                save_token_to_store(
                    self._token_store, self._user_id, self._credentials  # type: ignore[arg-type]
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

    def _build_service(self, service_name: ServiceName) -> Any:
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
            middleware=self._middleware,
        )

    @cached_property
    def docs(self) -> DocsService:
        """Access the Google Docs API."""
        self._ensure_service_enabled("docs")
        return DocsService(
            self._build_service("docs"),
            retry_config=self._retry_config,
            middleware=self._middleware,
        )

    @cached_property
    def drive(self) -> DriveService:
        """Access the Google Drive API."""
        self._ensure_service_enabled("drive")
        return DriveService(
            self._build_service("drive"),
            retry_config=self._retry_config,
            middleware=self._middleware,
        )

    @cached_property
    def forms(self) -> FormsService:
        """Access the Google Forms API."""
        self._ensure_service_enabled("forms")
        return FormsService(
            self._build_service("forms"),
            retry_config=self._retry_config,
            middleware=self._middleware,
        )

    @cached_property
    def gmail(self) -> GmailService:
        """Access the Gmail API."""
        self._ensure_service_enabled("gmail")
        return GmailService(
            self._build_service("gmail"),
            retry_config=self._retry_config,
            middleware=self._middleware,
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
            middleware=self._middleware,
        )
