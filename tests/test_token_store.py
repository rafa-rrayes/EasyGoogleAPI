"""Tests for token store functionality (v2.0 — JSON-only, no pickle)."""

import json
from pathlib import Path
import tempfile

import pytest

from easygoogleapi._token_store import (
    _BaseFileTokenStore,
    FileTokenStore,
    InMemoryTokenStore,
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
    """Tests for FileTokenStore (JSON-based in v2.0)."""

    def test_creates_directory_if_not_exists(self):
        """Test that the directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_dir = Path(tmpdir) / "tokens"
            assert not store_dir.exists()

            store = FileTokenStore(store_dir)

            assert store_dir.exists()
            assert store_dir.is_dir()

    def test_save_and_get(self):
        """Test saving and retrieving a token from JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileTokenStore(Path(tmpdir))
            token_data = {"token": "abc123", "refresh_token": "xyz789"}

            store.save("user_123", token_data)
            retrieved = store.get("user_123")

            assert retrieved == token_data

    def test_token_file_is_json(self):
        """Test that token file is created as JSON (not pickle)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileTokenStore(Path(tmpdir))

            store.save("user_123", {"token": "abc"})

            # v2.0: files are .json, not .pickle
            token_file = Path(tmpdir) / "user_123_token.json"
            assert token_file.exists()

            # Verify no pickle file exists
            pickle_file = Path(tmpdir) / "user_123_token.pickle"
            assert not pickle_file.exists()

    def test_json_serialization_roundtrip(self):
        """Test that JSON serialization round-trip preserves data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileTokenStore(Path(tmpdir))
            token_data = {
                "token": "abc123",
                "refresh_token": "xyz789",
                "scopes": ["calendar", "drive"],
                "expiry": "2025-12-31T23:59:59",
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
            }

            store.save("user_123", token_data)
            retrieved = store.get("user_123")

            assert retrieved == token_data

    def test_json_file_is_human_readable(self):
        """Test that the JSON file is human-readable with indentation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileTokenStore(Path(tmpdir))
            token_data = {"token": "abc123", "refresh_token": "xyz789"}

            store.save("user_123", token_data)

            token_file = Path(tmpdir) / "user_123_token.json"
            content = token_file.read_text()

            # Should be pretty-printed (multi-line)
            assert "\n" in content
            assert content.count("\n") > 1

            # Verify it's valid JSON
            parsed = json.loads(content)
            assert parsed == token_data

    def test_json_file_can_be_read_directly(self):
        """Test that the JSON file can be read with standard json module."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileTokenStore(Path(tmpdir))
            token_data = {"token": "abc123", "refresh_token": "xyz789"}

            store.save("user_123", token_data)

            token_file = Path(tmpdir) / "user_123_token.json"
            with open(token_file) as f:
                data = json.load(f)

            assert data == token_data

    def test_delete_removes_file(self):
        """Test that delete removes the token file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileTokenStore(Path(tmpdir))

            store.save("user_123", {"token": "abc"})
            token_file = Path(tmpdir) / "user_123_token.json"
            assert token_file.exists()

            result = store.delete("user_123")

            assert result is True
            assert not token_file.exists()

    def test_delete_nonexistent_returns_false(self):
        """Test that deleting a nonexistent token returns False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileTokenStore(Path(tmpdir))
            result = store.delete("nonexistent_user")
            assert result is False

    def test_persists_across_instances(self):
        """Test that tokens persist across store instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store1 = FileTokenStore(Path(tmpdir))
            store1.save("user_123", {"token": "abc"})

            # Create new instance pointing to same directory
            store2 = FileTokenStore(Path(tmpdir))
            retrieved = store2.get("user_123")

            assert retrieved["token"] == "abc"


class TestBaseFileTokenStoreSanitization:
    """Tests for _BaseFileTokenStore shared path computation and sanitization."""

    def test_sanitizes_slashes_in_user_id(self):
        """Test that slashes in user_id are sanitized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileTokenStore(Path(tmpdir))

            store.save("user/with/slashes", {"token": "abc"})

            # Should create file with sanitized name
            token_file = Path(tmpdir) / "user_with_slashes_token.json"
            assert token_file.exists()

    def test_sanitizes_special_characters(self):
        """Test that special characters in user_id are replaced."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileTokenStore(Path(tmpdir))

            store.save("user@email.com", {"token": "abc"})

            # @ and . replaced with _
            token_file = Path(tmpdir) / "user_email_com_token.json"
            assert token_file.exists()

    def test_sanitizes_spaces_and_dots(self):
        """Test that spaces and dots are sanitized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileTokenStore(Path(tmpdir))

            store.save("user name.test", {"token": "abc"})

            token_file = Path(tmpdir) / "user_name_test_token.json"
            assert token_file.exists()

    def test_allows_hyphens_and_underscores(self):
        """Test that hyphens and underscores are preserved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileTokenStore(Path(tmpdir))

            store.save("user-name_test", {"token": "abc"})

            token_file = Path(tmpdir) / "user-name_test_token.json"
            assert token_file.exists()

    def test_sanitizes_dots_to_underscores(self):
        """Test that dots in user_id are sanitized to underscores."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileTokenStore(Path(tmpdir))
            # "..." sanitizes to "___" (valid), "." to "_" (valid)
            store.save("...", {"token": "abc"})
            assert store.get("...") == {"token": "abc"}

    def test_sanitizes_dot_user_id(self):
        """Test that '.' and '..' are sanitized (not rejected)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileTokenStore(Path(tmpdir))
            # "." sanitizes to "_", ".." to "__" — both valid
            path = store._get_token_path(".", "json")
            assert path.name == "__token.json"
            path2 = store._get_token_path("..", "json")
            assert path2.name == "___token.json"

    def test_get_token_path_returns_correct_extension(self):
        """Test that _get_token_path uses the specified extension."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileTokenStore(Path(tmpdir))

            path = store._get_token_path("user_123", "json")
            assert path.name == "user_123_token.json"

    def test_sanitized_round_trip(self):
        """Test that save/get works with sanitized user_ids."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileTokenStore(Path(tmpdir))

            store.save("user/test@email", {"token": "value"})
            retrieved = store.get("user/test@email")

            assert retrieved == {"token": "value"}


class TestTokenStoreInterface:
    """Tests for TokenStore interface compliance."""

    @pytest.fixture(params=[InMemoryTokenStore, FileTokenStore])
    def store(self, request, tmp_path):
        """Parametrized fixture providing all token store implementations."""
        store_class = request.param

        if store_class is FileTokenStore:
            return store_class(tmp_path)
        else:
            return store_class()

    def test_implements_interface(self, store):
        """Test that all stores implement the TokenStore interface."""
        assert isinstance(store, TokenStore)
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
