# Migration from v0.2.0 to v1.0.0

This guide covers breaking changes and new features in EasyGoogleAPI v1.0.0.

## Breaking Changes

### `credentials_path` is now optional

In v0.2.0, `credentials_path` was required. In v1.0.0, you must provide exactly one of `credentials_path` or `client_config`:

```python
# v0.2.0
google = GoogleService(credentials_path="creds.json", services=["drive"])

# v1.0.0 — still works
google = GoogleService(credentials_path="creds.json", services=["drive"])

# v1.0.0 — new: in-memory config
google = GoogleService(
    client_config={"client_id": "...", "client_secret": "..."},
    services=["drive"],
    token_store=my_store,
    user_id="user_123",
    auto_auth=False,
)
```

Passing neither or both raises `ValueError`.

### `get_auth_url()` returns a tuple

In v0.2.0, `get_auth_url()` returned just the authorization URL string. In v1.0.0, it returns a `tuple[str, str]` of `(authorization_url, state)` for CSRF protection:

```python
# v0.2.0
auth_url = google.get_auth_url(redirect_uri="https://myapp.com/callback")

# v1.0.0
auth_url, state = google.get_auth_url(redirect_uri="https://myapp.com/callback")
# Store `state` in the user's session for CSRF verification
```

### `exchange_code()` auto-saves to token store

In v0.2.0, the caller was responsible for persisting the token after `exchange_code()`. In v1.0.0, `exchange_code()` automatically saves the credentials to the configured token store:

```python
# v0.2.0
google.exchange_code(code)
# Manual: save token to file/database

# v1.0.0
google.exchange_code(code)
# Token is automatically persisted to the token store
```

### `list_files()` returns a dict with pagination

In v0.2.0, `DriveService.list_files()` returned `list[dict]`. In v1.0.0, it returns `dict[str, Any]` with `files` and `nextPageToken` keys:

```python
# v0.2.0
files = google.drive.list_files()
for f in files:
    print(f["name"])

# v1.0.0
result = google.drive.list_files()
for f in result["files"]:
    print(f["name"])
# Pagination: result["nextPageToken"]
```

### `list_responses()` returns a dict with pagination

Similarly, `FormsService.list_responses()` now returns `dict[str, Any]` with `responses` and `nextPageToken` keys:

```python
# v0.2.0
responses = google.forms.list_responses("form_id")

# v1.0.0
result = google.forms.list_responses("form_id")
responses = result["responses"]
next_token = result["nextPageToken"]
```

### MeetService now uses gRPC

`MeetService` switched from the REST discovery API to the gRPC `google-apps-meet` client. This requires an optional dependency:

```bash
pip install easygoogleapi[meet]
```

`MeetService` no longer inherits from `BaseService` and does not have a `.raw` property. It also does not have automatic retry or error wrapping.

### `delete_file()` has a `permanent` parameter

The `permanent` parameter (default `True`) was added to `delete_file()`. The default behavior is unchanged (permanent delete), but you can now soft-delete by passing `permanent=False`:

```python
google.drive.delete_file("file_id")                  # Same as before
google.drive.delete_file("file_id", permanent=False)  # New: trash instead
```

## New Features

### In-memory client config (`client_config`)

Pass OAuth client credentials as a dict instead of a file path. Supports the standard Google format (`{"web": {...}}` or `{"installed": {...}}`) and a flat shorthand (`{"client_id": "...", "client_secret": "..."}`).

### `TokenRevokedError` exception

New exception raised when a refresh token is permanently revoked. Subclass of `AuthenticationError`:

```python
from easygoogleapi import TokenRevokedError

try:
    google.calendar.list_events()
except TokenRevokedError:
    # User must re-authenticate
    pass
```

### `on_token_refresh` and `on_token_expired` callbacks

New constructor parameters for handling token lifecycle events:

```python
google = GoogleService(
    credentials_path="creds.json",
    services=["drive"],
    on_token_refresh=lambda creds: print("Token refreshed"),
    on_token_expired=lambda error: print("Token revoked!"),
)
```

### `DjangoModelTokenStore`

New token store backed by a Django model, shipped in `easygoogleapi.contrib.django`:

```python
from easygoogleapi.contrib.django import DjangoModelTokenStore

store = DjangoModelTokenStore(model=OAuthToken)
```

### Custom scopes

New `scopes` parameter accepts a flat list or per-service dict to override the auto-derived scopes:

```python
google = GoogleService(
    credentials_path="creds.json",
    services=["drive", "gmail"],
    scopes=["https://www.googleapis.com/auth/drive.file"],
)
```

### New Drive methods

`get_file`, `update_file`, `copy_file`, `move_file`, `trash_file`, `restore_file`, `empty_trash`, `share_file`, `share_file_public`, `list_permissions`, `remove_permission`, `get_or_create_folder`, `export_file`, `get_storage_quota`

### New Calendar methods

`create_calendar`, `delete_calendar`, `add_calendar_to_list`, `get_event`

### New Sheets methods

`add_sheet`, `batch_update`, `sheets` parameter on `create_spreadsheet`

### New Docs methods

`create_document`, `insert_text`, `replace_text`

### `body` parameter on Calendar events

`create_event` and `update_event` now accept a raw `body` dict for full control over the event resource.

### Gmail `from_name` and `reply_to`

`send()` now accepts `from_name` (display name for the From header) and `reply_to` (Reply-To address).

### Python version

Minimum Python version is now 3.12 (was 3.13 in some v0.2.0 documentation).

### Version

The library version is `1.0.0` (`easygoogleapi.__version__`).
