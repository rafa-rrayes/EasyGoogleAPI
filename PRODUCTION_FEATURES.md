# Production Features (New in v0.2.0)

## 🚀 Production-Ready Multi-User Support

EasyGoogleAPI v0.2.0 is now production-ready for multi-user web applications and background workers.

### Quick Start: Production Web App

```python
from easygoogleapi import GoogleService
from my_app.storage import DatabaseTokenStore

@app.route("/calendar/events")
def get_events():
    # Create instance per request, per user
    google = GoogleService.for_user(
        user_id=current_user.id,
        token_store=DatabaseTokenStore(db.session),
        credentials_path="oauth_client.json",
        services=["calendar"]
    )
    
    events = google.calendar.list_events()
    return jsonify(events)
```

### Key Production Features

#### 1. **Multi-User Architecture**

Separate OAuth tokens per user with database-backed storage:

```python
from easygoogleapi import GoogleService, InMemoryTokenStore

# Each user gets their own instance
google = GoogleService.for_user(
    user_id="user_123",
    token_store=YourDatabaseTokenStore(db),
    credentials_path="oauth_client.json",
    services=["calendar", "gmail"]
)
```

#### 2. **Automatic Retry & Backoff**

Built-in handling for rate limits and transient failures:

```python
from easygoogleapi import GoogleService, RetryConfig

google = GoogleService.for_user(
    user_id="user_123",
    token_store=token_store,
    credentials_path="oauth_client.json",
    services=["calendar"],
    retry_config=RetryConfig(
        max_retries=5,        # Retry up to 5 times
        base_delay=2.0,       # Start with 2s delay
        exponential_base=2.0, # Double each time
        jitter=True,          # Add randomness
    )
)

# Rate limits (429) are automatically retried
# Server errors (5xx) are automatically retried
# Network failures are automatically retried
events = google.calendar.list_events()
```

#### 3. **Enhanced Error Handling**

Specific exception types for better error handling:

```python
from easygoogleapi import (
    RateLimitError,
    QuotaExceededError,
    PermissionDeniedError,
    NotFoundError,
)

try:
    events = google.calendar.list_events()
    
except RateLimitError as e:
    # Temporary - will auto-retry, but if you get this, you've hit limits
    print(f"Rate limited, retry after {e.retry_after} seconds")
    
except QuotaExceededError as e:
    # Permanent - need to wait for quota reset
    print(f"Quota exceeded: {e.message}")
    
except PermissionDeniedError as e:
    # Permanent - need more scopes
    print(f"Permission denied: {e.message}")
```

#### 4. **Service Account with Domain Delegation**

Access user data without user consent:

```python
# Service account with domain delegation
google = GoogleService.for_service_account(
    credentials_path="service_account.json",
    services=["drive", "sheets"],
    impersonate_user="user@yourdomain.com"
)

# Now accessing user@yourdomain.com's files
files = google.drive.list_files()
```

#### 5. **Pluggable Token Storage**

Use any storage backend (database, Redis, etc.):

```python
from easygoogleapi import TokenStore

class DatabaseTokenStore(TokenStore):
    """Store tokens in your database."""
    
    def get(self, user_id: str) -> dict | None:
        # Retrieve from database
        token = db.query(Token).filter_by(user_id=user_id).first()
        return token.to_dict() if token else None
    
    def save(self, user_id: str, token_data: dict) -> None:
        # Save to database
        token = Token(user_id=user_id, **token_data)
        db.add(token)
        db.commit()
    
    def delete(self, user_id: str) -> bool:
        # Delete from database
        token = db.query(Token).filter_by(user_id=user_id).first()
        if token:
            db.delete(token)
            db.commit()
            return True
        return False
```

Built-in implementations:
- `InMemoryTokenStore` - For development/testing
- `FileTokenStore` - For backwards compatibility
- `JSONFileTokenStore` - Human-readable JSON files

#### 6. **Background Worker Safe**

Perfect for Celery, RQ, or any background job system:

```python
from celery import shared_task
from easygoogleapi import GoogleService

@shared_task
def sync_user_calendar(user_id: str):
    # Create fresh instance per task
    google = GoogleService.for_user(
        user_id=user_id,
        token_store=DatabaseTokenStore(db),
        credentials_path="oauth_client.json",
        services=["calendar"]
    )
    
    events = google.calendar.list_events()
    # ... sync logic ...
    
    # Instance is garbage collected after task completes
```

## Backwards Compatibility

**100% backwards compatible!** Your existing code still works:

```python
# v0.1 code - still works in v0.2
from easygoogleapi import GoogleService

google = GoogleService(
    credentials_path="credentials.json",
    services=["calendar"]
)

events = google.calendar.list_events()
```

## Migration Guide

See [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md) for step-by-step migration instructions.

## Architecture

For detailed architecture analysis and production patterns, see:
- [ARCHITECTURE_ANALYSIS.md](./ARCHITECTURE_ANALYSIS.md) - Gap analysis and design decisions
- [scripts/example_production_patterns.py](./scripts/example_production_patterns.py) - Working examples

## Production Checklist

When deploying to production:

- [ ] Use `GoogleService.for_user()` with user IDs
- [ ] Implement database-backed `TokenStore`
- [ ] Configure retry policy for your use case
- [ ] Handle specific exception types
- [ ] Enable structured logging
- [ ] Implement web OAuth redirect flow (not desktop)
- [ ] Monitor rate limits and quotas
- [ ] Test token refresh flow
- [ ] Verify thread safety in your framework
- [ ] Add observability/monitoring

## New in v0.2.0

### Features
- ✅ Multi-user architecture with `for_user()` factory method
- ✅ Service account support with `for_service_account()`
- ✅ Pluggable token storage via `TokenStore` interface
- ✅ Automatic retry with exponential backoff
- ✅ Rate limit handling (HTTP 429)
- ✅ Enhanced exception hierarchy (11 specific types)
- ✅ Configurable retry policy via `RetryConfig`
- ✅ Structured logging throughout
- ✅ Thread-safe and stateless design

### Testing
- ✅ 58 tests (33 existing + 25 new)
- ✅ 100% backwards compatibility
- ✅ 0 CodeQL security alerts

### Documentation
- ✅ Comprehensive migration guide
- ✅ Production patterns examples
- ✅ Architecture analysis
- ✅ SQLAlchemy integration examples

## Requirements

- Python 3.12+
- Google Cloud project with enabled APIs and scopes
- OAuth 2.0 credentials or service account key

---

**Note:** For async/await support, see the upcoming v0.3.0 release.
