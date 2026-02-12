# Token Storage

EasyGoogleAPI uses a pluggable `TokenStore` interface for persisting OAuth tokens. This allows integration with databases, caches, filesystems, and other storage backends.

## TokenStore Interface

```python
from abc import ABC, abstractmethod
from typing import Any

class TokenStore(ABC):
    @abstractmethod
    def get(self, user_id: str) -> dict[str, Any] | None:
        """Retrieve token data for a user. Returns None if not found."""
        ...

    @abstractmethod
    def save(self, user_id: str, token_data: dict[str, Any]) -> None:
        """Save token data for a user."""
        ...

    @abstractmethod
    def delete(self, user_id: str) -> bool:
        """Delete token for a user. Returns True if deleted, False if not found."""
        ...
```

Token data is stored as a `dict[str, Any]` with keys: `token`, `refresh_token`, `token_uri`, `client_id`, `client_secret`, `scopes`, and `expiry` (ISO format string or `None`).

## Built-in Implementations

### InMemoryTokenStore

Stores tokens in a Python dict. Tokens are lost when the process exits.

```python
from easygoogleapi import InMemoryTokenStore

store = InMemoryTokenStore()
```

Best for: testing, development, short-lived processes.

### FileTokenStore

Stores each user's token in a separate pickle file. Files are named `{user_id}_token.pickle` in the specified directory.

```python
from pathlib import Path
from easygoogleapi import FileTokenStore

store = FileTokenStore(directory=Path("/path/to/tokens"))
```

**Constructor:** `FileTokenStore(directory: Path)` -- the directory is created if it doesn't exist.

This is the default store when using `credentials_path` without an explicit `token_store`. The directory defaults to the same directory as the credentials file.

Best for: single-user CLI scripts, local development.

### JSONFileTokenStore

Like `FileTokenStore` but uses JSON format instead of pickle. Files are named `{user_id}_token.json`. More portable and human-readable.

```python
from pathlib import Path
from easygoogleapi import JSONFileTokenStore

store = JSONFileTokenStore(directory=Path("/path/to/tokens"))
```

**Constructor:** `JSONFileTokenStore(directory: Path)` -- the directory is created if it doesn't exist.

Best for: local development when you want to inspect tokens, multi-server deployments where pickle compatibility is a concern.

## DjangoModelTokenStore

A Django ORM-backed token store shipped in `easygoogleapi.contrib.django`. No extra infrastructure needed -- tokens are stored in your existing database.

```python
from easygoogleapi.contrib.django import DjangoModelTokenStore
```

### Setup

1. Define a Django model with a user ID field and a JSON field for token data:

```python
# models.py
from django.db import models

class OAuthToken(models.Model):
    user_id = models.CharField(max_length=255, unique=True)
    token_data = models.JSONField()
```

2. Create and use the store:

```python
from easygoogleapi import GoogleService
from easygoogleapi.contrib.django import DjangoModelTokenStore
from .models import OAuthToken

store = DjangoModelTokenStore(
    model=OAuthToken,
    user_id_field="user_id",
    token_data_field="token_data",
)

google = GoogleService.for_user(
    user_id=str(request.user.id),
    token_store=store,
    credentials_path="oauth_client.json",
    services=["calendar"],
)
```

### Constructor

```python
DjangoModelTokenStore(
    model: Any,                        # The Django Model class
    user_id_field: str = "user_id",    # Name of the field storing user IDs
    token_data_field: str = "token_data",  # Name of the JSONField storing tokens
)
```

- `model`: The Django Model class. Must have the specified user ID and token data fields.
- `user_id_field`: Name of the `CharField`/`TextField` that stores the user identifier (default `"user_id"`).
- `token_data_field`: Name of the `JSONField` that stores the token dict (default `"token_data"`).

The store uses `objects.get()` for retrieval, `objects.update_or_create()` for saves, and `objects.filter().delete()` for deletion.

Django is **not** imported at the module level, so the library can be installed without Django present.

## Custom Token Store

Implement the `TokenStore` abstract class for any storage backend:

### Redis example

```python
import json
from typing import Any
from easygoogleapi import TokenStore

class RedisTokenStore(TokenStore):
    def __init__(self, redis_client, prefix: str = "oauth_token:"):
        self._redis = redis_client
        self._prefix = prefix

    def get(self, user_id: str) -> dict[str, Any] | None:
        data = self._redis.get(f"{self._prefix}{user_id}")
        return json.loads(data) if data else None

    def save(self, user_id: str, token_data: dict[str, Any]) -> None:
        self._redis.set(f"{self._prefix}{user_id}", json.dumps(token_data))

    def delete(self, user_id: str) -> bool:
        return self._redis.delete(f"{self._prefix}{user_id}") > 0
```

## Default Store Selection

When no explicit `token_store` is provided, `GoogleService` picks a default:

| Credential source | Default store |
|---|---|
| `credentials_path` (file) | `FileTokenStore` in the same directory as the credentials file |
| `client_config` (dict) | `InMemoryTokenStore` |

When using `client_config` without an explicit `token_store`, tokens are only kept in memory and lost when the process exits. For production use, always provide a persistent `token_store`.
