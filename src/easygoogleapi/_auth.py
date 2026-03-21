"""Authentication handling for Google APIs."""

import json
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import (
    Flow,
    InstalledAppFlow,
)

from ._exceptions import AuthenticationError, InvalidCredentialsError
from ._token_store import TokenStore
from ._types import CredentialType

# Default OAuth URIs used when normalizing flat client_config dicts
_DEFAULT_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
_DEFAULT_TOKEN_URI = "https://oauth2.googleapis.com/token"


def normalize_client_config(config: dict[str, Any]) -> dict[str, Any]:
    """Normalize a client config dict to the canonical Google format.

    Accepts either the standard Google format (``{"web": {...}}`` or
    ``{"installed": {...}}``) or a flat shorthand
    (``{"client_id": "...", "client_secret": "..."}``) and normalizes
    the shorthand to ``{"web": {...}}``.

    Args:
        config: Client configuration dictionary.

    Returns:
        Normalized config in Google's standard format.

    Raises:
        InvalidCredentialsError: If the dict doesn't contain the required keys.
    """
    if "web" in config or "installed" in config:
        return config

    # Service-account dicts are not client configs
    if config.get("type") == "service_account":
        return config

    # Flat shorthand: requires at least client_id + client_secret
    if "client_id" in config and "client_secret" in config:
        return {
            "web": {
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "auth_uri": config.get("auth_uri", _DEFAULT_AUTH_URI),
                "token_uri": config.get("token_uri", _DEFAULT_TOKEN_URI),
            }
        }

    raise InvalidCredentialsError(
        "client_config must contain 'web', 'installed', or "
        "'client_id'/'client_secret' keys."
    )


def detect_credential_type(credentials: Path | dict[str, Any]) -> CredentialType:
    """Detect whether credentials are OAuth or service account.

    Args:
        credentials: Path to a credentials JSON file, or an in-memory dict.

    Returns:
        The detected credential type.

    Raises:
        InvalidCredentialsError: If the credential format is unrecognized.
    """
    if isinstance(credentials, dict):
        data = normalize_client_config(credentials) if credentials else credentials
    else:
        try:
            with open(credentials) as f:
                data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            raise InvalidCredentialsError(
                f"Cannot read credentials file: {e}"
            ) from e

    if data.get("type") == "service_account":
        return CredentialType.SERVICE_ACCOUNT
    elif "installed" in data or "web" in data:
        return CredentialType.OAUTH
    else:
        source = str(credentials) if isinstance(credentials, Path) else "<dict>"
        raise InvalidCredentialsError(
            f"Unknown credential format in {source}. "
            "Expected OAuth client credentials or service account JSON."
        )


# Credential <-> Dict conversion for token store


def credentials_to_dict(credentials: Credentials) -> dict[str, Any]:
    """Convert Credentials object to a dictionary for storage."""
    return {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
        "expiry": credentials.expiry.isoformat() if credentials.expiry else None,
    }


def dict_to_credentials(token_data: dict[str, Any]) -> Credentials:
    """Convert dictionary to Credentials object."""
    creds = Credentials(  # type: ignore[no-untyped-call]
        token=token_data.get("token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri"),
        client_id=token_data.get("client_id"),
        client_secret=token_data.get("client_secret"),
        scopes=token_data.get("scopes"),
    )

    expiry_str = token_data.get("expiry")
    if expiry_str:
        try:
            creds.expiry = datetime.fromisoformat(expiry_str)
        except (ValueError, TypeError):
            pass

    return creds


# Token store integration


def load_token_from_store(token_store: TokenStore, user_id: str) -> Credentials | None:
    """Load OAuth token from token store."""
    token_data = token_store.get(user_id)
    if token_data:
        return dict_to_credentials(token_data)
    return None


def save_token_to_store(
    token_store: TokenStore,
    user_id: str,
    credentials: Credentials,
) -> None:
    """Save OAuth token to token store."""
    token_data = credentials_to_dict(credentials)
    token_store.save(user_id, token_data)


def delete_token_from_store(token_store: TokenStore, user_id: str) -> bool:
    """Delete OAuth token from token store."""
    return token_store.delete(user_id)


# OAuth flow functions


def _is_web_config(config: Path | dict[str, Any]) -> bool:
    """Return True if the config describes a web OAuth client."""
    if isinstance(config, dict):
        normalized = normalize_client_config(config) if config else config
        return "web" in normalized
    # File-based: read and check
    try:
        with open(config) as f:
            data = json.load(f)
        return "web" in data
    except Exception:
        return False


def create_oauth_flow(
    credentials: Path | dict[str, Any],
    scopes: list[str],
    redirect_uri: str | None = None,
    pkce: bool = True,
) -> Flow | InstalledAppFlow:
    """Create an OAuth flow without running it.

    Args:
        credentials: Path to client secrets file or in-memory client config dict.
        scopes: OAuth scopes to request.
        redirect_uri: Optional redirect URI.
        pkce: If True (default), enable PKCE (RFC 7636) for the OAuth flow.

    Returns:
        A ``Flow`` (for web configs) or ``InstalledAppFlow`` (for installed configs).
    """
    if isinstance(credentials, dict):
        config = normalize_client_config(credentials)
        if "web" in config:
            flow = Flow.from_client_config(config, scopes)
        else:
            flow = InstalledAppFlow.from_client_config(config, scopes)
    else:
        if _is_web_config(credentials):
            flow = Flow.from_client_secrets_file(str(credentials), scopes)
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials), scopes
            )
    if redirect_uri:
        flow.redirect_uri = redirect_uri

    # Enable PKCE (RFC 7636) — the Flow class handles code_verifier
    # generation and code_challenge computation automatically.
    if pkce:
        flow.autogenerate_code_verifier = True

    return flow


def get_auth_url(
    credentials: Path | dict[str, Any],
    scopes: list[str],
    redirect_uri: str = "urn:ietf:wg:oauth:2.0:oob",
) -> tuple[str, Flow | InstalledAppFlow, str]:
    """Get OAuth authorization URL without opening browser.

    PKCE is enabled by default for all OAuth flows.

    Returns:
        Tuple of (authorization_url, flow, state). The flow is needed for
        ``exchange_code()`` and the state for CSRF verification.
    """
    flow = create_oauth_flow(credentials, scopes, redirect_uri)
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return auth_url, flow, state


def exchange_code(
    flow: Flow | InstalledAppFlow,
    code: str,
) -> Credentials:
    """Exchange authorization code for credentials.

    If PKCE was enabled during flow creation, the code_verifier is
    automatically included in the token exchange request.

    Persistence is the caller's responsibility.

    Args:
        flow: The OAuth flow from get_auth_url().
        code: The authorization code from the OAuth callback.

    Returns:
        The OAuth credentials.
    """
    flow.fetch_token(code=code)
    creds: Credentials = flow.credentials
    return creds


def refresh_credentials(credentials: Credentials) -> Credentials:
    """Refresh OAuth credentials."""
    if not credentials.refresh_token:
        raise AuthenticationError("No refresh token available")
    try:
        credentials.refresh(Request())
        return credentials
    except Exception as e:
        raise AuthenticationError(f"Failed to refresh token: {e}") from e


def revoke_credentials(credentials: Credentials) -> bool:
    """Revoke OAuth credentials.

    Returns:
        True if revocation was successful, False otherwise.
    """
    if not credentials.token:
        return False

    try:
        params = urllib.parse.urlencode({"token": credentials.token})
        url = f"https://oauth2.googleapis.com/revoke?{params}"
        req = urllib.request.Request(
            url,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(req) as response:
            return bool(response.status == 200)
    except Exception:
        return False


def get_oauth_credentials_from_store(
    credentials: Path | dict[str, Any],
    token_store: TokenStore,
    user_id: str,
    scopes: list[str],
    open_browser: bool = True,
    port: int = 8080,
) -> Credentials:
    """Get OAuth credentials using a token store, refreshing or creating as needed.

    PKCE is enabled by default for all new OAuth flows.

    Args:
        credentials: Path to OAuth client secrets file, or in-memory config dict.
        token_store: Token store for loading/saving tokens.
        user_id: User identifier.
        scopes: List of OAuth scopes.
        open_browser: If True, opens browser for OAuth flow.
        port: Port for the local OAuth callback server (default: 8080).

    Returns:
        Valid OAuth credentials.

    Raises:
        AuthenticationError: If authentication fails.
    """
    creds = load_token_from_store(token_store, user_id)

    if creds and creds.expired and creds.refresh_token:
        creds = refresh_credentials(creds)
        save_token_to_store(token_store, user_id, creds)
    elif not creds or not creds.valid:
        # For web configs we never auto-open a browser
        is_web = _is_web_config(credentials)
        if is_web or not open_browser:
            raise AuthenticationError(
                "No valid credentials. "
                "Use get_auth_url() and exchange_code() for the OAuth flow."
            )
        if isinstance(credentials, dict):
            config = normalize_client_config(credentials)
            flow = InstalledAppFlow.from_client_config(config, scopes)
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials), scopes
            )
        # Enable PKCE for the installed app flow
        flow.autogenerate_code_verifier = True
        creds = flow.run_local_server(port=port)
        save_token_to_store(token_store, user_id, creds)

    return creds


def get_service_account_credentials(
    credentials_path: Path | None,
    scopes: list[str],
    subject: str | None = None,
) -> service_account.Credentials:
    """Get service account credentials."""
    if credentials_path is None:
        raise AuthenticationError(
            "credentials_path is required for service account authentication"
        )
    try:
        creds = service_account.Credentials.from_service_account_file(  # type: ignore[no-untyped-call]
            str(credentials_path), scopes=scopes
        )
        if subject:
            creds = creds.with_subject(subject)
        result: service_account.Credentials = creds
        return result
    except Exception as e:
        raise AuthenticationError(
            f"Failed to load service account credentials: {e}"
        ) from e


def get_service_account_info(credentials_path: Path | None) -> dict[str, Any]:
    """Get service account info from credentials file."""
    if credentials_path is None:
        raise InvalidCredentialsError("No credentials path provided")
    try:
        with open(credentials_path) as f:
            data: dict[str, Any] = json.load(f)
        return data
    except Exception as e:
        raise InvalidCredentialsError(
            f"Cannot read credentials file: {e}"
        ) from e
