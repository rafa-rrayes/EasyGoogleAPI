# Changelog

## [2.0.0] — 2026-03-20

### Breaking Changes

- **Typed response models**: All service methods now return typed dataclass models (e.g. `FileMetadata`, `Event`, `Message`) instead of `dict[str, Any]`. Access fields as attributes: `file.name`, not `file["name"]`.
- **Auto-paginating iterators**: `list_files()`, `list_events()`, `list_messages()`, `list_responses()` now return `PageIterator` that auto-paginates. Use `list_files_page()` for single-page results.
- **Removed `token_path` parameter**: Use `token_store` + `user_id` instead.
- **Removed `JSONFileTokenStore`**: Renamed to `FileTokenStore` (now JSON-based by default).
- **Removed pickle-based `FileTokenStore`**: Security fix — pickle deserialization is unsafe.
- **Removed deprecated functions**: `load_token`, `save_token`, `delete_token`, `get_oauth_credentials`.
- **Removed `requests` dependency**: Token revocation now uses `urllib.request`.
- **`GoogleService` moved to `_service.py`**: `__init__.py` is now a thin re-export module.

### Security

- PKCE (RFC 7636) enabled by default on all OAuth flows.
- Drive query injection fixed in `get_or_create_folder` (single quote escaping).
- `_wrap_http_error` null-safety fix for unparseable error responses.

### New Features

- **Scope presets**: `scope_preset="readonly"` for read-only access where available.
- **Async support**: `AsyncGoogleService` with `async with` and `await` support.
- **Middleware system**: `MiddlewareChain` with before/after request hooks, correlation IDs, and timing.
- **25 new service methods**: `search`, `quick_add`, `create_draft`, `reply`, `batch_get`, `append_text`, `add_question`, and more across all services.
- **Typed callbacks**: `on_token_refresh` and `on_token_expired` now have typed signatures.
- **`PermanentError`** added to public exports.
- **`.raw` property on MeetService** for escape-hatch gRPC access.

### Architecture

- `GoogleService` extracted from `__init__.py` to `_service.py`.
- `_BaseFileTokenStore` eliminates `_get_token_path` duplication.
- Drive download logic deduplicated into `_download_to()`.
- Meet lazy imports consolidated into single `_lazy_import()` function.
- Ruff target version fixed to `py312`.

### Testing

- 269 unit tests (up from ~100).
- Comprehensive `_execute_request` retry/backoff tests.
- `_wrap_http_error` status code mapping tests (100% branch coverage).
- Typed model `from_api_response`/`to_dict` round-trip tests.
- `PageIterator` multi-page/empty/single-page tests.
- `MiddlewareChain` hook firing and error isolation tests.
- GitHub Actions CI pipeline for Python 3.12/3.13.

## [1.0.0] — 2025

Initial release with 7 Google API services: Calendar, Drive, Gmail, Sheets, Docs, Forms, Meet.
