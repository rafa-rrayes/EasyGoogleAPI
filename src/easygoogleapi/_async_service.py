"""AsyncGoogleService — async entry point for EasyGoogleAPI."""

from collections.abc import Callable, Sequence
from functools import cached_property
from pathlib import Path
from types import TracebackType
from typing import Any

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow, InstalledAppFlow
from googleapiclient.discovery import build

from ._async_base import AsyncBaseService
from ._auth import (
    delete_token_from_store,
    detect_credential_type,
    get_auth_url as _get_auth_url,
    get_oauth_credentials_from_store,
    get_service_account_credentials,
    normalize_client_config,
    save_token_to_store,
)
from ._base import RetryConfig
from ._config import SERVICE_REGISTRY
from ._exceptions import (
    AuthenticationError,
    ServiceNotEnabledError,
    TokenRevokedError,
)
from ._token_store import FileTokenStore, InMemoryTokenStore, TokenStore
from ._types import SCOPE_PRESETS, CredentialType, ServiceName

# Dynamically create async service classes that mirror sync ones
# but use AsyncBaseService for _execute_request
from .calendar.service import CalendarService as _SyncCalendar
from .docs.service import DocsService as _SyncDocs
from .drive.service import DriveService as _SyncDrive
from .forms.service import FormsService as _SyncForms
from .gmail.service import GmailService as _SyncGmail
from .sheets.service import SheetsService as _SyncSheets


def _make_async_method(sync_method: Any) -> Any:
    """Create an async wrapper for a sync service method."""
    import asyncio
    import functools

    @functools.wraps(sync_method)
    async def async_method(self: Any, *args: Any, **kwargs: Any) -> Any:
        return await asyncio.to_thread(sync_method, self, *args, **kwargs)

    return async_method


def _create_async_service_class(
    sync_class: type, name: str
) -> type:
    """Create an async service class from a sync one.

    The async class inherits from the sync class but overrides
    _execute_request to use asyncio.to_thread(). All public methods
    that call _execute_request will thus be async-compatible when
    called via the async wrapper.
    """
    # For the async service, we actually keep the sync methods
    # but wrap them with asyncio.to_thread at call time.
    # This is simpler and maintains all the logic.
    attrs: dict[str, Any] = {}

    for attr_name in dir(sync_class):
        if attr_name.startswith("_"):
            continue
        attr = getattr(sync_class, attr_name)
        if callable(attr) and not isinstance(attr, property):
            attrs[attr_name] = _make_async_method(attr)

    async_cls = type(name, (sync_class,), attrs)
    return async_cls


AsyncCalendarService = _create_async_service_class(_SyncCalendar, "AsyncCalendarService")
AsyncDocsService = _create_async_service_class(_SyncDocs, "AsyncDocsService")
AsyncDriveService = _create_async_service_class(_SyncDrive, "AsyncDriveService")
AsyncFormsService = _create_async_service_class(_SyncForms, "AsyncFormsService")
AsyncGmailService = _create_async_service_class(_SyncGmail, "AsyncGmailService")
AsyncSheetsService = _create_async_service_class(_SyncSheets, "AsyncSheetsService")


class AsyncGoogleService:
    """Async entry point for EasyGoogleAPI.

    Usage::

        async with AsyncGoogleService(
            credentials_path="credentials.json",
            services=["drive"]
        ) as google:
            files = await google.drive.list_files_page()
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
        *,
        client_config: dict[str, Any] | None = None,
        scopes: list[str] | dict[str, list[str]] | None = None,
        scope_preset: str = "full",
        on_token_refresh: Callable[[Credentials], None] | None = None,
        on_token_expired: Callable[[TokenRevokedError], None] | None = None,
    ):
        if credentials_path is not None and client_config is not None:
            raise ValueError(
                "Cannot specify both 'credentials_path' and 'client_config'."
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
        self._oauth_port = oauth_port
        self._retry_config = retry_config or RetryConfig()
        self._on_token_refresh = on_token_refresh
        self._on_token_expired = on_token_expired

        invalid = set(services) - set(SERVICE_REGISTRY.keys())
        if invalid:
            raise ValueError(f"Unknown services: {invalid}")

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

        if scopes is not None:
            if isinstance(scopes, dict):
                combined: set[str] = set()
                for svc_scopes in scopes.values():
                    combined.update(svc_scopes)
                self._scopes = list(combined)
            else:
                self._scopes = list(scopes)
        else:
            if scope_preset not in SCOPE_PRESETS:
                raise ValueError(f"Unknown scope_preset: '{scope_preset}'")
            preset = SCOPE_PRESETS[scope_preset]
            scope_set: set[str] = set()
            for svc in self._enabled_services:
                if svc in preset:
                    scope_set.update(preset[svc])
                else:
                    scope_set.update(SERVICE_REGISTRY[svc].scopes)
            self._scopes = list(scope_set)

        cred_source = self._credentials_path or self._client_config
        self._credential_type = detect_credential_type(cred_source)  # type: ignore[arg-type]

        if auto_auth:
            self.authenticate()

    def authenticate(self, open_browser: bool = True, port: int | None = None) -> bool:
        """Perform authentication (synchronous — called during init)."""
        cred_source = self._credentials_path or self._client_config
        if self._credential_type == CredentialType.OAUTH:
            self._credentials = get_oauth_credentials_from_store(
                cred_source, self._token_store, self._user_id,  # type: ignore[arg-type]
                self._scopes, open_browser=open_browser,
                port=port or self._oauth_port,
            )
        else:
            subject = getattr(self, "_impersonate_user", None)
            self._credentials = get_service_account_credentials(
                self._credentials_path, self._scopes, subject=subject,
            )
        return True

    async def __aenter__(self) -> "AsyncGoogleService":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        pass

    def _ensure_authenticated(self) -> None:
        if self._credentials is None:
            self.authenticate()

    def _build_service(self, service_name: ServiceName) -> Any:
        self._ensure_authenticated()
        config = SERVICE_REGISTRY[service_name]
        return build(
            config.api_name, config.api_version,
            credentials=self._credentials, **config.build_kwargs,
        )

    @cached_property
    def calendar(self) -> Any:
        """Access the async Google Calendar API."""
        if "calendar" not in self._enabled_services:
            raise ServiceNotEnabledError("calendar", self._enabled_services)
        return AsyncCalendarService(
            self._build_service("calendar"), retry_config=self._retry_config,
        )

    @cached_property
    def docs(self) -> Any:
        """Access the async Google Docs API."""
        if "docs" not in self._enabled_services:
            raise ServiceNotEnabledError("docs", self._enabled_services)
        return AsyncDocsService(
            self._build_service("docs"), retry_config=self._retry_config,
        )

    @cached_property
    def drive(self) -> Any:
        """Access the async Google Drive API."""
        if "drive" not in self._enabled_services:
            raise ServiceNotEnabledError("drive", self._enabled_services)
        return AsyncDriveService(
            self._build_service("drive"), retry_config=self._retry_config,
        )

    @cached_property
    def forms(self) -> Any:
        """Access the async Google Forms API."""
        if "forms" not in self._enabled_services:
            raise ServiceNotEnabledError("forms", self._enabled_services)
        return AsyncFormsService(
            self._build_service("forms"), retry_config=self._retry_config,
        )

    @cached_property
    def gmail(self) -> Any:
        """Access the async Gmail API."""
        if "gmail" not in self._enabled_services:
            raise ServiceNotEnabledError("gmail", self._enabled_services)
        return AsyncGmailService(
            self._build_service("gmail"), retry_config=self._retry_config,
        )

    @cached_property
    def sheets(self) -> Any:
        """Access the async Google Sheets API."""
        if "sheets" not in self._enabled_services:
            raise ServiceNotEnabledError("sheets", self._enabled_services)
        return AsyncSheetsService(
            self._build_service("sheets"), retry_config=self._retry_config,
        )
