# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

EasyGoogleAPI is a Python library that simplifies interactions with Google APIs. It provides a unified `GoogleService` class that handles authentication and exposes individual services as properties.

## Development Environment

- Python 3.13+ required
- Uses `uv` for dependency management (pyproject.toml-based)

## Commands

```bash
# Install dependencies
uv add <package_name>

# Run Python code
uv run python <script.py>

# Test imports
uv run python -c "from easygoogleapi import GoogleService"

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

google = GoogleService(
    credentials_path="credentials.json",
    services=["calendar", "drive", "gmail"]
)
google.calendar.list_events()
google.drive.upload_file("file.pdf")
```

### File Structure

```
src/easygoogleapi/
├── __init__.py          # GoogleService class + exports
├── _exceptions.py       # Custom exception hierarchy
├── _types.py            # ServiceName literal, CredentialType enum
├── _config.py           # SERVICE_REGISTRY with scopes/versions
├── _auth.py             # OAuth + service account authentication
├── _base.py             # BaseService abstract class
└── {service}/
    ├── __init__.py      # Exports {Service}Service
    └── service.py       # Service implementation
```

### Key Design Patterns

1. **Lazy loading**: Services built on first access via `@cached_property`
2. **Service registry**: `_config.py` defines API names, versions, scopes per service
3. **Credential auto-detection**: Inspects JSON for `"type": "service_account"` vs `"installed"`/`"web"`
4. **BaseService inheritance**: All services inherit from `_base.BaseService` for error handling and `raw` API access

### Adding a New Service

1. Add entry to `SERVICE_REGISTRY` in `_config.py`
2. Create `{service}/__init__.py` and `{service}/service.py`
3. Add `@cached_property` in `GoogleService` class
4. Export in `__all__`

## Development Notes

- ALWAYS research the relevant Google API documentation before implementing features
- Document all documentation links used for research, as well as a summary of findings
- Each service exposes `.raw` property for direct access to underlying Google API resource
