# EasyGoogleAPI

A simplified Python interface for Google APIs. Stop wrestling with authentication flows and complex client libraries — just connect and use.

```python
from easygoogleapi import GoogleService

google = GoogleService(
    credentials_path="credentials.json",
    services=["calendar", "drive", "gmail"]
)

# That's it. Start using Google APIs.
events = google.calendar.list_events()
google.drive.upload_file("report.pdf")
google.gmail.send(to="team@company.com", subject="Report", body="See attached.")
```

## Features

- **Simple authentication** — OAuth 2.0 and service accounts, auto-detected from your credentials file
- **Multi-user support** — Per-user OAuth tokens with pluggable storage backends
- **Unified interface** — All Google services through a single `GoogleService` object
- **Automatic retries** — Exponential backoff for rate limits and transient failures
- **Rich error handling** — Specific exception types for every failure mode
- **Lazy loading** — Services are only initialized when you use them
- **Type hints** — Full typing support for better IDE experience
- **Raw access** — Drop down to the underlying Google API client when needed via `.raw`

## Supported Services

| Service | Property | Description |
|---------|----------|-------------|
| Google Calendar | `google.calendar` | Events, calendars, attendees |
| Google Drive | `google.drive` | Files, folders, permissions |
| Gmail | `google.gmail` | Send/read emails, labels, threads |
| Google Sheets | `google.sheets` | Spreadsheets, cells, ranges |
| Google Docs | `google.docs` | Documents, text manipulation |
| Google Forms | `google.forms` | Forms, questions, responses |
| Google Meet | `google.meet` | Meeting spaces, participants |

## Installation

```bash
pip install easygoogleapi
```

Or with uv:

```bash
uv add easygoogleapi
```

## Quick Start

### 1. Get Google Cloud Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project (or select existing)
3. Enable the APIs you need (Calendar, Drive, Gmail, etc.)
4. Go to **APIs & Services > Credentials**
5. Create **OAuth 2.0 Client ID** (for user data) or **Service Account** (for server-to-server)
6. Download the JSON credentials file

### 2. Configure Redirect URI (OAuth only)

For OAuth credentials, add your redirect URI to the authorized list:

1. Edit your OAuth 2.0 Client ID in Google Cloud Console
2. Add `http://localhost:8080/` to **Authorized redirect URIs**

### 3. Use the Library

```python
from easygoogleapi import GoogleService

google = GoogleService(
    credentials_path="path/to/credentials.json",
    services=["calendar", "gmail"],  # Only enable what you need
)

# First run opens browser for OAuth consent
# Token is saved automatically for future runs
```

## Usage Examples

### Calendar

```python
from datetime import datetime, timedelta, timezone

# List upcoming events
events = google.calendar.list_events(max_results=10)
for event in events:
    print(event["summary"], event["start"])

# Create an event
start = datetime.now(timezone.utc) + timedelta(days=1)
end = start + timedelta(hours=1)

google.calendar.create_event(
    summary="Team Meeting",
    start=start,
    end=end,
    description="Weekly sync",
    attendees=["alice@company.com", "bob@company.com"],
)
```

### Drive

```python
# List files
files = google.drive.list_files(query="mimeType='application/pdf'")

# Upload a file
result = google.drive.upload_file("report.pdf", folder_id="folder_id_here")
print(f"Uploaded: {result['webViewLink']}")

# Download a file
google.drive.download_file(file_id="...", destination="downloaded.pdf")

# Create a folder
folder = google.drive.create_folder("Project Documents")
```

### Gmail

```python
# Send an email
google.gmail.send(
    to="recipient@example.com",
    subject="Hello!",
    body="This is the email body.",
)

# Send with attachments
google.gmail.send(
    to=["alice@example.com", "bob@example.com"],
    subject="Monthly Report",
    body="<h1>Report</h1><p>Please review.</p>",
    html=True,
    attachments=["report.pdf", "data.xlsx"],
)

# List messages
messages = google.gmail.list_messages(query="is:unread", max_results=10)

# Get message details
message = google.gmail.get_message(message_id="...")
```

### Sheets

```python
# Read data
data = google.sheets.read_range("spreadsheet_id", "Sheet1!A1:D10")

# Write data
google.sheets.write_range(
    "spreadsheet_id",
    "Sheet1!A1:B2",
    values=[["Name", "Score"], ["Alice", 95]],
)

# Append rows
google.sheets.append_rows(
    "spreadsheet_id",
    "Sheet1!A:B",
    values=[["Bob", 87], ["Charlie", 92]],
)

# Create a new spreadsheet
spreadsheet = google.sheets.create_spreadsheet("Q4 Report")
```

### Meet

```python
# Create a meeting space
space = google.meet.create_space()
print(f"Join: {space['meetingUri']}")
print(f"Code: {space['meetingCode']}")
```

## Authentication

### OAuth 2.0 (User Data)

Best for scripts and applications that access user data with their consent.

```python
google = GoogleService(
    credentials_path="oauth_credentials.json",
    services=["calendar", "gmail"],
    oauth_port=8080,  # Redirect URI: http://localhost:8080/
)
```

First run opens browser for consent. Token is cached for subsequent runs.

### Service Account (Server-to-Server)

Best for backend services, automation, and accessing organization data.

```python
google = GoogleService(
    credentials_path="service_account.json",
    services=["sheets", "drive"],
)

# Access project info
print(google.project_id)
print(google.service_account_email)
```

### Service Account with Domain Delegation

Access user data without user consent via domain-wide delegation:

```python
google = GoogleService.for_service_account(
    credentials_path="service_account.json",
    services=["drive", "sheets"],
    impersonate_user="user@yourdomain.com",
)

# Now accessing user@yourdomain.com's files
files = google.drive.list_files()
```

### Manual OAuth Flow (Web Apps)

For web applications where you handle the redirect yourself:

```python
google = GoogleService(
    credentials_path="credentials.json",
    services=["calendar"],
    auto_auth=False,  # Don't authenticate automatically
)

# Get URL to show user
auth_url = google.get_auth_url(redirect_uri="https://myapp.com/callback")
print(f"Please visit: {auth_url}")

# After user authorizes and you receive the code
google.exchange_code(authorization_code)

# Now authenticated
events = google.calendar.list_events()
```

### Authentication Control

```python
# Check authentication status
if google.is_authenticated:
    print(f"Token expires: {google.token_expiry}")

# Force token refresh
google.refresh_token()

# Revoke access (removes token from Google)
google.revoke()

# Local logout (just deletes stored token)
google.logout()
```

## Multi-User Support

For web applications and background workers that handle multiple users, use `GoogleService.for_user()` with a pluggable token store:

```python
from easygoogleapi import GoogleService

@app.route("/calendar/events")
def get_events():
    google = GoogleService.for_user(
        user_id=current_user.id,
        token_store=DatabaseTokenStore(db.session),
        credentials_path="oauth_client.json",
        services=["calendar"],
    )

    events = google.calendar.list_events()
    return jsonify(events)
```

Each user gets their own isolated `GoogleService` instance with their own OAuth token. Instances are stateless and safe for concurrent use.

### Token Store

The `TokenStore` interface lets you store tokens anywhere — database, Redis, filesystem, etc.

Built-in implementations:

| Store | Use Case |
|-------|----------|
| `FileTokenStore` | Local scripts (default) |
| `JSONFileTokenStore` | Human-readable file storage |
| `InMemoryTokenStore` | Testing and development |

#### Custom Token Store

Implement the `TokenStore` interface for your storage backend:

```python
from easygoogleapi import TokenStore

class DatabaseTokenStore(TokenStore):
    def __init__(self, session):
        self.session = session

    def get(self, user_id: str) -> dict | None:
        token = self.session.query(OAuthToken).filter_by(user_id=user_id).first()
        return token.to_dict() if token else None

    def save(self, user_id: str, token_data: dict) -> None:
        token = OAuthToken(user_id=user_id, **token_data)
        self.session.merge(token)
        self.session.commit()

    def delete(self, user_id: str) -> bool:
        token = self.session.query(OAuthToken).filter_by(user_id=user_id).first()
        if token:
            self.session.delete(token)
            self.session.commit()
            return True
        return False
```

### Background Workers

Safe for Celery, RQ, or any background job system — create a fresh instance per task:

```python
@celery.task
def sync_user_calendar(user_id: str):
    google = GoogleService.for_user(
        user_id=user_id,
        token_store=DatabaseTokenStore(db.session),
        credentials_path="oauth_client.json",
        services=["calendar"],
    )

    events = google.calendar.list_events()
    # ... sync logic ...
    # Instance is garbage collected after task completes
```

## Retry and Backoff

All API calls automatically retry on transient failures with exponential backoff:

- **Rate limits (HTTP 429)** — retried with `Retry-After` header respected
- **Server errors (HTTP 5xx)** — retried with exponential backoff
- **Network failures** — retried automatically

Configure retry behavior per instance:

```python
from easygoogleapi import GoogleService, RetryConfig

google = GoogleService(
    credentials_path="credentials.json",
    services=["calendar"],
    retry_config=RetryConfig(
        max_retries=5,        # Default: 3
        base_delay=2.0,       # Default: 1.0
        max_delay=60.0,       # Default: 60.0
        exponential_base=2.0, # Default: 2.0
        jitter=True,          # Default: True
    ),
)
```

## Error Handling

Specific exception types let you handle each failure mode differently:

```python
from easygoogleapi import (
    EasyGoogleAPIError,
    AuthenticationError,
    ServiceNotEnabledError,
    RateLimitError,
    QuotaExceededError,
    PermissionDeniedError,
    NotFoundError,
    ServerError,
    MaxRetriesExceededError,
    APIError,
)

try:
    google.calendar.list_events()

except RateLimitError as e:
    # Auto-retried; only raised if retries exhausted
    print(f"Rate limited, retry after {e.retry_after}s")

except QuotaExceededError:
    # Permanent — wait for quota reset
    print("Quota exceeded")

except PermissionDeniedError:
    # Permanent — need more scopes or permissions
    print("Permission denied")

except NotFoundError:
    # Resource doesn't exist
    print("Not found")

except AuthenticationError:
    # Auth failed — token expired, revoked, etc.
    print("Authentication failed")

except ServiceNotEnabledError as e:
    # Service wasn't listed in services=[]
    print(f"Service not enabled: {e.service_name}")

except MaxRetriesExceededError:
    # All retry attempts failed
    print("All retries exhausted")

except APIError as e:
    # Catch-all for other API errors
    print(f"API error: {e}")
    print(f"Original error: {e.original_error}")
```

### Exception Hierarchy

```
EasyGoogleAPIError
├── AuthenticationError
│   ├── InvalidCredentialsError
│   └── TokenExpiredError
├── ServiceNotEnabledError
├── APIError
│   ├── TransientError (retryable)
│   │   ├── RateLimitError
│   │   ├── ServerError
│   │   └── BackendError
│   ├── PermissionDeniedError
│   ├── NotFoundError
│   ├── QuotaExceededError
│   ├── InvalidRequestError
│   └── ConflictError
└── MaxRetriesExceededError
```

## Advanced Usage

### Raw API Access

Every service exposes the underlying Google API client:

```python
# Use the raw Google API client for advanced operations
raw_calendar = google.calendar.raw
raw_calendar.events().quickAdd(
    calendarId="primary",
    text="Dinner with Alice tomorrow 7pm"
).execute()
```

### Scopes

Scopes are automatically determined from enabled services:

```python
print(google.scopes)
# ['https://www.googleapis.com/auth/calendar', 'https://www.googleapis.com/auth/gmail.modify']
```

## Configuration Reference

### GoogleService Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `credentials_path` | `str \| Path` | required | Path to credentials JSON |
| `services` | `list[str]` | required | Services to enable |
| `token_path` | `str \| Path` | auto | Where to store OAuth token (file mode) |
| `token_store` | `TokenStore` | `None` | Pluggable token storage backend |
| `user_id` | `str` | `None` | User identifier (required with `token_store`) |
| `auto_auth` | `bool` | `True` | Authenticate on init |
| `oauth_port` | `int` | `8080` | Port for OAuth callback |
| `retry_config` | `RetryConfig` | defaults | Retry behavior configuration |

### Factory Methods

| Method | Use Case |
|--------|----------|
| `GoogleService(...)` | Simple scripts, single user |
| `GoogleService.for_user(...)` | Multi-user web apps, background workers |
| `GoogleService.for_service_account(...)` | Server-to-server, domain delegation |

### Available Services

`"calendar"`, `"drive"`, `"gmail"`, `"sheets"`, `"docs"`, `"forms"`, `"meet"`

## Requirements

- Python 3.13+
- Google Cloud project with enabled APIs and scopes
- OAuth 2.0 credentials or service account key
