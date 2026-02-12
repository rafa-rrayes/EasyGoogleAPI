"""Tests for token store functionality."""

import json
from pathlib import Path
import tempfile

import pytest

from easygoogleapi._token_store import (
    FileTokenStore,
    InMemoryTokenStore,
    JSONFileTokenStore,
    TokenStore,
)


class TestInMemoryTokenStore:
    """Tests for InMemoryTokenStore."""
    
    def test_get_nonexistent_returns_none(self):
        """Test that getting a nonexistent token returns None."""
        store = InMemoryTokenStore()
        assert store.get("user_123") is None
    
    def test_save_and_get(self):
        """Test saving and retrieving a token."""
        store = InMemoryTokenStore()
        token_data = {"token": "abc123", "refresh_token": "xyz789"}
        
        store.save("user_123", token_data)
        retrieved = store.get("user_123")
        
        assert retrieved == token_data
    
    def test_save_creates_copy(self):
        """Test that save creates a copy of the data."""
        store = InMemoryTokenStore()
        token_data = {"token": "abc123", "refresh_token": "xyz789"}
        
        store.save("user_123", token_data)
        token_data["token"] = "modified"
        
        retrieved = store.get("user_123")
        assert retrieved["token"] == "abc123"  # Not modified
    
    def test_delete_existing_returns_true(self):
        """Test that deleting an existing token returns True."""
        store = InMemoryTokenStore()
        store.save("user_123", {"token": "abc"})
        
        result = store.delete("user_123")
        
        assert result is True
        assert store.get("user_123") is None
    
    def test_delete_nonexistent_returns_false(self):
        """Test that deleting a nonexistent token returns False."""
        store = InMemoryTokenStore()
        
        result = store.delete("user_123")
        
        assert result is False
    
    def test_multiple_users(self):
        """Test storing tokens for multiple users."""
        store = InMemoryTokenStore()
        
        store.save("user_1", {"token": "token_1"})
        store.save("user_2", {"token": "token_2"})
        store.save("user_3", {"token": "token_3"})
        
        assert store.get("user_1")["token"] == "token_1"
        assert store.get("user_2")["token"] == "token_2"
        assert store.get("user_3")["token"] == "token_3"
    
    def test_update_existing_token(self):
        """Test updating an existing token."""
        store = InMemoryTokenStore()
        
        store.save("user_123", {"token": "old_token"})
        store.save("user_123", {"token": "new_token"})
        
        retrieved = store.get("user_123")
        assert retrieved["token"] == "new_token"


class TestFileTokenStore:
    """Tests for FileTokenStore."""
    
    def test_creates_directory_if_not_exists(self):
        """Test that the directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_dir = Path(tmpdir) / "tokens"
            assert not store_dir.exists()
            
            store = FileTokenStore(store_dir)
            
            assert store_dir.exists()
            assert store_dir.is_dir()
    
    def test_save_and_get(self):
        """Test saving and retrieving a token from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileTokenStore(Path(tmpdir))
            token_data = {"token": "abc123", "refresh_token": "xyz789"}
            
            store.save("user_123", token_data)
            retrieved = store.get("user_123")
            
            assert retrieved == token_data
    
    def test_token_file_exists(self):
        """Test that token file is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileTokenStore(Path(tmpdir))
            
            store.save("user_123", {"token": "abc"})
            
            token_file = Path(tmpdir) / "user_123_token.pickle"
            assert token_file.exists()
    
    def test_delete_removes_file(self):
        """Test that delete removes the token file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileTokenStore(Path(tmpdir))
            
            store.save("user_123", {"token": "abc"})
            token_file = Path(tmpdir) / "user_123_token.pickle"
            assert token_file.exists()
            
            result = store.delete("user_123")
            
            assert result is True
            assert not token_file.exists()
    
    def test_sanitizes_user_id(self):
        """Test that user_id is sanitized for filesystem safety."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileTokenStore(Path(tmpdir))
            
            # Try user_id with path separators
            store.save("user/with/slashes", {"token": "abc"})
            
            # Should create file with sanitized name
            token_file = Path(tmpdir) / "user_with_slashes_token.pickle"
            assert token_file.exists()
    
    def test_persists_across_instances(self):
        """Test that tokens persist across store instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store1 = FileTokenStore(Path(tmpdir))
            store1.save("user_123", {"token": "abc"})
            
            # Create new instance pointing to same directory
            store2 = FileTokenStore(Path(tmpdir))
            retrieved = store2.get("user_123")
            
            assert retrieved["token"] == "abc"


class TestJSONFileTokenStore:
    """Tests for JSONFileTokenStore."""
    
    def test_save_and_get(self):
        """Test saving and retrieving a token from JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = JSONFileTokenStore(Path(tmpdir))
            token_data = {
                "token": "abc123",
                "refresh_token": "xyz789",
                "scopes": ["calendar", "gmail"],
            }
            
            store.save("user_123", token_data)
            retrieved = store.get("user_123")
            
            assert retrieved == token_data
    
    def test_json_file_is_readable(self):
        """Test that the JSON file is human-readable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = JSONFileTokenStore(Path(tmpdir))
            token_data = {"token": "abc123", "refresh_token": "xyz789"}
            
            store.save("user_123", token_data)
            
            # Read the file directly
            token_file = Path(tmpdir) / "user_123_token.json"
            with open(token_file) as f:
                data = json.load(f)
            
            assert data == token_data
    
    def test_formatted_json(self):
        """Test that JSON is formatted with indentation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = JSONFileTokenStore(Path(tmpdir))
            
            store.save("user_123", {"token": "abc", "refresh_token": "xyz"})
            
            token_file = Path(tmpdir) / "user_123_token.json"
            content = token_file.read_text()
            
            # Should be pretty-printed (multi-line)
            assert "\n" in content
            assert content.count("\n") > 1


class TestTokenStoreInterface:
    """Tests for TokenStore interface compliance."""
    
    @pytest.fixture(params=[
        InMemoryTokenStore,
        FileTokenStore,
        JSONFileTokenStore,
    ])
    def store(self, request, tmp_path):
        """Parametrized fixture providing all token store implementations."""
        store_class = request.param
        
        if store_class in (FileTokenStore, JSONFileTokenStore):
            return store_class(tmp_path)
        else:
            return store_class()
    
    def test_implements_interface(self, store):
        """Test that all stores implement the TokenStore interface."""
        assert hasattr(store, "get")
        assert hasattr(store, "save")
        assert hasattr(store, "delete")
        assert callable(store.get)
        assert callable(store.save)
        assert callable(store.delete)
    
    def test_basic_workflow(self, store):
        """Test basic save/get/delete workflow works for all implementations."""
        token_data = {"token": "test_token", "refresh_token": "test_refresh"}
        
        # Initially empty
        assert store.get("test_user") is None
        
        # Save and retrieve
        store.save("test_user", token_data)
        retrieved = store.get("test_user")
        assert retrieved == token_data
        
        # Delete
        assert store.delete("test_user") is True
        assert store.get("test_user") is None
        
        # Delete again
        assert store.delete("test_user") is False
    
    def test_multiple_users_isolated(self, store):
        """Test that multiple users' tokens are properly isolated."""
        store.save("user_1", {"token": "token_1"})
        store.save("user_2", {"token": "token_2"})
        
        assert store.get("user_1")["token"] == "token_1"
        assert store.get("user_2")["token"] == "token_2"
        
        store.delete("user_1")
        assert store.get("user_1") is None
        assert store.get("user_2")["token"] == "token_2"
