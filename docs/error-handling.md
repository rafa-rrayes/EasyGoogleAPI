# Error Handling

EasyGoogleAPI provides a structured exception hierarchy and automatic retry with exponential backoff.

## Exception Hierarchy

```
EasyGoogleAPIError
├── AuthenticationError
│   ├── InvalidCredentialsError
│   ├── TokenExpiredError
│   └── TokenRevokedError
├── ServiceNotEnabledError
├── APIError
│   ├── TransientError (retryable=True)
│   │   ├── RateLimitError
│   │   ├── ServerError
│   │   │   └── BackendError
│   ├── PermanentError (retryable=False)
│   │   ├── PermissionDeniedError
│   │   ├── NotFoundError
│   │   ├── QuotaExceededError
│   │   ├── InvalidRequestError
│   │   └── ConflictError
└── MaxRetriesExceededError
```

## Base Exception

### `EasyGoogleAPIError`

Base exception for all library errors.

| Attribute | Type | Description |
|-----------|------|-------------|
| `message` | `str` | Human-readable error message |
| `status_code` | `int \| None` | HTTP status code, if applicable |
| `retryable` | `bool` | Whether the operation can be retried |
| `reason` | `str \| None` | Short error code/reason |
| `request_id` | `str \| None` | Google API request ID for debugging |

## Authentication Errors

### `AuthenticationError`

Raised when authentication fails. `retryable=False`.

Default message: `"Authentication failed"`

### `InvalidCredentialsError`

Subclass of `AuthenticationError`. Raised when the credentials file is invalid, malformed, or cannot be read.

Default message: `"Invalid credentials"`

### `TokenExpiredError`

Subclass of `AuthenticationError`. Raised when a token has expired and cannot be refreshed.

Default message: `"Token expired and cannot be refreshed"`

### `TokenRevokedError`

Subclass of `AuthenticationError`. Raised when a refresh token has been permanently revoked or invalidated. This typically happens when:

- The user revokes access through their Google Account settings
- The token is invalidated by a password change
- The refresh token exceeds its maximum lifetime

Re-authentication via the full OAuth flow is required.

Default message: `"Token has been revoked — re-authentication required"`

### `ServiceNotEnabledError`

Raised when accessing a service not specified in the `services` list at initialization.

| Attribute | Type | Description |
|-----------|------|-------------|
| `service_name` | `str` | The service that was accessed |
| `enabled_services` | `list[str]` | Services that were enabled |

## API Errors

### `APIError`

Wrapper for Google API errors. Subclass of `EasyGoogleAPIError`.

| Attribute | Type | Description |
|-----------|------|-------------|
| `original_error` | `Exception \| None` | The underlying `HttpError` from the Google API client |

### Transient (Retryable) Errors

These errors have `retryable=True` and are automatically retried by `BaseService._execute_request()`.

#### `TransientError`

Base class for temporary errors. Includes network issues, temporary server failures, and rate limits.

#### `RateLimitError`

HTTP 429. Google API rate limit exceeded.

| Attribute | Type | Description |
|-----------|------|-------------|
| `retry_after` | `int \| None` | Seconds to wait before retrying (from `Retry-After` header) |

Default `reason`: `"rateLimitExceeded"`

#### `ServerError`

HTTP 5xx. Temporary failure on Google's side.

#### `BackendError`

HTTP 503 (Service Unavailable). Subclass of `ServerError`.

Default `reason`: `"backendError"`

### Permanent (Non-Retryable) Errors

These errors have `retryable=False` and are raised immediately without retry.

#### `PermanentError`

Base class for permanent errors.

#### `PermissionDeniedError`

HTTP 403. The authenticated user lacks the required permissions.

Default `reason`: `"forbidden"`

#### `NotFoundError`

HTTP 404. The requested resource does not exist or has been deleted.

Default `reason`: `"notFound"`

#### `QuotaExceededError`

HTTP 429 with a quota-related reason. Unlike rate limits, quota errors require waiting for the quota to reset (daily, hourly) or upgrading.

| Attribute | Type | Description |
|-----------|------|-------------|
| `quota_type` | `str \| None` | Type of quota exceeded (e.g. `"queriesPerDay"`) |
| `limit` | `int \| None` | The quota limit, if available |

Default `reason`: `"quotaExceeded"`

#### `InvalidRequestError`

HTTP 400. The request is malformed or contains invalid parameters.

Default `reason`: `"badRequest"`

#### `ConflictError`

HTTP 409. The operation conflicts with the current state of the resource.

Default `reason`: `"conflict"`

### `MaxRetriesExceededError`

Raised when the maximum number of retry attempts has been exceeded for a retryable error.

| Attribute | Type | Description |
|-----------|------|-------------|
| `attempts` | `int \| None` | Number of attempts made |
| `last_error` | `Exception \| None` | The last error encountered |

## RetryConfig

Configure retry behavior with the `RetryConfig` dataclass:

```python
from easygoogleapi import RetryConfig

config = RetryConfig(
    max_retries=3,         # Maximum retry attempts (default: 3)
    base_delay=1.0,        # Base delay in seconds (default: 1.0)
    max_delay=60.0,        # Maximum delay cap in seconds (default: 60.0)
    exponential_base=2.0,  # Exponential backoff base (default: 2.0)
    jitter=True,           # Add random jitter to delays (default: True)
)

google = GoogleService(
    credentials_path="credentials.json",
    services=["drive"],
    retry_config=config,
)
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_retries` | `int` | `3` | Maximum number of retry attempts |
| `base_delay` | `float` | `1.0` | Base delay in seconds for exponential backoff |
| `max_delay` | `float` | `60.0` | Maximum delay cap in seconds |
| `exponential_base` | `float` | `2.0` | Base for exponential backoff calculation |
| `jitter` | `bool` | `True` | Whether to add random jitter to delay |

## Automatic Retry Behavior

`BaseService._execute_request()` handles retry logic for all REST-based services:

1. Execute the API request
2. On `HttpError`, convert it to the appropriate `APIError` subclass
3. Check if the error is retryable:
   - **HTTP 429** (rate limit) -> retry
   - **HTTP 5xx** (server error) -> retry
   - **All other errors** -> raise immediately
4. Calculate backoff delay using exponential backoff with optional jitter
5. If a `Retry-After` header is present on HTTP 429 responses, use that value instead
6. Repeat up to `max_retries` times
7. If all retries are exhausted, raise `MaxRetriesExceededError`

The delay formula: `min(base_delay * (exponential_base ** attempt), max_delay)`, with optional jitter applied as `delay * (0.5 + random())`.

## Error Handling Example

```python
from easygoogleapi import (
    RateLimitError,
    QuotaExceededError,
    PermissionDeniedError,
    NotFoundError,
    TokenRevokedError,
    MaxRetriesExceededError,
    APIError,
)

try:
    google.drive.list_files()

except TokenRevokedError:
    # User must re-authenticate
    print("Google access revoked, please reconnect")

except RateLimitError as e:
    # Only raised after all retries are exhausted
    print(f"Rate limited, retry after {e.retry_after}s")

except QuotaExceededError:
    # Wait for quota reset
    print("Quota exceeded")

except PermissionDeniedError:
    # Need more scopes or permissions
    print("Permission denied")

except NotFoundError:
    # Resource doesn't exist
    print("Not found")

except MaxRetriesExceededError as e:
    # All retries failed
    print(f"Failed after {e.attempts} attempts: {e.last_error}")

except APIError as e:
    # Catch-all for other API errors
    print(f"API error ({e.status_code}): {e.message}")
```

## Raw API Access

The `.raw` property on each service (except `MeetService`) provides direct access to the underlying Google API resource. Errors from `.raw` calls are standard `googleapiclient.errors.HttpError` and are **not** automatically retried or wrapped.

```python
# Raw access bypasses retry and error wrapping
try:
    result = google.drive.raw.files().watch(
        fileId=file_id,
        body={"id": channel_id, "type": "web_hook", "address": url},
    ).execute()
except HttpError as e:
    # Handle directly
    pass
```
