# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

EasyGoogleAPI is a Python library (v2.0.0) that simplifies interactions with Google APIs. It provides a unified `GoogleService` class that handles authentication and exposes individual services as properties with typed response models.

## Development Environment

- Python 3.12+ required
- Uses `uv` for dependency management (pyproject.toml-based)

## Commands

```bash
# Install dependencies
uv add <package_name>

# Run Python code
uv run python <script.py>

# Test imports
uv run python -c "from easygoogleapi import GoogleService, AsyncGoogleService, PageIterator, MiddlewareChain"

# Run unit tests (no credentials needed)
uv run pytest tests/ -m "not integration"

# Run integration tests (requires credentials in tests/)
uv run pytest tests/ -m integration

# Run all tests
uv run pytest tests/ -v

# Lint
uv run ruff check src/ tests/
```

## Architecture

### Core Pattern

```python
from easygoogleapi import GoogleService

google = GoogleService(
    credentials_path="credentials.json",
    services=["calendar", "drive", "gmail"]
)

# Typed models — file.name, not file["name"]
for file in google.drive.list_files():
    print(file.name, file.mime_type)
```

### Constructor Signature

```python
GoogleService(
    credentials_path: str | Path | None = None,
    services: Sequence[ServiceName] = (),
    token_store: TokenStore | None = None,
    user_id: str | None = None,
    auto_auth: bool = True,
    oauth_port: int = 8080,
    retry_config: RetryConfig | None = None,
    middleware: MiddlewareChain | None = None,
    *,
    client_config: dict[str, Any] | None = None,
    scopes: list[str] | dict[str, list[str]] | None = None,
    scope_preset: str = "full",
    on_token_refresh: Callable[[Credentials], None] | None = None,
    on_token_expired: Callable[[TokenRevokedError], None] | None = None,
)
```

### File Structure

```
src/easygoogleapi/
├── __init__.py          # Thin re-export module (~70 lines)
├── _service.py          # GoogleService class
├── _async_service.py    # AsyncGoogleService class
├── _auth.py             # OAuth + service account (PKCE enabled)
├── _base.py             # BaseService + RetryConfig + middleware integration
├── _async_base.py       # AsyncBaseService
├── _config.py           # SERVICE_REGISTRY with scopes/versions
├── _exceptions.py       # Exception hierarchy (16 classes)
├── _middleware.py        # MiddlewareChain, RequestContext, ResponseContext
├── _models.py           # GoogleModel base class
├── _pagination.py       # PageIterator for auto-pagination
├── _token_store.py      # TokenStore ABC + FileTokenStore (JSON), InMemoryTokenStore
├── _types.py            # ServiceName, CredentialType, SCOPE_PRESETS
├── contrib/
│   └── django.py        # DjangoModelTokenStore
└── {service}/
    ├── __init__.py
    ├── models.py         # Typed response models (dataclasses)
    └── service.py        # Service implementation
```

### Key Design Patterns

1. **Typed models**: All service methods return dataclass models via `from_api_response()`
2. **Auto-pagination**: List methods return `PageIterator`; `_page` variants for single pages
3. **Lazy loading**: Services built on first access via `@cached_property`
4. **Service registry**: `_config.py` defines API names, versions, scopes per service
5. **PKCE by default**: All OAuth flows use code_verifier/code_challenge (RFC 7636)
6. **Scope presets**: `"readonly"` and `"full"` presets in `_types.py`
7. **Middleware**: Before/after request hooks with correlation IDs
8. **Async support**: `AsyncGoogleService` wraps sync calls via `asyncio.to_thread()`
9. **Token store abstraction**: Pluggable `TokenStore` with JSON file default
10. **MeetService uses gRPC**: `google-apps-meet` (`SpacesServiceClient`)

### Adding a New Service

1. Add entry to `SERVICE_REGISTRY` in `_config.py`
2. Create `{service}/models.py` with dataclasses inheriting from `GoogleModel`
3. Create `{service}/service.py` inheriting from `BaseService`
4. Add `@cached_property` in `GoogleService` (`_service.py`)
5. Export in `__init__.py` and `__all__`
6. Write tests

## Development Notes

- ALWAYS research the relevant Google API documentation before implementing features
- Document all documentation links used for research, as well as a summary of findings
- All service methods return typed models — never `dict[str, Any]`
- List methods use `PageIterator` for auto-pagination
- Each service exposes `.raw` property for direct access to underlying Google API resource
- `get_auth_url()` returns `tuple[str, str]` (url, state) with PKCE enabled
- No `requests` dependency — uses `urllib.request` for token revocation
