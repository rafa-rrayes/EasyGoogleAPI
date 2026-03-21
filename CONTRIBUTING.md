# Contributing to EasyGoogleAPI

## Development Setup

```bash
# Clone the repository
git clone https://github.com/rafa-rrayes/easygoogleapi.git
cd easygoogleapi

# Install dependencies with uv
uv sync --dev

# Run tests (no credentials needed)
uv run pytest tests/ -m "not integration" -v

# Run linter
uv run ruff check src/ tests/

# Run type checker
uv run mypy src/
```

## Project Structure

```
src/easygoogleapi/
├── __init__.py          # Thin re-export module
├── _service.py          # GoogleService class
├── _async_service.py    # AsyncGoogleService class
├── _auth.py             # OAuth + service account authentication
├── _base.py             # BaseService + RetryConfig
├── _async_base.py       # AsyncBaseService
├── _config.py           # SERVICE_REGISTRY
├── _exceptions.py       # Exception hierarchy
├── _middleware.py        # MiddlewareChain
├── _models.py           # GoogleModel base class
├── _pagination.py       # PageIterator
├── _token_store.py      # TokenStore ABC + implementations
├── _types.py            # ServiceName, CredentialType, scope presets
└── {service}/
    ├── __init__.py
    ├── models.py         # Typed response models
    └── service.py        # Service implementation
```

## Adding a New Service

1. Add entry to `SERVICE_REGISTRY` in `_config.py`
2. Create `{service}/models.py` with typed dataclass models inheriting from `GoogleModel`
3. Create `{service}/service.py` with a class inheriting from `BaseService`
4. Add `@cached_property` in `GoogleService` (`_service.py`)
5. Add exports to `__init__.py` and `__all__`
6. Write tests in `tests/test_{service}.py`

## Adding a New Method

1. Research the Google API documentation
2. Add the method to the appropriate service class
3. Return a typed model (never `dict[str, Any]`)
4. If it's a list method, use `PageIterator` for auto-pagination
5. Write at least one unit test with a mocked API response

## Code Style

- Python 3.12+, no compatibility shims
- `ruff` for linting and formatting
- `mypy --strict` for type checking
- All service methods return typed models
- All new files need module-level docstrings

## Testing

- Unit tests: `uv run pytest tests/ -m "not integration"`
- Integration tests: `uv run pytest tests/ -m integration` (requires credentials in `tests/`)
- All tests must pass before merging

## Pull Request Process

1. Create a feature branch
2. Write tests for new functionality
3. Ensure `ruff check` and tests pass
4. Submit PR with a clear description
