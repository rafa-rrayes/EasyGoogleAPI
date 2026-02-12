# Authentication Guide

EasyGoogleAPI supports three credential modes: file-based OAuth, in-memory client config, and service accounts.

## Credential Modes

### 1. File-based OAuth

Pass the path to your downloaded OAuth client credentials JSON file:

```python
google = GoogleService(
    credentials_path="credentials.json",
    services=["calendar", "drive"],
)
```

On first run with `auto_auth=True` (the default), a browser opens for OAuth consent. The token is stored automatically using a `FileTokenStore` in the same directory as the credentials file (with a `_token.pickle` suffix).

### 2. In-memory client config

For web applications where credentials come from environment variables or a database, pass a `client_config` dict:

```python
google = GoogleService(
    client_config={
        "web": {
            "client_id": "xxx.apps.googleusercontent.com",
            "client_secret": "GOCSPX-xxx",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    },
    services=["drive"],
    token_store=my_store,
    user_id="user_123",
    auto_auth=False,
)
```

#### Flat shorthand

You can also use a flat dict with just `client_id` and `client_secret`. The library normalizes it to `{"web": {...}}` format internally, using default Google OAuth URIs:

```python
google = GoogleService(
    client_config={
        "client_id": "xxx.apps.googleusercontent.com",
        "client_secret": "GOCSPX-xxx",
    },
    services=["drive"],
    token_store=my_store,
    user_id="user_123",
    auto_auth=False,
)
```

This normalization is handled by `normalize_client_config()`, which fills in `auth_uri` (`https://accounts.google.com/o/oauth2/auth`) and `token_uri` (`https://oauth2.googleapis.com/token`).

### 3. Service account

For server-to-server communication:

```python
google = GoogleService(
    credentials_path="service_account.json",
    services=["sheets", "drive"],
)
```

Or with domain-wide delegation (impersonation):

```python
google = GoogleService.for_service_account(
    credentials_path="service_account.json",
    services=["drive"],
    impersonate_user="user@yourdomain.com",
)
```

## Credential Type Detection

`detect_credential_type(credentials: Path | dict) -> CredentialType` examines the credential source and returns either `CredentialType.OAUTH` or `CredentialType.SERVICE_ACCOUNT`:

- If the JSON has `"type": "service_account"` -> `SERVICE_ACCOUNT`
- If the JSON has `"installed"` or `"web"` keys -> `OAUTH`
- Otherwise raises `InvalidCredentialsError`

This works for both file paths and in-memory dicts.

## OAuth Flow

### Automatic flow (desktop/CLI apps)

With `auto_auth=True` (default) and installed-type credentials, `authenticate()` opens a browser for consent and starts a local server on `oauth_port` (default 8080) to receive the callback.

### Manual flow (web applications)

For web applications, use the two-step `get_auth_url()` / `exchange_code()` flow:

```python
google = GoogleService(
    client_config=my_config,
    services=["calendar"],
    token_store=my_store,
    user_id="user_123",
    auto_auth=False,
)

# Step 1: Generate the authorization URL
auth_url, state = google.get_auth_url(
    redirect_uri="https://myapp.com/callback"
)
# Redirect the user to auth_url
# Store state in session for CSRF verification

# Step 2: After callback, exchange the code
google.exchange_code(code_from_callback)
# Credentials are automatically saved to the token store

# Now authenticated
events = google.calendar.list_events()
```

#### `get_auth_url(redirect_uri: str | None = None) -> tuple[str, str]`

Returns a tuple of `(authorization_url, state)`. The `state` value should be stored in the user's session and verified in the OAuth callback for CSRF protection.

- `redirect_uri`: Custom redirect URI. Defaults to `"urn:ietf:wg:oauth:2.0:oob"` (out-of-band flow).
- Raises `AuthenticationError` if using service account credentials.

#### `exchange_code(code: str) -> bool`

Exchanges the authorization code for OAuth credentials. The credentials are automatically persisted to the token store. Returns `True` on success.

- Raises `AuthenticationError` if no OAuth flow is active (call `get_auth_url()` first).

## Token Refresh

### Automatic refresh

When accessing a service, `_ensure_authenticated()` checks if the token is expired. If expired and a refresh token is available, it transparently refreshes the token and persists it to the token store. The `on_token_refresh` callback fires after a successful refresh.

### Manual refresh

```python
google.refresh_token()  # -> bool
```

Forces a token refresh. Returns `True` on success.

- Raises `AuthenticationError` for service accounts or if not authenticated.
- Raises `TokenRevokedError` if the refresh token has been permanently revoked (e.g., user revoked access in Google Account settings, password change, or token lifetime exceeded).

## TokenRevokedError and Callbacks

When a refresh token is permanently invalidated (Google returns `invalid_grant`), the library raises `TokenRevokedError` (a subclass of `AuthenticationError`).

You can handle this proactively with the `on_token_expired` callback:

```python
def handle_expired(error: TokenRevokedError):
    # Mark user as disconnected, notify them, etc.
    print(f"Token revoked: {error}")

google = GoogleService(
    credentials_path="credentials.json",
    services=["calendar"],
    on_token_expired=handle_expired,
)
```

The `on_token_expired` callback receives the `TokenRevokedError` instance as its argument. It fires both during automatic refresh (in `_ensure_authenticated()`) and manual refresh (in `refresh_token()`).

The `on_token_refresh` callback receives the refreshed `Credentials` object:

```python
def handle_refresh(credentials):
    print(f"Token refreshed, expires: {credentials.expiry}")

google = GoogleService(
    credentials_path="credentials.json",
    services=["calendar"],
    on_token_refresh=handle_refresh,
)
```

## The `auto_auth` Parameter

- `auto_auth=True` (default): `authenticate()` is called in the constructor. For installed-type credentials, this opens a browser if no valid token exists.
- `auto_auth=False`: Authentication is deferred. You must call `authenticate()`, use the `get_auth_url()`/`exchange_code()` flow, or simply access a service (which triggers `_ensure_authenticated()` automatically).

## Revoking and Logging Out

### `revoke() -> bool`

Revokes the OAuth token with Google's servers **and** deletes the stored token. The user will need to re-authenticate. Returns `True` if revocation succeeded.

### `logout() -> bool`

Deletes the stored token locally **without** contacting Google's servers. The token remains valid on Google's side until it expires. Returns `True` if a token was deleted.

Both methods raise `AuthenticationError` if called with service account credentials.

## Custom Scopes

By default, scopes are derived automatically from the enabled services (see `_config.py`). You can override them:

### Flat list (replaces all auto-computed scopes)

```python
google = GoogleService(
    credentials_path="credentials.json",
    services=["drive", "gmail"],
    scopes=[
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/gmail.send",
    ],
)
```

### Per-service dict

```python
google = GoogleService(
    credentials_path="credentials.json",
    services=["drive", "gmail"],
    scopes={
        "drive": ["https://www.googleapis.com/auth/drive.file"],
        "gmail": ["https://www.googleapis.com/auth/gmail.send"],
    },
)
```

When a dict is provided, all scope lists are merged into a single flat list for the OAuth request.

## Properties

| Property | Type | Description |
|----------|------|-------------|
| `is_authenticated` | `bool` | Whether credentials are valid and not expired |
| `token_expiry` | `datetime \| None` | Token expiry time (OAuth only) |
| `user_email` | `str \| None` | Authenticated user's email (from ID token or service account) |
| `project_id` | `str \| None` | GCP project ID (service account only) |
| `service_account_email` | `str \| None` | Service account email (service account only) |
| `scopes` | `list[str]` | OAuth scopes in use |
| `user_id` | `str \| None` | User ID for this instance |
| `oauth_redirect_uri` | `str` | The redirect URI for Google Cloud Console configuration |
| `enabled_services` | `list[ServiceName]` | Services enabled for this instance |
| `credential_type` | `CredentialType` | `OAUTH` or `SERVICE_ACCOUNT` |
