"""Token storage abstraction for multi-user support.

This module provides a pluggable interface for storing OAuth tokens,
allowing integration with databases, caches, and other storage backends.
"""

import json
import pickle
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class TokenStore(ABC):
    """Abstract base class for token storage.
    
    Implementations must provide methods to get, save, and delete tokens
    for users identified by user_id strings.
    """
    
    @abstractmethod
    def get(self, user_id: str) -> dict[str, Any] | None:
        """Retrieve token data for a user.
        
        Args:
            user_id: Unique identifier for the user.
            
        Returns:
            Token data as a dictionary, or None if not found.
        """
        pass
    
    @abstractmethod
    def save(self, user_id: str, token_data: dict[str, Any]) -> None:
        """Save token data for a user.
        
        Args:
            user_id: Unique identifier for the user.
            token_data: Token data to store.
        """
        pass
    
    @abstractmethod
    def delete(self, user_id: str) -> bool:
        """Delete token for a user.
        
        Args:
            user_id: Unique identifier for the user.
            
        Returns:
            True if token was deleted, False if not found.
        """
        pass


class InMemoryTokenStore(TokenStore):
    """In-memory token storage for development and testing.
    
    Warning: Tokens are lost when the process exits. Not suitable for production.
    
    Example:
        >>> store = InMemoryTokenStore()
        >>> store.save("user_123", {"token": "abc", "refresh_token": "xyz"})
        >>> token = store.get("user_123")
        >>> print(token)
        {'token': 'abc', 'refresh_token': 'xyz'}
    """
    
    def __init__(self) -> None:
        """Initialize an empty in-memory store."""
        self._tokens: dict[str, dict[str, Any]] = {}
    
    def get(self, user_id: str) -> dict[str, Any] | None:
        """Get token from memory."""
        return self._tokens.get(user_id)
    
    def save(self, user_id: str, token_data: dict[str, Any]) -> None:
        """Save token to memory."""
        self._tokens[user_id] = token_data.copy()
    
    def delete(self, user_id: str) -> bool:
        """Delete token from memory."""
        if user_id in self._tokens:
            del self._tokens[user_id]
            return True
        return False


class FileTokenStore(TokenStore):
    """File-based token storage using pickle format.
    
    Each user's token is stored in a separate file in the specified directory.
    Files are named: {user_id}_token.pickle
    
    This implementation provides backwards compatibility with the original
    single-file token storage while supporting multiple users.
    
    Example:
        >>> store = FileTokenStore(Path("/path/to/tokens"))
        >>> store.save("user_123", {"token": "abc", "refresh_token": "xyz"})
        >>> token = store.get("user_123")
    
    Note:
        For production use with multiple servers, consider using a database-backed
        token store instead of file-based storage to avoid file locking issues.
    """
    
    def __init__(self, directory: Path) -> None:
        """Initialize file-based token store.
        
        Args:
            directory: Directory where token files will be stored.
                      Will be created if it doesn't exist.
        """
        self._directory = Path(directory).resolve()
        self._directory.mkdir(parents=True, exist_ok=True)
    
    def _get_token_path(self, user_id: str) -> Path:
        """Get the file path for a user's token."""
        # Sanitize user_id to prevent directory traversal
        safe_user_id = user_id.replace("/", "_").replace("\\", "_")
        return self._directory / f"{safe_user_id}_token.pickle"
    
    def get(self, user_id: str) -> dict[str, Any] | None:
        """Load token from file."""
        token_path = self._get_token_path(user_id)
        if token_path.exists():
            with open(token_path, "rb") as f:
                return pickle.load(f)
        return None
    
    def save(self, user_id: str, token_data: dict[str, Any]) -> None:
        """Save token to file."""
        token_path = self._get_token_path(user_id)
        with open(token_path, "wb") as f:
            pickle.dump(token_data, f)
    
    def delete(self, user_id: str) -> bool:
        """Delete token file."""
        token_path = self._get_token_path(user_id)
        if token_path.exists():
            token_path.unlink()
            return True
        return False


class JSONFileTokenStore(TokenStore):
    """JSON-based file token storage.
    
    Similar to FileTokenStore but uses JSON format instead of pickle.
    More portable and inspectable than pickle, but requires token data
    to be JSON-serializable.
    
    Example:
        >>> store = JSONFileTokenStore(Path("/path/to/tokens"))
        >>> store.save("user_123", {"token": "abc", "refresh_token": "xyz"})
    """
    
    def __init__(self, directory: Path) -> None:
        """Initialize JSON file token store.
        
        Args:
            directory: Directory where token files will be stored.
                      Will be created if it doesn't exist.
        """
        self._directory = Path(directory).resolve()
        self._directory.mkdir(parents=True, exist_ok=True)
    
    def _get_token_path(self, user_id: str) -> Path:
        """Get the file path for a user's token."""
        safe_user_id = user_id.replace("/", "_").replace("\\", "_")
        return self._directory / f"{safe_user_id}_token.json"
    
    def get(self, user_id: str) -> dict[str, Any] | None:
        """Load token from JSON file."""
        token_path = self._get_token_path(user_id)
        if token_path.exists():
            with open(token_path, "r") as f:
                return json.load(f)
        return None
    
    def save(self, user_id: str, token_data: dict[str, Any]) -> None:
        """Save token to JSON file."""
        token_path = self._get_token_path(user_id)
        with open(token_path, "w") as f:
            json.dump(token_data, f, indent=2)
    
    def delete(self, user_id: str) -> bool:
        """Delete token file."""
        token_path = self._get_token_path(user_id)
        if token_path.exists():
            token_path.unlink()
            return True
        return False
