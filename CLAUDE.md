# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

EasyGoogleAPI is a Python library (v1.0.0) that simplifies interactions with Google APIs. It provides a unified `GoogleService` class that handles authentication and exposes individual services as properties.

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
uv run python -c "from easygoogleapi import GoogleService, TokenRevokedError, DjangoModelTokenStore"

# Run unit tests (no credentials needed)
uv run pytest tests/ -m "not integration"

# Run integration tests (requires credentials in tests/)
uv run pytest tests/ -m integration

# Run all tests
uv run pytest tests/ -v
```

## Architecture

### Core Pattern

```python
from easygoogleapi import GoogleService

# File-based credentials
google = GoogleService(
    credentials_path="credentials.json",
    services=["calendar", "drive", "gmail"]
)

# In-memory client config (web apps)
google = GoogleService(
    client_config={"client_id": "...", "client_secret": "..."},
    services=["drive"],
    token_store=my_store,
    user_id="user_123",
    auto_auth=False,
)
```

### Constructor Signature

```python
GoogleService(
    credentials_path: str | Path | None = None,  # Mutually exclusive with client_config
    services: Sequence[ServiceName] = (),
    token_path: str | Path | None = None,
    token_store: TokenStore | None = None,
    user_id: str | None = None,
    auto_auth: bool = True,
    oauth_port: int = 8080,
    retry_config: RetryConfig | None = None,
    *,
    client_config: dict | None = None,           # Mutually exclusive with credentials_path
    scopes: list[str] | dict[str, list[str]] | None = None,
    on_token_refresh: Callable | None = None,
    on_token_expired: Callable | None = None,
)
```

### File Structure

```
src/easygoogleapi/
├── __init__.py          # GoogleService class + exports
├── _exceptions.py       # Custom exception hierarchy
├── _types.py            # ServiceName literal, CredentialType enum
├── _config.py           # SERVICE_REGISTRY with scopes/versions
├── _auth.py             # OAuth + service account authentication
├── _token_store.py      # TokenStore ABC + FileTokenStore, InMemoryTokenStore, JSONFileTokenStore
├── _base.py             # BaseService abstract class + RetryConfig
├── contrib/
│   └── django.py        # DjangoModelTokenStore
└── {service}/
    ├── __init__.py      # Exports {Service}Service
    └── service.py       # Service implementation
```

### Key Design Patterns

1. **Lazy loading**: Services built on first access via `@cached_property`
2. **Service registry**: `_config.py` defines API names, versions, scopes per service
3. **Credential auto-detection**: Inspects JSON for `"type": "service_account"` vs `"installed"`/`"web"`
4. **BaseService inheritance**: All services except MeetService inherit from `_base.BaseService` for error handling, retry logic, and `raw` API access
5. **Token store abstraction**: Pluggable `TokenStore` interface for multi-user token persistence
6. **MeetService uses gRPC**: Uses `google-apps-meet` (`SpacesServiceClient`) instead of REST discovery

### Adding a New Service

1. Add entry to `SERVICE_REGISTRY` in `_config.py`
2. Create `{service}/__init__.py` and `{service}/service.py`
3. Add `@cached_property` in `GoogleService` class
4. Export in `__all__`

## Development Notes

- ALWAYS research the relevant Google API documentation before implementing features
- Document all documentation links used for research, as well as a summary of findings
- Each service exposes `.raw` property for direct access to underlying Google API resource (except MeetService)
- `get_auth_url()` returns `tuple[str, str]` (url, state) for CSRF protection
- `list_files()` and `list_responses()` return `dict` with pagination, not flat lists
