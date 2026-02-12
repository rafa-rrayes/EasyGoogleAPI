# EasyGoogleAPI

A simplified Python interface for Google APIs. One class, seven services, zero boilerplate.

## Installation

```bash
pip install easygoogleapi
```

For Google Meet support (requires the gRPC client):

```bash
pip install easygoogleapi[meet]
```

## Supported Services

| Service | Property | Description |
|---------|----------|-------------|
| Google Calendar | `google.calendar` | Events, calendars, attendees |
| Google Drive | `google.drive` | Files, folders, permissions, sharing |
| Gmail | `google.gmail` | Send emails, list messages, labels |
| Google Sheets | `google.sheets` | Read/write ranges, create spreadsheets |
| Google Docs | `google.docs` | Documents, text insertion and replacement |
| Google Forms | `google.forms` | Forms, responses with pagination |
| Google Meet | `google.meet` | Meeting spaces (gRPC-based) |

## Quickstart

### 1. File-based OAuth credentials

The simplest path for scripts and local applications. On first run, a browser window opens for OAuth consent. The token is cached automatically for subsequent runs.

```python
from easygoogleapi import GoogleService

google = GoogleService(
    credentials_path="credentials.json",
    services=["calendar", "drive", "gmail"],
)

events = google.calendar.list_events()
google.drive.upload_file("report.pdf")
google.gmail.send(to="team@company.com", subject="Report", body="See attached.")
```

### 2. In-memory client config (web applications)

For web applications that store client credentials in environment variables or a database, pass a `client_config` dict instead of a file path. Set `auto_auth=False` to use the manual OAuth flow.

```python
import os
from easygoogleapi import GoogleService, InMemoryTokenStore

store = InMemoryTokenStore()

google = GoogleService(
    client_config={
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    },
    services=["drive"],
    token_store=store,
    user_id="user_123",
    auto_auth=False,
)

# Step 1: Get the authorization URL
auth_url, state = google.get_auth_url(redirect_uri="https://myapp.com/callback")

# Step 2: After user authorizes, exchange the code
google.exchange_code(authorization_code)

# Step 3: Use the API
files = google.drive.list_files()
```

### 3. Service account with impersonation

For server-to-server communication or domain-wide delegation:

```python
from easygoogleapi import GoogleService

google = GoogleService.for_service_account(
    credentials_path="service_account.json",
    services=["drive", "sheets"],
    impersonate_user="user@yourdomain.com",
)

files = google.drive.list_files()
```

## Constructor Reference

```python
GoogleService(
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
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `credentials_path` | `str \| Path \| None` | `None` | Path to credentials JSON. Mutually exclusive with `client_config`. |
| `client_config` | `dict \| None` | `None` | In-memory OAuth client config. Mutually exclusive with `credentials_path`. |
| `services` | `Sequence[ServiceName]` | `()` | Services to enable (e.g. `["calendar", "drive"]`). |
| `scopes` | `list[str] \| dict[str, list[str]] \| None` | `None` | Custom OAuth scopes. Auto-derived from services if `None`. |
| `token_path` | `str \| Path \| None` | `None` | Custom path for OAuth token file. |
| `token_store` | `TokenStore \| None` | `None` | Pluggable token storage backend. |
| `user_id` | `str \| None` | `None` | User identifier. Required when using `token_store`. |
| `auto_auth` | `bool` | `True` | Authenticate immediately on init. |
| `oauth_port` | `int` | `8080` | Port for the local OAuth callback server. |
| `retry_config` | `RetryConfig \| None` | `None` | Retry behavior configuration. |
| `on_token_refresh` | `Callable \| None` | `None` | Callback after successful token refresh. |
| `on_token_expired` | `Callable \| None` | `None` | Callback when refresh token is permanently revoked. |

## Factory Methods

| Method | Use Case |
|--------|----------|
| `GoogleService(...)` | Simple scripts, single-user applications |
| `GoogleService.for_user(...)` | Multi-user web apps, background workers |
| `GoogleService.for_service_account(...)` | Server-to-server, domain-wide delegation |

## Documentation

- [Authentication Guide](authentication.md)
- [Token Storage](token-stores.md)
- [Error Handling](error-handling.md)
- [Migration from v0.2.0](migration.md)
- **Services:** [Drive](services/drive.md) | [Calendar](services/calendar.md) | [Gmail](services/gmail.md) | [Sheets](services/sheets.md) | [Forms](services/forms.md) | [Meet](services/meet.md) | [Docs](services/docs.md)
