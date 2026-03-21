# EasyGoogleAPI

[![PyPI version](https://img.shields.io/pypi/v/easygoogleapi)](https://pypi.org/project/easygoogleapi/)
[![Python versions](https://img.shields.io/pypi/pyversions/easygoogleapi)](https://pypi.org/project/easygoogleapi/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A simplified Python interface for Google APIs. One class, seven services, typed responses, zero boilerplate.

**Python 3.12+ required.**

## Quick Start

```bash
pip install easygoogleapi
```

```python
from easygoogleapi import GoogleService

google = GoogleService(
    credentials_path="credentials.json",
    services=["calendar", "drive", "gmail"],
)

# Typed models with IDE autocompletion
for event in google.calendar.list_events():
    print(event.summary, event.start)

# Auto-paginating iteration
for file in google.drive.list_files():
    print(file.name, file.mime_type)

# Simple email sending
google.gmail.send(to="user@example.com", subject="Hello", body="World")
```

## Features

- **Typed response models** — `file.name`, not `file["name"]`. Full IDE autocompletion.
- **Auto-pagination** — `for file in drive.list_files()` iterates across all pages automatically.
- **Async support** — `AsyncGoogleService` for FastAPI and async frameworks.
- **PKCE-secured OAuth** — RFC 7636 enabled by default on all flows.
- **Scope presets** — `scope_preset="readonly"` for minimal permissions.
- **Middleware hooks** — before/after request hooks with correlation IDs and timing.
- **7 services** — Calendar, Drive, Gmail, Sheets, Docs, Forms, Meet.
- **Automatic retries** — Exponential backoff with jitter for transient errors.
- **Multi-user token storage** — Pluggable `TokenStore` interface with JSON file, in-memory, Django, and Redis backends.

## Typed Models

All service methods return typed dataclass models:

```python
file = google.drive.get_file("file_id")
print(file.name)           # str
print(file.mime_type)       # str
print(file.web_view_link)  # str | None
print(file.to_dict())      # dict for serialization
```

## Auto-Pagination

List methods return `PageIterator` — just iterate:

```python
# Automatically fetches all pages
all_files = list(google.drive.list_files(query="mimeType='application/pdf'"))

# Or iterate lazily
for msg in google.gmail.list_messages(query="is:unread"):
    print(msg.id, msg.snippet)

# Single-page manual control when needed
page = google.drive.list_files_page(page_size=10)
print(page.files, page.next_page_token)
```

## Async Support

```python
from easygoogleapi import AsyncGoogleService

async with AsyncGoogleService(
    credentials_path="credentials.json",
    services=["drive"],
) as google:
    page = await google.drive.list_files_page()
    for file in page.files:
        print(file.name)
```

## Scope Presets

```python
# Read-only access — safer for read-only apps
google = GoogleService(
    credentials_path="credentials.json",
    services=["drive", "gmail"],
    scope_preset="readonly",
)
```

## Middleware

```python
from easygoogleapi import GoogleService, MiddlewareChain

middleware = MiddlewareChain()

@middleware.before_request
def log_request(ctx):
    print(f"[{ctx.correlation_id[:8]}] {ctx.service_name}.{ctx.method_name}")

@middleware.after_request
def log_response(ctx):
    print(f"[{ctx.request.correlation_id[:8]}] {ctx.duration_ms:.0f}ms")

google = GoogleService(
    credentials_path="credentials.json",
    services=["drive"],
    middleware=middleware,
)
```

## Multi-User OAuth

```python
from easygoogleapi import GoogleService, FileTokenStore

store = FileTokenStore(Path("./tokens"))

google = GoogleService.for_user(
    user_id="user_123",
    token_store=store,
    credentials_path="oauth_client.json",
    services=["calendar", "gmail"],
)
```

## Service Account

```python
google = GoogleService.for_service_account(
    credentials_path="service_account.json",
    services=["drive"],
    impersonate_user="user@domain.com",
)
```

## Escape Hatch

Every service exposes `.raw` for direct access to the underlying Google API resource:

```python
# When you need something not wrapped by EasyGoogleAPI
raw_result = google.drive.raw.files().list(q="trashed=true").execute()
```

## License

MIT
