"""Authentication handling for Google APIs."""

import json
import pickle
from pathlib import Path

import requests
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from ._exceptions import AuthenticationError, InvalidCredentialsError
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


def load_token(token_path: Path) -> Credentials | None:
    """Load existing OAuth token from file."""
    if token_path.exists():
        with open(token_path, "rb") as token_file:
            return pickle.load(token_file)
    return None


def save_token(token_path: Path, credentials: Credentials) -> None:
    """Save OAuth token to file."""
    token_path.parent.mkdir(parents=True, exist_ok=True)
    with open(token_path, "wb") as token_file:
        pickle.dump(credentials, token_file)


def delete_token(token_path: Path) -> bool:
    """Delete OAuth token file. Returns True if deleted, False if not found."""
    if token_path.exists():
        token_path.unlink()
        return True
    return False


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


def get_service_account_credentials(
    credentials_path: Path,
    scopes: list[str],
) -> service_account.Credentials:
    """Get service account credentials."""
    try:
        return service_account.Credentials.from_service_account_file(
            str(credentials_path), scopes=scopes
        )
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
