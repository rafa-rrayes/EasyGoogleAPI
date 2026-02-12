# EasyGoogleAPI

<!-- Badges -->
[![PyPI version](https://img.shields.io/pypi/v/easygoogleapi)](https://pypi.org/project/easygoogleapi/)
[![Python versions](https://img.shields.io/pypi/pyversions/easygoogleapi)](https://pypi.org/project/easygoogleapi/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A simplified Python interface for Google APIs. One class, seven services, zero boilerplate. Handles OAuth 2.0 and service account authentication, automatic retries with exponential backoff, multi-user token storage, and a structured exception hierarchy -- so you can focus on what you're building.

## Installation

```bash
pip install easygoogleapi
```

For Google Meet support (requires the gRPC client):

```bash
pip install easygoogleapi[meet]
```

## Quick Start

```python
from easygoogleapi import GoogleService

google = GoogleService(
    credentials_path="credentials.json",
    services=["calendar", "drive", "gmail"],
)

# Start using Google APIs immediately
events = google.calendar.list_events()
google.drive.upload_file("report.pdf")
google.gmail.send(to="team@company.com", subject="Report", body="See attached.")
```

## Usage Examples

### Web Application (in-memory credentials)

```python
import os
from easygoogleapi import GoogleService

google = GoogleService(
    client_config={
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    },
    services=["drive"],
    token_store=my_store,
    user_id="user_123",
    auto_auth=False,
)

# Manual OAuth flow
auth_url, state = google.get_auth_url(redirect_uri="https://myapp.com/callback")
# ... redirect user, receive callback ...
google.exchange_code(authorization_code)

# Now use the API
files = google.drive.list_files()
```

### Service Account with Domain Delegation

```python
google = GoogleService.for_service_account(
    credentials_path="service_account.json",
    services=["drive", "sheets"],
    impersonate_user="user@yourdomain.com",
)

files = google.drive.list_files()
```

### Multi-User with Token Store

```python
from easygoogleapi import GoogleService
from easygoogleapi.contrib.django import DjangoModelTokenStore

store = DjangoModelTokenStore(model=OAuthToken)

google = GoogleService.for_user(
    user_id=str(request.user.id),
    token_store=store,
    credentials_path="oauth_client.json",
    services=["calendar", "gmail"],
)

events = google.calendar.list_events()
```

### Error Handling

```python
from easygoogleapi import TokenRevokedError, NotFoundError, RateLimitError

try:
    google.drive.get_file("file_id")
except TokenRevokedError:
    # User must re-authenticate
    pass
except NotFoundError:
    # File doesn't exist
    pass
except RateLimitError as e:
    # Raised only after all automatic retries are exhausted
    print(f"Retry after {e.retry_after}s")
```

## Supported Services

| Service | Property | Key Methods |
|---------|----------|-------------|
| Calendar | `google.calendar` | `list_events`, `create_event`, `update_event`, `delete_event` |
| Drive | `google.drive` | `list_files`, `upload_file`, `download_file`, `share_file` |
| Gmail | `google.gmail` | `send`, `list_messages`, `get_message` |
| Sheets | `google.sheets` | `read_range`, `write_range`, `append_rows`, `create_spreadsheet` |
| Docs | `google.docs` | `get_document`, `create_document`, `insert_text`, `replace_text` |
| Forms | `google.forms` | `get_form`, `list_responses`, `create_form` |
| Meet | `google.meet` | `create_space`, `get_space`, `end_active_conference` |

## Features

- **Flexible authentication** -- OAuth 2.0 (file-based or in-memory client config) and service accounts, auto-detected
- **Multi-user support** -- Per-user OAuth tokens with pluggable storage backends (`FileTokenStore`, `JSONFileTokenStore`, `InMemoryTokenStore`, `DjangoModelTokenStore`)
- **Automatic retries** -- Exponential backoff with jitter for rate limits (429) and server errors (5xx)
- **Structured exceptions** -- `RateLimitError`, `NotFoundError`, `TokenRevokedError`, `QuotaExceededError`, and more
- **Lazy loading** -- Services initialize only when accessed
- **Type hints** -- Full typing with `py.typed` marker
- **Raw access** -- `.raw` property on every service for direct Google API client access

## Documentation

Full documentation is in the [`/docs`](docs/) folder:

- [Overview & Quickstart](docs/index.md)
- [Authentication Guide](docs/authentication.md)
- [Token Storage](docs/token-stores.md)
- [Error Handling](docs/error-handling.md)
- [Migration from v0.2.0](docs/migration.md)
- **Services:** [Drive](docs/services/drive.md) | [Calendar](docs/services/calendar.md) | [Gmail](docs/services/gmail.md) | [Sheets](docs/services/sheets.md) | [Forms](docs/services/forms.md) | [Meet](docs/services/meet.md) | [Docs](docs/services/docs.md)

## Requirements

- Python 3.12+
- Google Cloud project with enabled APIs
- OAuth 2.0 credentials or service account key

## License

[MIT](LICENSE)
