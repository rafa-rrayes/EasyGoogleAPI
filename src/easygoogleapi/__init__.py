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
"""

from collections.abc import Sequence
from datetime import datetime
from functools import cached_property
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from ._auth import (
    delete_token,
    detect_credential_type,
    exchange_code,
    get_auth_url,
    get_oauth_credentials,
    get_service_account_credentials,
    get_service_account_info,
    load_token,
    refresh_credentials,
    revoke_credentials,
    save_token,
)
from ._config import SERVICE_REGISTRY, get_scopes_for_services
from ._exceptions import (
    APIError,
    AuthenticationError,
    EasyGoogleAPIError,
    InvalidCredentialsError,
    ServiceNotEnabledError,
    TokenExpiredError,
)
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
    # Exceptions
    "EasyGoogleAPIError",
    "AuthenticationError",
    "InvalidCredentialsError",
    "TokenExpiredError",
    "ServiceNotEnabledError",
    "APIError",
]

__version__ = "0.1.0"


class GoogleService:
    """Main entry point for EasyGoogleAPI.

    Handles authentication and provides access to Google API services
    through lazy-loaded properties.

    Args:
        credentials_path: Path to the credentials JSON file (OAuth or service account).
        services: List of services to enable (e.g., ['calendar', 'drive', 'gmail']).
        token_path: Optional custom path for storing OAuth tokens.
                   Defaults to same directory as credentials with '_token.pickle' suffix.
        auto_auth: If True (default), authenticate immediately. If False, delay until
                   authenticate() is called or a service is accessed.
        oauth_port: Port for OAuth callback server (default: 8080). The redirect URI
                   will be http://localhost:{port}/

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
        auto_auth: bool = True,
        oauth_port: int = 8080,
    ):
        self._credentials_path = Path(credentials_path).expanduser().resolve()
        self._enabled_services: list[ServiceName] = list(services)
        self._credentials = None
        self._oauth_flow: InstalledAppFlow | None = None
        self._oauth_port = oauth_port

        # Validate services
        invalid = set(services) - set(SERVICE_REGISTRY.keys())
        if invalid:
            raise ValueError(
                f"Unknown services: {invalid}. "
                f"Valid services: {list(SERVICE_REGISTRY.keys())}"
            )

        # Determine token path
        if token_path:
            self._token_path = Path(token_path).expanduser().resolve()
        else:
            # Default: credentials.json -> credentials_token.pickle
            self._token_path = self._credentials_path.with_name(
                self._credentials_path.stem + "_token.pickle"
            )

        # Get combined scopes and detect credential type
        self._scopes = get_scopes_for_services(self._enabled_services)
        self._credential_type = detect_credential_type(self._credentials_path)

        if auto_auth:
            self.authenticate()

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
            self._credentials = get_oauth_credentials(
                self._credentials_path,
                self._token_path,
                self._scopes,
                open_browser=open_browser,
                port=port or self._oauth_port,
            )
        else:
            self._credentials = get_service_account_credentials(
                self._credentials_path,
                self._scopes,
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
        save_token(self._token_path, self._credentials)
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
        delete_token(self._token_path)
        self._credentials = None

        # Clear cached services
        self._clear_service_cache()

        return success

    def logout(self) -> bool:
        """Delete stored token without revoking (local logout only).

        Returns:
            True if token file was deleted.
        """
        if self._credential_type == CredentialType.SERVICE_ACCOUNT:
            raise AuthenticationError(
                "logout() is only available for OAuth credentials"
            )

        deleted = delete_token(self._token_path)
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
        return build(
            config.api_name,
            config.api_version,
            credentials=self._credentials,
            **config.build_kwargs,
        )

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
        return CalendarService(self._build_service("calendar"))

    @cached_property
    def docs(self) -> DocsService:
        """Access the Google Docs API."""
        self._ensure_service_enabled("docs")
        return DocsService(self._build_service("docs"))

    @cached_property
    def drive(self) -> DriveService:
        """Access the Google Drive API."""
        self._ensure_service_enabled("drive")
        return DriveService(self._build_service("drive"))

    @cached_property
    def forms(self) -> FormsService:
        """Access the Google Forms API."""
        self._ensure_service_enabled("forms")
        return FormsService(self._build_service("forms"))

    @cached_property
    def gmail(self) -> GmailService:
        """Access the Gmail API."""
        self._ensure_service_enabled("gmail")
        return GmailService(self._build_service("gmail"))

    @cached_property
    def meet(self) -> MeetService:
        """Access the Google Meet API."""
        self._ensure_service_enabled("meet")
        return MeetService(self._build_service("meet"))

    @cached_property
    def sheets(self) -> SheetsService:
        """Access the Google Sheets API."""
        self._ensure_service_enabled("sheets")
        return SheetsService(self._build_service("sheets"))

    @property
    def enabled_services(self) -> list[ServiceName]:
        """List of services enabled for this instance."""
        return self._enabled_services.copy()

    @property
    def credential_type(self) -> CredentialType:
        """The type of credentials being used."""
        return self._credential_type
