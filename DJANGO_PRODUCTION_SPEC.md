# EasyGoogleAPI v1.0 — Production Django Specification

**Target**: Transform easygoogleapi into a gold-standard library for integrating Google APIs in production Django/web applications.

**Audience**: Engineers working on easygoogleapi.

**Reference application**: SIGE — a multi-tenant Django + DRF + React SPA that uses Drive, Gmail, Calendar, Forms, Sheets, and Meet APIs with OAuth tokens stored in a PostgreSQL database.

**Current version analyzed**: v0.2.0

---

## Executive Summary

easygoogleapi v0.2.0 was designed for desktop/CLI apps that store credentials in JSON files on disk. Production web applications like SIGE:

- Store OAuth `client_id`/`client_secret` in environment variables or database fields — there is **no credentials JSON file on disk**
- Use web-based OAuth flows (`google_auth_oauthlib.flow.Flow`) with frontend callback URLs — not desktop flows (`InstalledAppFlow`)
- Upload files from in-memory streams (`BinaryIO`/`bytes`) received from HTTP requests — not from local file paths
- Use both shared organizational credentials and per-user credentials
- Need comprehensive Drive API coverage (50+ operations), not just 5

This document specifies every change needed to close these gaps.

---

## Table of Contents

1. [AUTH-1: Support in-memory client config (no credentials file)](#auth-1-support-in-memory-client-config)
2. [AUTH-2: Use web OAuth flow, not desktop flow](#auth-2-use-web-oauth-flow)
3. [AUTH-3: Fix exchange_code() to save to TokenStore](#auth-3-fix-exchange_code-to-save-to-tokenstore)
4. [AUTH-4: Support custom scopes at instantiation](#auth-4-support-custom-scopes)
5. [AUTH-5: Add on_token_refresh callback](#auth-5-add-on_token_refresh-callback)
6. [DRIVE-1: Support stream upload (BinaryIO/bytes)](#drive-1-support-stream-upload)
7. [DRIVE-2: Support stream download (return bytes)](#drive-2-support-stream-download)
8. [DRIVE-3: Add get_file method](#drive-3-add-get_file)
9. [DRIVE-4: Add update_file method](#drive-4-add-update_file)
10. [DRIVE-5: Add copy_file method](#drive-5-add-copy_file)
11. [DRIVE-6: Add move_file method](#drive-6-add-move_file)
12. [DRIVE-7: Add trash/restore methods](#drive-7-add-trash-restore)
13. [DRIVE-8: Add sharing and permissions methods](#drive-8-add-sharing-and-permissions)
14. [DRIVE-9: Add get_or_create_folder](#drive-9-add-get_or_create_folder)
15. [DRIVE-10: Add export_file method](#drive-10-add-export_file)
16. [DRIVE-11: Add storage quota method](#drive-11-add-storage-quota)
17. [DRIVE-12: Improve list_files with pagination and ordering](#drive-12-improve-list_files)
18. [CAL-1: Add create_calendar and delete_calendar](#cal-1-add-create-and-delete-calendar)
19. [CAL-2: Add insert_calendar_to_list](#cal-2-add-insert-calendar-to-list)
20. [CAL-3: Add get_event method](#cal-3-add-get_event)
21. [CAL-4: Support raw event body in create/update](#cal-4-support-raw-event-body)
22. [SHEETS-1: Add add_sheet (tab) method](#sheets-1-add-add_sheet)
23. [SHEETS-2: Support sheets parameter in create_spreadsheet](#sheets-2-support-sheets-in-create)
24. [SHEETS-3: Add batch_update method](#sheets-3-add-batch_update)
25. [FORMS-1: Add pagination support to list_responses](#forms-1-add-pagination)
26. [MEET-1: Support gRPC Meet client (SpacesServiceClient)](#meet-1-support-grpc-meet-client)
27. [GMAIL-1: Support From header / sender name](#gmail-1-support-from-header)
28. [CORE-1: Make all service wrappers expose raw resource consistently](#core-1-raw-resource-access)
29. [TOKEN-1: Add DjangoModelTokenStore example](#token-1-django-model-tokenstore)
30. [TOKEN-2: Add on_token_expired callback to TokenStore](#token-2-on_token_expired-callback)
31. [ERR-1: Add token revocation/expiry detection](#err-1-token-revocation-detection)

---

## AUTH-1: Support in-memory client config

**Problem**: `GoogleService.__init__` requires `credentials_path: str | Path` pointing to a JSON file on disk. Production web apps store `client_id` and `client_secret` in environment variables (via `os.environ`) or database fields. There is no JSON file.

**Current code** (`__init__.py:192`):
```python
self._credentials_path = Path(credentials_path).expanduser().resolve()
```

**Required change**: Accept an alternative `client_config: dict` parameter.

**Signature**:
```python
class GoogleService:
    def __init__(
        self,
        credentials_path: str | Path | None = None,  # Now optional
        services: Sequence[ServiceName] = (),
        *,
        client_config: dict | None = None,  # NEW — in-memory config
        # ... rest unchanged
    ):
```

**Validation**: Exactly one of `credentials_path` or `client_config` must be provided.

**`client_config` format** (matches Google's expected format):
```python
# OAuth web application
{
    "web": {
        "client_id": "xxx.apps.googleusercontent.com",
        "client_secret": "GOCSPX-xxx",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}

# OAuth installed application
{
    "installed": {
        "client_id": "xxx.apps.googleusercontent.com",
        "client_secret": "GOCSPX-xxx",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}
```

**Shorthand** — also accept a flat dict for convenience:
```python
{
    "client_id": "xxx.apps.googleusercontent.com",
    "client_secret": "GOCSPX-xxx",
}
```
The library should normalize this to `{"web": {...}}` format internally, filling in `auth_uri` and `token_uri` defaults.

**Impact on `_auth.py`**: All functions that call `InstalledAppFlow.from_client_secrets_file(credentials_path, ...)` must also accept `Flow.from_client_config(client_config, ...)`. The `detect_credential_type()` function must also handle dict input.

**Impact on factory methods**:
```python
# Both of these must work:
GoogleService.for_user(
    user_id="entity",
    token_store=store,
    credentials_path="oauth_client.json",   # file-based (backwards compatible)
    services=["drive"],
)

GoogleService.for_user(
    user_id="entity",
    token_store=store,
    client_config={                          # NEW: in-memory
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    },
    services=["drive"],
)
```

**Priority**: CRITICAL — this is the single biggest blocker for any Django adoption.

---

## AUTH-2: Use web OAuth flow, not desktop flow

**Problem**: `_auth.py` exclusively uses `InstalledAppFlow` (designed for desktop apps that open a local browser and listen on `localhost`). Web applications need `google_auth_oauthlib.flow.Flow` which supports custom redirect URIs pointing to frontend callback pages like `https://myapp.com/auth/google/callback`.

**Current code** (`_auth.py:183`):
```python
flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), scopes)
```

**Required change**: Detect credential type and use the correct flow:

- If `client_config` has `"web"` key → use `Flow.from_client_config()`
- If `client_config` has `"installed"` key → use `InstalledAppFlow.from_client_secrets_file()` (or `from_client_config`)
- If `credentials_path` is provided → detect from file content (existing logic)

**`get_auth_url()` must change**:
```python
# Current (desktop-only):
def get_auth_url(credentials_path, scopes, redirect_uri="urn:ietf:wg:oauth:2.0:oob"):
    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), scopes)
    ...

# Required (web-aware):
def get_auth_url(
    credentials_path_or_config,  # Path | dict
    scopes,
    redirect_uri,                # REQUIRED for web flows (no default OOB)
):
    if isinstance(credentials_path_or_config, dict):
        flow = Flow.from_client_config(credentials_path_or_config, scopes=scopes)
    else:
        flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path_or_config), scopes)

    flow.redirect_uri = redirect_uri

    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return auth_url, flow, state  # ALSO return state for CSRF protection
```

**Key changes**:
1. Import `Flow` from `google_auth_oauthlib.flow` (not just `InstalledAppFlow`)
2. Accept dict (in-memory config) or Path (file)
3. Return `state` parameter — web apps need this for CSRF protection
4. Make `redirect_uri` required when using web flows (no OOB default)

**`exchange_code()` must change** — see AUTH-3.

**The `authenticate()` method** must detect web vs installed mode:
- Web mode (`client_config` has `"web"` key): Do NOT call `run_local_server()`. Require manual `get_auth_url()` → `exchange_code()` flow.
- Installed mode: Existing behavior (browser + local server) preserved.

**Priority**: CRITICAL — without this, no web application can use the library.

---

## AUTH-3: Fix exchange_code() to save to TokenStore

**Problem**: `exchange_code()` (`_auth.py:210-231`) saves the token to `self._token_path` (a file path) but does NOT save to `self._token_store`. In multi-user mode (`for_user()`), `_token_path` is `None`, so the exchanged token is never persisted.

**Current code** (`__init__.py:434-438`):
```python
def exchange_code(self, code: str) -> bool:
    self._credentials = exchange_code(
        self._oauth_flow, code, self._token_path  # <-- token_path is None in multi-user mode
    )
    self._oauth_flow = None
    return True
```

**Required change**:
```python
def exchange_code(self, code: str) -> bool:
    if self._oauth_flow is None:
        raise AuthenticationError("No active OAuth flow. Call get_auth_url() first.")

    self._credentials = exchange_code(self._oauth_flow, code)
    self._oauth_flow = None

    # Save to token store (critical for multi-user mode)
    if self._token_store and self._user_id:
        save_token_to_store(self._token_store, self._user_id, self._credentials)

    return True
```

**Also**: `exchange_code()` in `_auth.py` should NOT take `token_path` as a parameter. Persistence is the responsibility of `GoogleService`, not the auth utility function.

**Priority**: CRITICAL — this is a bug. Multi-user token persistence is broken.

---

## AUTH-4: Support custom scopes

**Problem**: Scopes are hardcoded per service in `_config.py`. Production apps often need more specific scopes. For example:
- SIGE uses `drive.file` (access only files created by the app) instead of `drive` (full access)
- SIGE uses `gmail.send` instead of `gmail.modify`
- SIGE uses `forms.body` + `forms.responses.readonly` instead of `forms` (full access)

**Required change**: Allow scope overrides at instantiation:
```python
GoogleService.for_user(
    user_id="entity",
    token_store=store,
    client_config={...},
    services=["drive", "gmail"],
    scopes={                          # NEW: per-service scope overrides
        "drive": ["https://www.googleapis.com/auth/drive.file"],
        "gmail": ["https://www.googleapis.com/auth/gmail.send"],
    },
)
```

**Behavior**:
- If `scopes` dict is provided, use specified scopes for those services
- For services not in `scopes` dict, use defaults from `SERVICE_REGISTRY`
- Validation: warn if overridden scopes may be insufficient for the service's methods

**Alternative** (simpler): Accept a flat `scopes: list[str]` that replaces the auto-computed scopes entirely:
```python
GoogleService.for_user(
    user_id="entity",
    token_store=store,
    client_config={...},
    services=["drive", "gmail"],
    scopes=[                          # Flat list overrides everything
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/gmail.send",
    ],
)
```

**Priority**: HIGH — most production apps need granular scope control for principle of least privilege.

---

## AUTH-5: Add on_token_refresh callback

**Problem**: When the library internally refreshes a token (e.g., during `_execute_request`), the new token must be persisted. Currently, the library only persists during `authenticate()` and `refresh_token()`, but NOT during automatic refresh that happens when accessing a service with an expired token.

In production, if a token is refreshed during an API call but not saved, the next request will use the old (now-invalid) token and fail.

**Required change**: After any successful credential refresh, call `save_token_to_store()`:

```python
def _ensure_authenticated(self) -> None:
    if self._credentials is None:
        self.authenticate()
    elif self._credentials.expired and self._credentials.refresh_token:
        self._credentials = refresh_credentials(self._credentials)
        # Persist the refreshed token
        if self._token_store and self._user_id:
            save_token_to_store(self._token_store, self._user_id, self._credentials)
```

**Additionally**: Expose an optional callback for consumers who need to run custom logic on refresh (e.g., update additional DB fields, log to audit):

```python
GoogleService.for_user(
    user_id="entity",
    token_store=store,
    client_config={...},
    services=["drive"],
    on_token_refresh=lambda user_id, new_token, new_expiry: ...,  # Optional callback
)
```

**Priority**: CRITICAL — without this, tokens refreshed during API calls are silently lost.

---

## DRIVE-1: Support stream upload (BinaryIO/bytes)

**Problem**: `DriveService.upload_file()` only accepts `file_path: str | Path` and uses `MediaFileUpload`. In web applications, file data arrives as in-memory `BinaryIO` streams or `bytes` from HTTP request bodies (e.g., Django's `request.FILES["file"]`). Writing to a temp file first is a performance regression and security risk.

**Current code** (`drive/service.py:32-51`):
```python
def upload_file(self, file_path: str | Path, ...):
    media = MediaFileUpload(str(file_path), mimetype=mime_type)
```

**Required change**: Support both file paths and streams:
```python
def upload_file(
    self,
    file: str | Path | BinaryIO | bytes,  # Accept all input types
    name: str | None = None,
    folder_id: str | None = None,
    mime_type: str | None = None,
    description: str | None = None,
    fields: str = "id, name, mimeType, size, webViewLink, webContentLink",
    resumable: bool = True,
) -> dict[str, Any]:
    """Upload a file to Drive from a path, bytes, or stream."""
    file_metadata: dict[str, Any] = {}
    if name:
        file_metadata["name"] = name
    if folder_id:
        file_metadata["parents"] = [folder_id]
    if description:
        file_metadata["description"] = description

    if isinstance(file, (str, Path)):
        file_path = Path(file)
        if not name:
            file_metadata["name"] = file_path.name
        media = MediaFileUpload(str(file_path), mimetype=mime_type, resumable=resumable)
    else:
        if isinstance(file, bytes):
            file = io.BytesIO(file)
        if not name:
            raise ValueError("name is required when uploading from stream/bytes")
        media = MediaIoBaseUpload(
            file, mimetype=mime_type or "application/octet-stream", resumable=resumable
        )

    request = self._resource.files().create(
        body=file_metadata, media_body=media, fields=fields
    )
    return self._execute_request(request)
```

**New imports needed**: `io`, `BinaryIO` from `typing`, `MediaIoBaseUpload` from `googleapiclient.http`

**Priority**: CRITICAL — every web application uploads files from HTTP request streams, not local file paths.

---

## DRIVE-2: Support stream download (return bytes)

**Problem**: `DriveService.download_file()` only writes to a local file path. Web applications need bytes (to serve as HTTP response, store in memory, etc.).

**Required change**: Support both modes:
```python
def download_file(
    self,
    file_id: str,
    destination: str | Path | None = None,  # If None, return bytes
) -> Path | bytes:
    """Download a file. Returns bytes if no destination, else writes to file."""
    request = self._resource.files().get_media(fileId=file_id)

    if destination is not None:
        destination = Path(destination)
        with open(destination, "wb") as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
        return destination
    else:
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        buffer.seek(0)
        return buffer.read()
```

**Also add** `export_file()` for Google Docs/Sheets/Slides — see DRIVE-10.

**Priority**: CRITICAL

---

## DRIVE-3: Add get_file method

**Purpose**: Retrieve file metadata by ID. This is the most common Drive operation.

```python
def get_file(
    self,
    file_id: str,
    fields: str = "id, name, mimeType, size, createdTime, modifiedTime, parents, webViewLink, webContentLink, owners, shared",
) -> dict[str, Any]:
    """Get file metadata by ID."""
    request = self._resource.files().get(fileId=file_id, fields=fields)
    return self._execute_request(request)
```

**Priority**: HIGH

---

## DRIVE-4: Add update_file method

**Purpose**: Update a file's content and/or metadata. Must support stream input (same as upload).

```python
def update_file(
    self,
    file_id: str,
    new_content: str | Path | BinaryIO | bytes | None = None,
    new_name: str | None = None,
    description: str | None = None,
    mime_type: str | None = None,
    fields: str = "id, name, mimeType, size, modifiedTime, webViewLink",
) -> dict[str, Any]:
    """Update a file's content and/or metadata."""
    file_metadata = {}
    if new_name:
        file_metadata["name"] = new_name
    if description is not None:
        file_metadata["description"] = description

    media = None
    if new_content is not None:
        if isinstance(new_content, (str, Path)):
            media = MediaFileUpload(str(new_content), mimetype=mime_type, resumable=True)
        else:
            if isinstance(new_content, bytes):
                new_content = io.BytesIO(new_content)
            media = MediaIoBaseUpload(
                new_content, mimetype=mime_type or "application/octet-stream", resumable=True
            )

    request = self._resource.files().update(
        fileId=file_id,
        body=file_metadata or None,
        media_body=media,
        fields=fields,
    )
    return self._execute_request(request)
```

**Priority**: HIGH

---

## DRIVE-5: Add copy_file method

```python
def copy_file(
    self,
    file_id: str,
    name: str | None = None,
    folder_id: str | None = None,
    fields: str = "id, name, mimeType, size, webViewLink",
) -> dict[str, Any]:
    """Create a copy of a file."""
    body: dict[str, Any] = {}
    if name:
        body["name"] = name
    if folder_id:
        body["parents"] = [folder_id]

    request = self._resource.files().copy(
        fileId=file_id, body=body or None, fields=fields
    )
    return self._execute_request(request)
```

**Priority**: MEDIUM

---

## DRIVE-6: Add move_file method

```python
def move_file(
    self,
    file_id: str,
    new_parent_id: str,
    fields: str = "id, name, parents",
) -> dict[str, Any]:
    """Move a file to a different folder."""
    # Get current parents
    file = self.get_file(file_id, fields="parents")
    previous_parents = ",".join(file.get("parents", []))

    request = self._resource.files().update(
        fileId=file_id,
        addParents=new_parent_id,
        removeParents=previous_parents,
        fields=fields,
    )
    return self._execute_request(request)
```

**Priority**: MEDIUM

---

## DRIVE-7: Add trash/restore methods

**Problem**: Current `delete_file()` only does permanent delete. Production apps typically trash files first (recoverable), not permanently delete.

```python
def trash_file(self, file_id: str) -> dict[str, Any]:
    """Move a file to trash (recoverable)."""
    request = self._resource.files().update(
        fileId=file_id, body={"trashed": True}, fields="id, name, trashed"
    )
    return self._execute_request(request)

def restore_file(self, file_id: str) -> dict[str, Any]:
    """Restore a file from trash."""
    request = self._resource.files().update(
        fileId=file_id, body={"trashed": False}, fields="id, name, trashed"
    )
    return self._execute_request(request)

def empty_trash(self) -> None:
    """Permanently delete all files in trash."""
    request = self._resource.files().emptyTrash()
    self._execute_request(request)
```

**Also update** existing `delete_file()` to add an optional `permanent` parameter:
```python
def delete_file(self, file_id: str, permanent: bool = True) -> None:
    """Delete a file. If permanent=False, trash it instead."""
    if permanent:
        request = self._resource.files().delete(fileId=file_id)
        self._execute_request(request)
    else:
        self.trash_file(file_id)
```

**Priority**: MEDIUM

---

## DRIVE-8: Add sharing and permissions methods

Production apps need to share files with users and manage access control.

```python
def share_file(
    self,
    file_id: str,
    email: str,
    role: str = "reader",
    send_notification: bool = True,
    message: str | None = None,
) -> dict[str, Any]:
    """Share a file with a user by email."""
    permission = {"type": "user", "role": role, "emailAddress": email}
    request = self._resource.permissions().create(
        fileId=file_id,
        body=permission,
        sendNotificationEmail=send_notification,
        emailMessage=message,
        fields="id, type, role, emailAddress",
    )
    return self._execute_request(request)

def share_file_public(self, file_id: str, role: str = "reader") -> dict[str, Any]:
    """Make a file accessible to anyone with the link."""
    permission = {"type": "anyone", "role": role}
    request = self._resource.permissions().create(
        fileId=file_id, body=permission, fields="id, type, role"
    )
    return self._execute_request(request)

def list_permissions(
    self, file_id: str,
    fields: str = "permissions(id, type, role, emailAddress, displayName)",
) -> list[dict[str, Any]]:
    """List all permissions on a file."""
    request = self._resource.permissions().list(fileId=file_id, fields=fields)
    result = self._execute_request(request)
    return result.get("permissions", [])

def remove_permission(self, file_id: str, permission_id: str) -> None:
    """Remove a permission from a file."""
    request = self._resource.permissions().delete(
        fileId=file_id, permissionId=permission_id
    )
    self._execute_request(request)
```

**Priority**: HIGH

---

## DRIVE-9: Add get_or_create_folder

Common pattern in production apps: ensure a folder exists before uploading.

```python
def get_or_create_folder(
    self,
    name: str,
    parent_id: str | None = None,
) -> dict[str, Any]:
    """Get an existing folder by name, or create it if it doesn't exist."""
    query_parts = [
        f"name = '{name}'",
        "mimeType = 'application/vnd.google-apps.folder'",
        "trashed = false",
    ]
    if parent_id:
        query_parts.append(f"'{parent_id}' in parents")

    existing = self.list_files(query=" and ".join(query_parts), page_size=1)
    if existing:
        return existing[0]

    return self.create_folder(name, parent_id)
```

**Priority**: MEDIUM

---

## DRIVE-10: Add export_file method

Google Docs/Sheets/Slides cannot be downloaded directly — they must be exported to a standard format.

```python
EXPORT_MIME_TYPES = {
    "application/vnd.google-apps.document": "application/pdf",
    "application/vnd.google-apps.spreadsheet": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.google-apps.presentation": "application/pdf",
}

def export_file(
    self,
    file_id: str,
    mime_type: str | None = None,
    destination: str | Path | None = None,
) -> Path | bytes:
    """Export a Google Docs/Sheets/Slides file to a standard format.

    If mime_type not provided, uses sensible defaults (PDF for Docs/Slides, XLSX for Sheets).
    If destination not provided, returns bytes.
    """
    if mime_type is None:
        # Auto-detect from file metadata
        metadata = self.get_file(file_id, fields="mimeType")
        mime_type = self.EXPORT_MIME_TYPES.get(metadata["mimeType"], "application/pdf")

    request = self._resource.files().export_media(fileId=file_id, mimeType=mime_type)

    if destination is not None:
        destination = Path(destination)
        with open(destination, "wb") as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
        return destination
    else:
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        buffer.seek(0)
        return buffer.read()
```

**Priority**: MEDIUM

---

## DRIVE-11: Add storage quota method

```python
def get_storage_quota(self) -> dict[str, Any]:
    """Get storage quota info (limit, usage, usageInDrive, usageInDriveTrash)."""
    request = self._resource.about().get(fields="storageQuota, user")
    result = self._execute_request(request)
    return result.get("storageQuota", {})
```

**Priority**: LOW

---

## DRIVE-12: Improve list_files with pagination and ordering

**Problem**: Current `list_files` doesn't support pagination tokens or custom ordering.

```python
def list_files(
    self,
    query: str | None = None,
    folder_id: str | None = None,       # NEW: shorthand for common query
    page_size: int = 100,
    page_token: str | None = None,       # NEW: pagination
    order_by: str | None = None,         # NEW: e.g. "modifiedTime desc"
    fields: str = "files(id, name, mimeType, size, modifiedTime, parents, webViewLink)",
) -> dict[str, Any]:
    """List files. Returns dict with 'files' list and optional 'nextPageToken'."""
    if query is None and folder_id:
        query = f"'{folder_id}' in parents and trashed = false"
    elif query is None:
        query = "trashed = false"

    kwargs: dict[str, Any] = {
        "pageSize": min(page_size, 1000),
        "fields": f"nextPageToken, {fields}",
    }
    if query:
        kwargs["q"] = query
    if page_token:
        kwargs["pageToken"] = page_token
    if order_by:
        kwargs["orderBy"] = order_by

    request = self._resource.files().list(**kwargs)
    result = self._execute_request(request)
    return {
        "files": result.get("files", []),
        "nextPageToken": result.get("nextPageToken"),
    }
```

**Breaking change note**: The current `list_files` returns `list[dict]`. The new version returns `dict` with `files` and `nextPageToken`. Provide a migration path or document clearly.

**Priority**: HIGH

---

## CAL-1: Add create_calendar and delete_calendar

Production apps create dedicated calendars (e.g., "SIGE Calendar" in a member's Google account).

```python
def create_calendar(
    self,
    summary: str,
    description: str | None = None,
    timezone: str = "UTC",
) -> dict[str, Any]:
    """Create a new secondary calendar."""
    body: dict[str, Any] = {"summary": summary, "timeZone": timezone}
    if description:
        body["description"] = description
    request = self._resource.calendars().insert(body=body)
    return self._execute_request(request)

def delete_calendar(self, calendar_id: str) -> None:
    """Delete a calendar."""
    request = self._resource.calendars().delete(calendarId=calendar_id)
    self._execute_request(request)
```

**Priority**: HIGH

---

## CAL-2: Add insert_calendar_to_list

After creating a secondary calendar, it must be added to the user's calendar list to be visible.

```python
def add_calendar_to_list(
    self,
    calendar_id: str,
    color_id: str | None = None,
    hidden: bool = False,
) -> dict[str, Any]:
    """Add a calendar to the user's calendar list."""
    body: dict[str, Any] = {"id": calendar_id}
    if color_id:
        body["colorId"] = color_id
    if hidden:
        body["hidden"] = True
    request = self._resource.calendarList().insert(body=body)
    return self._execute_request(request)
```

**Priority**: MEDIUM

---

## CAL-3: Add get_event method

```python
def get_event(
    self,
    event_id: str,
    calendar_id: str = "primary",
) -> dict[str, Any]:
    """Get a single event by ID."""
    request = self._resource.events().get(
        calendarId=calendar_id, eventId=event_id
    )
    return self._execute_request(request)
```

**Priority**: MEDIUM

---

## CAL-4: Support raw event body in create/update

**Problem**: `create_event()` only accepts individual parameters (`summary`, `start`, `end`, etc.). Production apps need to pass arbitrary event body dicts with fields like `colorId`, `conferenceData`, `reminders`, `recurrence`, `visibility`, `transparency`, etc.

```python
def create_event(
    self,
    calendar_id: str = "primary",
    *,
    # Simple mode (existing):
    summary: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    description: str | None = None,
    location: str | None = None,
    attendees: list[str] | None = None,
    timezone: str = "UTC",
    # Raw mode (NEW):
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a calendar event.

    Either provide individual fields (summary, start, end, ...) for simple events,
    or provide a raw body dict for full control over all event properties.
    """
    if body is not None:
        event_body = body
    else:
        if summary is None or start is None or end is None:
            raise ValueError("summary, start, and end are required when not using body")
        event_body = {
            "summary": summary,
            "start": {"dateTime": start.isoformat(), "timeZone": timezone},
            "end": {"dateTime": end.isoformat(), "timeZone": timezone},
        }
        if description:
            event_body["description"] = description
        if location:
            event_body["location"] = location
        if attendees:
            event_body["attendees"] = [{"email": e} for e in attendees]

    request = self._resource.events().insert(calendarId=calendar_id, body=event_body)
    return self._execute_request(request)
```

Same pattern for `update_event()` — accept raw body dict.

**Priority**: HIGH

---

## SHEETS-1: Add add_sheet (tab) method

```python
def add_sheet(
    self,
    spreadsheet_id: str,
    title: str,
    index: int | None = None,
) -> dict[str, Any]:
    """Add a new sheet (tab) to an existing spreadsheet."""
    sheet_properties: dict[str, Any] = {"title": title}
    if index is not None:
        sheet_properties["index"] = index

    body = {"requests": [{"addSheet": {"properties": sheet_properties}}]}
    request = self._resource.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body=body
    )
    return self._execute_request(request)
```

**Priority**: MEDIUM

---

## SHEETS-2: Support sheets parameter in create_spreadsheet

```python
def create_spreadsheet(
    self,
    title: str,
    sheets: list[str] | None = None,  # NEW: list of sheet/tab names
) -> dict[str, Any]:
    """Create a new spreadsheet, optionally with named sheets."""
    body: dict[str, Any] = {"properties": {"title": title}}
    if sheets:
        body["sheets"] = [
            {"properties": {"title": name}} for name in sheets
        ]
    request = self._resource.spreadsheets().create(body=body)
    return self._execute_request(request)
```

**Priority**: LOW

---

## SHEETS-3: Add batch_update method

For advanced operations like formatting, merging cells, conditional formatting, etc.

```python
def batch_update(
    self,
    spreadsheet_id: str,
    requests: list[dict[str, Any]],
) -> dict[str, Any]:
    """Apply batch updates to a spreadsheet (formatting, merging, etc)."""
    body = {"requests": requests}
    request = self._resource.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body=body
    )
    return self._execute_request(request)
```

**Priority**: MEDIUM

---

## FORMS-1: Add pagination support to list_responses

**Problem**: `list_responses()` has no `page_token` parameter. Forms with many responses need pagination.

```python
def list_responses(
    self,
    form_id: str,
    page_size: int = 50,
    page_token: str | None = None,  # NEW
) -> dict[str, Any]:  # Changed return type to include nextPageToken
    """List form responses with pagination."""
    kwargs: dict[str, Any] = {"formId": form_id, "pageSize": page_size}
    if page_token:
        kwargs["pageToken"] = page_token
    request = self._resource.forms().responses().list(**kwargs)
    result = self._execute_request(request)
    return {
        "responses": result.get("responses", []),
        "nextPageToken": result.get("nextPageToken"),
    }
```

**Priority**: MEDIUM

---

## MEET-1: Support gRPC Meet client (SpacesServiceClient)

**Problem**: The current MeetService uses `googleapiclient.discovery.build("meet", "v2")` (REST). However, the production-grade Google Meet integration uses `google.apps.meet_v2.SpacesServiceClient` (gRPC), which is a completely different client library (`google-apps-meet`).

The gRPC client provides the `SpacesServiceClient` for creating meeting spaces with OAuth credentials, which is the standard approach used in production.

**Required change**: MeetService should use the gRPC client:

```python
"""Google Meet API wrapper using gRPC client."""

from typing import Any

from .._base import BaseService


class MeetService:
    """Wrapper for Google Meet API using gRPC SpacesServiceClient.

    Note: This service does NOT inherit from BaseService because it uses
    the gRPC client (google.apps.meet_v2) instead of googleapiclient.discovery.
    """

    def __init__(self, credentials):
        """Initialize with OAuth credentials.

        Args:
            credentials: google.oauth2.credentials.Credentials instance
        """
        try:
            from google.apps.meet_v2 import SpacesServiceClient
            from google.apps.meet_v2.types import CreateSpaceRequest, Space
        except ImportError:
            raise ImportError(
                "google-apps-meet is required for Meet integration. "
                "Install it with: pip install google-apps-meet"
            )

        self._SpacesServiceClient = SpacesServiceClient
        self._CreateSpaceRequest = CreateSpaceRequest
        self._Space = Space
        self._credentials = credentials

    def _get_client(self) -> Any:
        """Create a SpacesServiceClient with current credentials."""
        return self._SpacesServiceClient(credentials=self._credentials)

    def create_space(self) -> dict[str, Any]:
        """Create a new meeting space.

        Returns:
            Dict with 'name' (space resource name) and 'meetingUri' (join URL).
        """
        client = self._get_client()
        request = self._CreateSpaceRequest()
        space = client.create_space(request=request)
        return {
            "name": space.name,
            "meetingUri": space.meeting_uri,
            "meetingCode": space.meeting_code,
        }

    def get_space(self, space_name: str) -> dict[str, Any]:
        """Get a meeting space by resource name."""
        client = self._get_client()
        space = client.get_space(name=space_name)
        return {
            "name": space.name,
            "meetingUri": space.meeting_uri,
            "meetingCode": space.meeting_code,
        }
```

**Impact on GoogleService**: The `meet` property must pass `credentials` directly instead of a built `discovery.Resource`:

```python
@cached_property
def meet(self) -> MeetService:
    self._ensure_authenticated()
    return MeetService(credentials=self._credentials)
```

**New dependency**: `google-apps-meet` (add as optional dependency: `pip install easygoogleapi[meet]`)

**Priority**: HIGH — the REST discovery client for Meet is unreliable and less maintained than the gRPC client.

---

## GMAIL-1: Support From header / sender name

**Problem**: `GmailService.send()` doesn't set the `From` header. Production apps send from an organization name (e.g., `"SIGE <org@gmail.com>"`).

```python
def send(
    self,
    to: str | list[str],
    subject: str,
    body: str,
    html: bool = False,
    cc: str | list[str] | None = None,
    bcc: str | list[str] | None = None,
    from_name: str | None = None,       # NEW
    reply_to: str | None = None,         # NEW
    attachments: list[str | Path] | None = None,
) -> dict[str, Any]:
    # ... existing code ...

    if from_name:
        message["from"] = f"{from_name} <me>"  # Gmail replaces "me" with actual address
    if reply_to:
        message["reply-to"] = reply_to

    # ... rest unchanged
```

**Priority**: MEDIUM

---

## CORE-1: Raw resource access consistency

**Current state**: `.raw` is already exposed on `BaseService`. Good.

**Enhancement**: Document clearly that `.raw` is the escape hatch for all operations not covered by wrapper methods. Add a section in README showing the pattern:

```python
# For operations not yet wrapped:
result = google.drive.raw.files().watch(
    fileId=file_id,
    body={"id": channel_id, "type": "web_hook", "address": webhook_url}
).execute()
```

**Priority**: LOW (already works, just needs documentation)

---

## TOKEN-1: Add DjangoModelTokenStore example

Ship a concrete `DjangoModelTokenStore` in an extras module or in documentation.

```python
# easygoogleapi/contrib/django.py (or documented example)

from easygoogleapi import TokenStore


class DjangoModelTokenStore(TokenStore):
    """TokenStore backed by a Django model.

    Expects a model with fields: user_id (CharField), token_data (JSONField).

    Usage:
        store = DjangoModelTokenStore(GoogleToken)
        google = GoogleService.for_user(
            user_id=str(request.user.id),
            token_store=store,
            client_config={...},
            services=["drive"],
        )
    """

    def __init__(self, model_class):
        """
        Args:
            model_class: Django model with 'user_id' (CharField) and
                        'token_data' (JSONField) fields.
        """
        self.model = model_class

    def get(self, user_id: str) -> dict | None:
        try:
            obj = self.model.objects.get(user_id=user_id)
            return obj.token_data
        except self.model.DoesNotExist:
            return None

    def save(self, user_id: str, token_data: dict) -> None:
        self.model.objects.update_or_create(
            user_id=user_id,
            defaults={"token_data": token_data},
        )

    def delete(self, user_id: str) -> bool:
        deleted, _ = self.model.objects.filter(user_id=user_id).delete()
        return deleted > 0
```

**Also provide**: An example Django model:
```python
# Example model for your Django app
from django.db import models

class GoogleToken(models.Model):
    user_id = models.CharField(max_length=255, unique=True, db_index=True)
    token_data = models.JSONField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "google_tokens"
```

**Priority**: HIGH — this removes the biggest friction point for Django adoption.

---

## TOKEN-2: Add on_token_expired callback

**Problem**: When a refresh token is revoked or expires permanently (Google returns `invalid_grant`), production apps need to run cleanup logic: mark the user's Google connection as disconnected, notify the user, clear stale tokens.

**Required change**: Add callback support to `GoogleService`:

```python
GoogleService.for_user(
    user_id="entity",
    token_store=store,
    client_config={...},
    services=["drive"],
    on_token_expired=lambda user_id: Entity.objects.update(
        google_access_token="", google_connected_email=""
    ),
)
```

**Implementation**: In `_ensure_authenticated()` and `refresh_token()`, catch `RefreshError` with `invalid_grant` and call the callback before raising `TokenExpiredError`.

**Priority**: HIGH — without this, apps cannot gracefully handle disconnected accounts.

---

## ERR-1: Token revocation/expiry detection

**Problem**: The current error taxonomy doesn't distinguish between "token needs refresh" (transient) and "token is permanently revoked" (user must re-authenticate). Both are critical in production.

**Required change**: Detect `invalid_grant` and `Token has been revoked` in refresh failures:

```python
class TokenRevokedError(AuthenticationError):
    """Token has been permanently revoked. User must re-authenticate."""
    pass
```

Raise `TokenRevokedError` (not generic `AuthenticationError`) when:
- `google.auth.exceptions.RefreshError` message contains `"invalid_grant"`
- `google.auth.exceptions.RefreshError` message contains `"Token has been revoked"`
- `google.auth.exceptions.RefreshError` message contains `"Token has been expired or revoked"`

This allows consumers to catch specifically:
```python
try:
    events = google.calendar.list_events()
except TokenRevokedError:
    # User must reconnect their Google account
    mark_google_disconnected(user_id)
    return Response({"error": "google_auth_expired"}, status=401)
except TokenExpiredError:
    # Transient — retry after refresh
    google.refresh_token()
```

**Priority**: HIGH

---

## Summary: Priority Matrix

### CRITICAL (must ship for any production web app adoption)

| ID | Change | Effort |
|----|--------|--------|
| AUTH-1 | Support in-memory client config (no credentials file) | Medium |
| AUTH-2 | Use web OAuth flow (Flow, not InstalledAppFlow) | Medium |
| AUTH-3 | Fix exchange_code() to save to TokenStore | Small |
| AUTH-5 | Persist tokens on auto-refresh | Small |
| DRIVE-1 | Stream upload (BinaryIO/bytes) | Small |
| DRIVE-2 | Stream download (return bytes) | Small |

### HIGH (needed for real-world usage)

| ID | Change | Effort |
|----|--------|--------|
| AUTH-4 | Custom scopes | Small |
| DRIVE-3 | get_file | Small |
| DRIVE-4 | update_file (with stream) | Small |
| DRIVE-8 | Sharing and permissions (4 methods) | Medium |
| DRIVE-12 | list_files with pagination + ordering | Small |
| CAL-1 | create_calendar / delete_calendar | Small |
| CAL-4 | Raw event body in create/update | Small |
| MEET-1 | gRPC SpacesServiceClient | Medium |
| TOKEN-1 | DjangoModelTokenStore example | Small |
| TOKEN-2 | on_token_expired callback | Small |
| ERR-1 | Token revocation detection | Small |

### MEDIUM

| ID | Change | Effort |
|----|--------|--------|
| DRIVE-5 | copy_file | Small |
| DRIVE-6 | move_file | Small |
| DRIVE-7 | trash/restore | Small |
| DRIVE-9 | get_or_create_folder | Small |
| DRIVE-10 | export_file | Small |
| CAL-2 | add_calendar_to_list | Small |
| CAL-3 | get_event | Small |
| SHEETS-1 | add_sheet | Small |
| SHEETS-3 | batch_update | Small |
| FORMS-1 | Pagination in list_responses | Small |
| GMAIL-1 | From header / sender name | Small |

### LOW

| ID | Change | Effort |
|----|--------|--------|
| DRIVE-11 | Storage quota | Small |
| SHEETS-2 | Sheets param in create | Small |
| CORE-1 | Document .raw pattern | Docs only |

---

## Implementation Order

Recommended order for implementation:

1. **AUTH-1 + AUTH-2 + AUTH-3 + AUTH-5** (authentication overhaul) — these are coupled and should be done together
2. **DRIVE-1 + DRIVE-2** (stream I/O) — unblocks web app file handling
3. **TOKEN-1 + TOKEN-2 + ERR-1** (Django token store + error handling) — unblocks Django adoption
4. **DRIVE-3, 4, 5, 6, 7, 8, 9, 10, 11, 12** (Drive API completeness) — incremental
5. **CAL-1, 2, 3, 4** (Calendar completeness) — incremental
6. **MEET-1** (gRPC client) — independent work item
7. **SHEETS-1, 2, 3 + FORMS-1 + GMAIL-1** (remaining service gaps) — incremental

After all CRITICAL and HIGH items are implemented, easygoogleapi will be production-ready for Django web applications.
