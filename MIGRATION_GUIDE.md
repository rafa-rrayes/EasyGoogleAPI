# Migration Guide: EasyGoogleAPI v0.1 → v0.2

This guide helps you migrate from EasyGoogleAPI v0.1.x to v0.2.0, which introduces **production-ready multi-user support** while maintaining backwards compatibility.

---

## What's New in v0.2.0

### ✅ Production-Ready Features

1. **Multi-User Support** - Handle multiple users with separate OAuth tokens
2. **Pluggable Token Storage** - Database, Redis, or custom storage backends
3. **Automatic Retry & Backoff** - Handle rate limits and transient failures
4. **Enhanced Error Handling** - Specific exceptions with retry metadata
5. **Service Account Delegation** - Impersonate users with domain delegation
6. **Configurable Retry Policy** - Control retry behavior per instance
7. **Structured Logging** - Better observability in production

### ⚠️ Breaking Changes

**None!** The v0.1 API still works exactly as before.

---

## Quick Start: What You Need to Know

### If You're Using Simple Scripts (Personal Use)

**✅ No changes required!** Your existing code works as-is:

```python
# v0.1 code - still works in v0.2
from easygoogleapi import GoogleService

google = GoogleService(
    credentials_path="credentials.json",
    services=["calendar", "gmail"]
)

events = google.calendar.list_events()
```

### If You're Building a Production Web App

**⚠️ You should migrate to the new multi-user API:**

```python
# v0.2 recommended pattern for production
from easygoogleapi import GoogleService
from my_app.storage import DatabaseTokenStore

# In your request handler or background job
google = GoogleService.for_user(
    user_id=current_user.id,
    token_store=DatabaseTokenStore(db.session),
    credentials_path="oauth_client.json",
    services=["calendar", "gmail"]
)

events = google.calendar.list_events()
```

---

## Migration Scenarios

### Scenario 1: Simple Desktop Script → No Changes

**Before (v0.1):**
```python
from easygoogleapi import GoogleService

google = GoogleService(
    credentials_path="credentials.json",
    services=["calendar"]
)

events = google.calendar.list_events()
```

**After (v0.2):**
```python
# Same code works! No changes needed.
from easygoogleapi import GoogleService

google = GoogleService(
    credentials_path="credentials.json",
    services=["calendar"]
)

events = google.calendar.list_events()
```

**What changed internally:**
- Token storage now uses `FileTokenStore` automatically
- Automatic retry on rate limits and server errors
- Better error messages

---

### Scenario 2: Web App (Flask/Django) → Migrate to Multi-User

**Before (v0.1) - ❌ NOT SAFE FOR PRODUCTION:**
```python
# Don't do this! Single GoogleService for all users
google = GoogleService(
    credentials_path="credentials.json",
    services=["calendar"]
)

@app.route("/events")
def get_events():
    # Problem: All users share the same token!
    events = google.calendar.list_events()
    return jsonify(events)
```

**After (v0.2) - ✅ SAFE FOR PRODUCTION:**
```python
from easygoogleapi import GoogleService
from my_app.models import TokenStore  # Your DB-backed store

@app.route("/events")
def get_events():
    # Create instance per request, per user
    google = GoogleService.for_user(
        user_id=current_user.id,
        token_store=TokenStore(db.session),
        credentials_path="oauth_client.json",
        services=["calendar"]
    )
    
    events = google.calendar.list_events()
    return jsonify(events)
```

**Key Changes:**
1. Use `GoogleService.for_user()` factory method
2. Provide `user_id` (from your auth system)
3. Use database-backed `token_store`
4. Create new instance per request (stateless)

---

### Scenario 3: Background Workers (Celery/RQ) → Multi-User Safe

**Before (v0.1) - ❌ PROBLEMATIC:**
```python
# Shared instance = race conditions
google = GoogleService(
    credentials_path="credentials.json",
    services=["calendar"]
)

@celery.task
def sync_calendar(user_id):
    # Problem: All tasks share the same GoogleService
    events = google.calendar.list_events()
    # ...
```

**After (v0.2) - ✅ SAFE:**
```python
from easygoogleapi import GoogleService
from my_app.models import TokenStore

@celery.task
def sync_calendar(user_id):
    # Create fresh instance per task
    google = GoogleService.for_user(
        user_id=user_id,
        token_store=TokenStore(db.session),
        credentials_path="oauth_client.json",
        services=["calendar"]
    )
    
    events = google.calendar.list_events()
    # Instance is garbage collected after task completes
```

**Key Changes:**
1. Create new instance **inside** the task
2. Pass `user_id` as task parameter
3. Token store handles concurrent access safely

---

### Scenario 4: Service Account → Add Domain Delegation

**Before (v0.1):**
```python
from easygoogleapi import GoogleService

# Service account without impersonation
google = GoogleService(
    credentials_path="service_account.json",
    services=["drive"]
)

files = google.drive.list_files()
```

**After (v0.2) - with impersonation:**
```python
from easygoogleapi import GoogleService

# Service account WITH domain delegation
google = GoogleService.for_service_account(
    credentials_path="service_account.json",
    services=["drive"],
    impersonate_user="user@yourdomain.com"  # NEW
)

files = google.drive.list_files()
# Now accessing user@yourdomain.com's files
```

**Key Changes:**
1. Use `GoogleService.for_service_account()` factory
2. Add `impersonate_user` parameter for delegation

---

## Implementing a Token Store

For production use, you need a database-backed token store.

### Example: SQLAlchemy Token Store

```python
from typing import Any
from easygoogleapi import TokenStore
from sqlalchemy.orm import Session
from my_app.models import OAuthToken  # Your model

class SQLAlchemyTokenStore(TokenStore):
    """Database-backed token storage using SQLAlchemy."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get(self, user_id: str) -> dict[str, Any] | None:
        """Retrieve token for user."""
        token = self.session.query(OAuthToken).filter_by(
            user_id=user_id
        ).first()
        
        if token:
            return {
                "token": token.access_token,
                "refresh_token": token.refresh_token,
                "token_uri": token.token_uri,
                "client_id": token.client_id,
                "client_secret": token.client_secret,
                "scopes": token.scopes.split(","),
                "expiry": token.expiry.isoformat() if token.expiry else None,
            }
        return None
    
    def save(self, user_id: str, token_data: dict[str, Any]) -> None:
        """Save token for user."""
        token = self.session.query(OAuthToken).filter_by(
            user_id=user_id
        ).first()
        
        if not token:
            token = OAuthToken(user_id=user_id)
            self.session.add(token)
        
        token.access_token = token_data.get("token")
        token.refresh_token = token_data.get("refresh_token")
        token.token_uri = token_data.get("token_uri")
        token.client_id = token_data.get("client_id")
        token.client_secret = token_data.get("client_secret")
        token.scopes = ",".join(token_data.get("scopes", []))
        
        expiry_str = token_data.get("expiry")
        if expiry_str:
            from datetime import datetime
            token.expiry = datetime.fromisoformat(expiry_str)
        
        self.session.commit()
    
    def delete(self, user_id: str) -> bool:
        """Delete token for user."""
        token = self.session.query(OAuthToken).filter_by(
            user_id=user_id
        ).first()
        
        if token:
            self.session.delete(token)
            self.session.commit()
            return True
        return False
```

### Example: SQLAlchemy Model

```python
from sqlalchemy import Column, String, Text, DateTime
from my_app.database import Base

class OAuthToken(Base):
    __tablename__ = "oauth_tokens"
    
    user_id = Column(String(255), primary_key=True)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text)
    token_uri = Column(String(500))
    client_id = Column(String(500))
    client_secret = Column(String(500))
    scopes = Column(Text)  # Comma-separated
    expiry = Column(DateTime)
```

---

## Error Handling Changes

### New Exception Types

v0.2 introduces specific exception types for better error handling:

```python
from easygoogleapi import (
    RateLimitError,          # Rate limit hit (429)
    QuotaExceededError,      # Quota exceeded
    PermissionDeniedError,   # Insufficient permissions (403)
    NotFoundError,           # Resource not found (404)
    ServerError,             # Google server error (5xx)
    MaxRetriesExceededError, # All retries failed
)

try:
    events = google.calendar.list_events()
    
except RateLimitError as e:
    # Temporary - library auto-retries, but if you get this, you've hit limits
    print(f"Rate limited, retry after {e.retry_after} seconds")
    
except QuotaExceededError as e:
    # Permanent - need to wait for quota reset or upgrade
    print(f"Quota exceeded: {e.message}")
    
except PermissionDeniedError as e:
    # Permanent - need to request more scopes
    print(f"Permission denied: {e.message}")
    
except NotFoundError as e:
    # Permanent - resource doesn't exist
    print(f"Not found: {e.message}")
```

### Automatic Retry Behavior

**NEW in v0.2:** Automatic retries with exponential backoff!

```python
from easygoogleapi import GoogleService, RetryConfig

# Customize retry behavior
retry_config = RetryConfig(
    max_retries=5,        # Retry up to 5 times (default: 3)
    base_delay=2.0,       # Start with 2s delay (default: 1.0)
    max_delay=60.0,       # Cap at 60s (default: 60.0)
    exponential_base=2.0, # Double each time (default: 2.0)
    jitter=True,          # Add randomness (default: True)
)

google = GoogleService.for_user(
    user_id="user_123",
    token_store=token_store,
    credentials_path="oauth_client.json",
    services=["calendar"],
    retry_config=retry_config,  # NEW
)

# Rate limits and server errors are automatically retried
events = google.calendar.list_events()
```

**What's automatically retried:**
- ✅ Rate limits (HTTP 429)
- ✅ Server errors (HTTP 5xx)
- ✅ Network timeouts

**What's NOT retried:**
- ❌ Bad requests (HTTP 400)
- ❌ Permission denied (HTTP 403)
- ❌ Not found (HTTP 404)
- ❌ Quota exceeded (HTTP 429 with quota reason)

---

## OAuth Flow for Web Apps

### Before (v0.1) - Desktop Only

```python
# Automatically opens browser - doesn't work in web apps
google = GoogleService(
    credentials_path="credentials.json",
    services=["calendar"]
)
# Browser opens automatically
```

### After (v0.2) - Web App Flow

```python
from easygoogleapi import GoogleService
from flask import redirect, request, session

# Step 1: Redirect user to Google's consent screen
@app.route("/oauth/login")
def oauth_login():
    google = GoogleService(
        credentials_path="oauth_client.json",
        services=["calendar", "gmail"],
        auto_auth=False,  # Don't auto-authenticate
    )
    
    auth_url = google.get_auth_url(
        redirect_uri="https://myapp.com/oauth/callback"
    )
    
    return redirect(auth_url)

# Step 2: Handle callback from Google
@app.route("/oauth/callback")
def oauth_callback():
    code = request.args.get("code")
    
    google = GoogleService(
        credentials_path="oauth_client.json",
        services=["calendar", "gmail"],
        auto_auth=False,
    )
    
    # Exchange code for credentials
    google.get_auth_url(redirect_uri="https://myapp.com/oauth/callback")
    google.exchange_code(code)
    
    # Save to database
    from easygoogleapi import credentials_to_dict
    token_data = credentials_to_dict(google._credentials)
    token_store.save(user_id=current_user.id, token_data=token_data)
    
    return redirect("/dashboard")
```

---

## Testing Changes

### Test with InMemoryTokenStore

For unit tests, use the in-memory token store:

```python
from easygoogleapi import GoogleService, InMemoryTokenStore

def test_calendar_access():
    # Use in-memory store for tests
    token_store = InMemoryTokenStore()
    
    # Pre-populate with test token
    token_store.save("test_user", {
        "token": "test_access_token",
        "refresh_token": "test_refresh_token",
        # ... other fields
    })
    
    google = GoogleService.for_user(
        user_id="test_user",
        token_store=token_store,
        credentials_path="test_credentials.json",
        services=["calendar"]
    )
    
    # Test your code...
```

---

## Performance Considerations

### Before (v0.1)

```python
# Cached properties - shared service instances
google = GoogleService(...)
calendar1 = google.calendar  # Creates and caches
calendar2 = google.calendar  # Returns cached instance
```

### After (v0.2)

**Still cached!** But now thread-safe with proper isolation:

```python
google = GoogleService.for_user(...)
calendar1 = google.calendar  # Creates and caches
calendar2 = google.calendar  # Returns cached instance (same google instance)

# But each user gets their own GoogleService instance
google_user1 = GoogleService.for_user(user_id="user1", ...)
google_user2 = GoogleService.for_user(user_id="user2", ...)
# ✓ Properly isolated, no cross-contamination
```

---

## Checklist: Migrating to Production

- [ ] **Token Storage**: Implement database-backed `TokenStore`
- [ ] **Multi-User**: Use `GoogleService.for_user()` with `user_id`
- [ ] **OAuth Flow**: Implement web redirect flow (not desktop flow)
- [ ] **Error Handling**: Catch specific exceptions (`RateLimitError`, etc.)
- [ ] **Retry Config**: Configure retry policy for your use case
- [ ] **Logging**: Enable structured logging for observability
- [ ] **Testing**: Update tests to use `InMemoryTokenStore`
- [ ] **Documentation**: Update team docs with new patterns

---

## FAQ

### Q: Do I need to migrate immediately?

**A:** No. v0.2 is fully backwards compatible. Migrate when:
- Building a new production app
- Adding multi-user support
- Experiencing rate limit issues
- Need better error handling

### Q: Can I mix v0.1 and v0.2 patterns?

**A:** Yes! You can use the simple API in scripts and the multi-user API in web apps.

### Q: What's the performance impact?

**A:** Minimal. Retry logic only activates on failures. Normal requests have negligible overhead.

### Q: Do I need to change my OAuth credentials?

**A:** No. Same Google Cloud credentials work with both versions.

### Q: What about async/await support?

**A:** Coming in v0.3.0. Stay tuned!

---

## Need Help?

- 📖 See [ARCHITECTURE_ANALYSIS.md](./ARCHITECTURE_ANALYSIS.md) for design details
- 💡 Check [examples/](./examples/) for complete working examples
- 🐛 Report issues on [GitHub Issues](https://github.com/rafa-rrayes/easygoogleapi/issues)
- 📧 Email: rafa@rayes.com.br

---

**Happy migrating! 🚀**
