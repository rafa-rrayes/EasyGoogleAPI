"""Authentication handling for Google APIs."""

import json
import pickle
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from ._exceptions import AuthenticationError, InvalidCredentialsError
from ._token_store import TokenStore
from ._types import CredentialType


def detect_credential_type(credentials_path: Path) -> CredentialType:
    """Detect whether credentials are OAuth or service account."""
    try:
        with open(credentials_path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        raise InvalidCredentialsError(f"Cannot read credentials file: {e}")

    if data.get("type") == "service_account":
        return CredentialType.SERVICE_ACCOUNT
    elif "installed" in data or "web" in data:
        return CredentialType.OAUTH
    else:
        raise InvalidCredentialsError(
            f"Unknown credential format in {credentials_path}. "
            "Expected OAuth client credentials or service account JSON."
        )


# Credential <-> Dict conversion for token store


def credentials_to_dict(credentials: Credentials) -> dict[str, Any]:
    """Convert Credentials object to a dictionary for storage.
    
    Args:
        credentials: OAuth credentials object.
        
    Returns:
        Dictionary containing all credential fields.
    """
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
    """Convert dictionary to Credentials object.
    
    Args:
        token_data: Dictionary containing credential fields.
        
    Returns:
        Credentials object.
    """
    creds = Credentials(
        token=token_data.get("token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri"),
        client_id=token_data.get("client_id"),
        client_secret=token_data.get("client_secret"),
        scopes=token_data.get("scopes"),
    )
    
    # Parse expiry
    expiry_str = token_data.get("expiry")
    if expiry_str:
        try:
            creds.expiry = datetime.fromisoformat(expiry_str)
        except (ValueError, TypeError):
            pass
    
    return creds


# Token store integration


def load_token_from_store(token_store: TokenStore, user_id: str) -> Credentials | None:
    """Load OAuth token from token store.
    
    Args:
        token_store: The token store to load from.
        user_id: User identifier.
        
    Returns:
        Credentials object, or None if not found.
    """
    token_data = token_store.get(user_id)
    if token_data:
        return dict_to_credentials(token_data)
    return None


def save_token_to_store(
    token_store: TokenStore,
    user_id: str,
    credentials: Credentials,
) -> None:
    """Save OAuth token to token store.
    
    Args:
        token_store: The token store to save to.
        user_id: User identifier.
        credentials: Credentials to save.
    """
    token_data = credentials_to_dict(credentials)
    token_store.save(user_id, token_data)


def delete_token_from_store(token_store: TokenStore, user_id: str) -> bool:
    """Delete OAuth token from token store.
    
    Args:
        token_store: The token store to delete from.
        user_id: User identifier.
        
    Returns:
        True if deleted, False if not found.
    """
    return token_store.delete(user_id)


# Legacy file-based functions (kept for backwards compatibility)


def load_token(token_path: Path) -> Credentials | None:
    """Load existing OAuth token from file.
    
    Note: This is deprecated. Use TokenStore with load_token_from_store instead.
    """
    if token_path.exists():
        with open(token_path, "rb") as token_file:
            return pickle.load(token_file)
    return None


def save_token(token_path: Path, credentials: Credentials) -> None:
    """Save OAuth token to file.
    
    Note: This is deprecated. Use TokenStore with save_token_to_store instead.
    """
    token_path.parent.mkdir(parents=True, exist_ok=True)
    with open(token_path, "wb") as token_file:
        pickle.dump(credentials, token_file)


def delete_token(token_path: Path) -> bool:
    """Delete OAuth token file. Returns True if deleted, False if not found.
    
    Note: This is deprecated. Use TokenStore with delete_token_from_store instead.
    """
    if token_path.exists():
        token_path.unlink()
        return True
    return False


# OAuth flow functions


def create_oauth_flow(
    credentials_path: Path,
    scopes: list[str],
    redirect_uri: str | None = None,
) -> InstalledAppFlow:
    """Create an OAuth flow without running it."""
    flow = InstalledAppFlow.from_client_secrets_file(
        str(credentials_path), scopes
    )
    if redirect_uri:
        flow.redirect_uri = redirect_uri
    return flow


def get_auth_url(
    credentials_path: Path,
    scopes: list[str],
    redirect_uri: str = "urn:ietf:wg:oauth:2.0:oob",
) -> tuple[str, InstalledAppFlow]:
    """Get OAuth authorization URL without opening browser.

    Returns:
        Tuple of (authorization_url, flow). The flow is needed for exchange_code().
    """
    flow = create_oauth_flow(credentials_path, scopes, redirect_uri)
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return auth_url, flow


def exchange_code(
    flow: InstalledAppFlow,
    code: str,
    token_path: Path | None = None,
) -> Credentials:
    """Exchange authorization code for credentials.

    Args:
        flow: The OAuth flow from get_auth_url().
        code: The authorization code from the OAuth callback.
        token_path: Optional path to save the token.

    Returns:
        The OAuth credentials.
    """
    flow.fetch_token(code=code)
    credentials = flow.credentials

    if token_path:
        save_token(token_path, credentials)

    return credentials


def refresh_credentials(credentials: Credentials) -> Credentials:
    """Refresh OAuth credentials."""
    if not credentials.refresh_token:
        raise AuthenticationError("No refresh token available")
    try:
        credentials.refresh(Request())
        return credentials
    except Exception as e:
        raise AuthenticationError(f"Failed to refresh token: {e}")


def revoke_credentials(credentials: Credentials) -> bool:
    """Revoke OAuth credentials.

    Returns:
        True if revocation was successful, False otherwise.
    """
    if not credentials.token:
        return False

    try:
        response = requests.post(
            "https://oauth2.googleapis.com/revoke",
            params={"token": credentials.token},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        return response.status_code == 200
    except Exception:
        return False


def get_oauth_credentials(
    credentials_path: Path,
    token_path: Path,
    scopes: list[str],
    open_browser: bool = True,
    port: int = 8080,
) -> Credentials:
    """Get OAuth credentials, refreshing or creating as needed.
    
    Note: This is deprecated. Use get_oauth_credentials_from_store for multi-user support.

    Args:
        credentials_path: Path to OAuth client secrets file.
        token_path: Path to store/load the token.
        scopes: List of OAuth scopes.
        open_browser: If True, opens browser for OAuth flow.
        port: Port for the local OAuth callback server (default: 8080).
    """
    creds = load_token(token_path)

    # Refresh or create new credentials
    if creds and creds.expired and creds.refresh_token:
        creds = refresh_credentials(creds)
        save_token(token_path, creds)
    elif not creds or not creds.valid:
        if not open_browser:
            raise AuthenticationError(
                "No valid credentials and open_browser=False. "
                "Use get_auth_url() and exchange_code() for manual flow."
            )
        flow = InstalledAppFlow.from_client_secrets_file(
            str(credentials_path), scopes
        )
        creds = flow.run_local_server(port=port)
        save_token(token_path, creds)

    return creds


def get_oauth_credentials_from_store(
    credentials_path: Path,
    token_store: TokenStore,
    user_id: str,
    scopes: list[str],
    open_browser: bool = True,
    port: int = 8080,
) -> Credentials:
    """Get OAuth credentials using a token store, refreshing or creating as needed.

    Args:
        credentials_path: Path to OAuth client secrets file.
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

    # Refresh or create new credentials
    if creds and creds.expired and creds.refresh_token:
        creds = refresh_credentials(creds)
        save_token_to_store(token_store, user_id, creds)
    elif not creds or not creds.valid:
        if not open_browser:
            raise AuthenticationError(
                "No valid credentials and open_browser=False. "
                "Use get_auth_url() and exchange_code() for manual flow."
            )
        flow = InstalledAppFlow.from_client_secrets_file(
            str(credentials_path), scopes
        )
        creds = flow.run_local_server(port=port)
        save_token_to_store(token_store, user_id, creds)

    return creds


def get_service_account_credentials(
    credentials_path: Path,
    scopes: list[str],
    subject: str | None = None,
) -> service_account.Credentials:
    """Get service account credentials.
    
    Args:
        credentials_path: Path to service account JSON file.
        scopes: List of OAuth scopes.
        subject: Optional email address to impersonate (domain delegation).
        
    Returns:
        Service account credentials.
        
    Raises:
        AuthenticationError: If loading credentials fails.
    """
    try:
        creds = service_account.Credentials.from_service_account_file(
            str(credentials_path), scopes=scopes
        )
        
        # Apply domain delegation if subject is provided
        if subject:
            creds = creds.with_subject(subject)
        
        return creds
    except Exception as e:
        raise AuthenticationError(
            f"Failed to load service account credentials: {e}"
        )


def get_service_account_info(credentials_path: Path) -> dict:
    """Get service account info from credentials file."""
    try:
        with open(credentials_path) as f:
            return json.load(f)
    except Exception as e:
        raise InvalidCredentialsError(f"Cannot read credentials file: {e}")
