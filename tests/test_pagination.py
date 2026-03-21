"""Tests for PageIterator auto-pagination."""

import pytest

from easygoogleapi._pagination import PageIterator
from easygoogleapi.drive.models import FileMetadata


class TestPageIteratorBasics:
    """Tests for basic PageIterator behavior."""

    def test_single_page_no_next_token(self):
        """Test iteration over a single page with no nextPageToken."""
        def fetch_page(page_token):
            return {
                "files": [{"id": "f1"}, {"id": "f2"}],
            }

        iterator = PageIterator(fetch_page, items_key="files")
        items = list(iterator)

        assert len(items) == 2
        assert items[0] == {"id": "f1"}
        assert items[1] == {"id": "f2"}

    def test_empty_result(self):
        """Test iteration over empty result set."""
        def fetch_page(page_token):
            return {"files": []}

        iterator = PageIterator(fetch_page, items_key="files")
        items = list(iterator)

        assert items == []

    def test_empty_result_with_no_key(self):
        """Test iteration when the items key is entirely absent."""
        def fetch_page(page_token):
            return {}

        iterator = PageIterator(fetch_page, items_key="files")
        items = list(iterator)

        assert items == []


class TestPageIteratorMultiplePages:
    """Tests for multi-page iteration."""

    def test_iteration_over_three_pages(self):
        """Test that iterator fetches across 3 pages seamlessly."""
        pages = [
            {"files": [{"id": "f1"}, {"id": "f2"}], "nextPageToken": "token1"},
            {"files": [{"id": "f3"}, {"id": "f4"}], "nextPageToken": "token2"},
            {"files": [{"id": "f5"}]},  # Last page, no nextPageToken
        ]
        call_count = 0

        def fetch_page(page_token):
            nonlocal call_count
            idx = call_count
            call_count += 1
            return pages[idx]

        iterator = PageIterator(fetch_page, items_key="files")
        items = list(iterator)

        assert len(items) == 5
        assert [item["id"] for item in items] == ["f1", "f2", "f3", "f4", "f5"]
        assert call_count == 3

    def test_page_tokens_passed_correctly(self):
        """Test that page tokens are passed to subsequent requests."""
        received_tokens = []

        def fetch_page(page_token):
            received_tokens.append(page_token)
            if page_token is None:
                return {"items": [{"id": "1"}], "nextPageToken": "tok_a"}
            elif page_token == "tok_a":
                return {"items": [{"id": "2"}], "nextPageToken": "tok_b"}
            else:
                return {"items": [{"id": "3"}]}

        iterator = PageIterator(fetch_page, items_key="items")
        list(iterator)

        assert received_tokens == [None, "tok_a", "tok_b"]


class TestPageIteratorWithModels:
    """Tests for PageIterator with typed model classes."""

    def test_models_correctly_instantiated(self):
        """Test that model_class is used to wrap each item."""
        def fetch_page(page_token):
            return {
                "files": [
                    {"id": "f1", "name": "test.txt", "mimeType": "text/plain"},
                    {"id": "f2", "name": "doc.pdf", "mimeType": "application/pdf"},
                ],
            }

        iterator = PageIterator(fetch_page, items_key="files", model_class=FileMetadata)
        items = list(iterator)

        assert len(items) == 2
        assert isinstance(items[0], FileMetadata)
        assert isinstance(items[1], FileMetadata)
        assert items[0].name == "test.txt"
        assert items[1].mime_type == "application/pdf"

    def test_models_across_pages(self):
        """Test model instantiation across multiple pages."""
        pages = [
            {"files": [{"id": "f1", "name": "a.txt"}], "nextPageToken": "t1"},
            {"files": [{"id": "f2", "name": "b.txt"}]},
        ]
        idx = 0

        def fetch_page(page_token):
            nonlocal idx
            page = pages[idx]
            idx += 1
            return page

        iterator = PageIterator(fetch_page, items_key="files", model_class=FileMetadata)
        items = list(iterator)

        assert len(items) == 2
        assert all(isinstance(item, FileMetadata) for item in items)
        assert items[0].name == "a.txt"
        assert items[1].name == "b.txt"

    def test_without_model_class_returns_raw_dicts(self):
        """Test that without model_class, raw dicts are returned."""
        def fetch_page(page_token):
            return {"files": [{"id": "f1", "name": "test.txt"}]}

        iterator = PageIterator(fetch_page, items_key="files")
        items = list(iterator)

        assert isinstance(items[0], dict)
        assert items[0]["id"] == "f1"


class TestPageIteratorList:
    """Tests for collecting all items with list()."""

    def test_list_collects_all_items(self):
        """Test that list() collects all items across pages."""
        pages = [
            {"files": [{"id": "1"}, {"id": "2"}], "nextPageToken": "t1"},
            {"files": [{"id": "3"}]},
        ]
        idx = 0

        def fetch_page(page_token):
            nonlocal idx
            page = pages[idx]
            idx += 1
            return page

        iterator = PageIterator(fetch_page, items_key="files")
        all_items = list(iterator)

        assert len(all_items) == 3

    def test_for_loop_iteration(self):
        """Test that for-loop iteration works correctly."""
        def fetch_page(page_token):
            return {"items": [{"value": 1}, {"value": 2}]}

        iterator = PageIterator(fetch_page, items_key="items")
        collected = []
        for item in iterator:
            collected.append(item["value"])

        assert collected == [1, 2]

    def test_iterator_protocol(self):
        """Test that PageIterator implements the iterator protocol."""
        def fetch_page(page_token):
            return {"items": [{"v": 1}]}

        iterator = PageIterator(fetch_page, items_key="items")

        # __iter__ returns self
        assert iter(iterator) is iterator

        # __next__ returns items
        item = next(iterator)
        assert item == {"v": 1}

        # StopIteration when exhausted
        with pytest.raises(StopIteration):
            next(iterator)


class TestPageIteratorEdgeCases:
    """Edge case tests for PageIterator."""

    def test_page_with_empty_items_but_next_token(self):
        """Test page with empty items but nextPageToken continues."""
        pages = [
            {"files": [], "nextPageToken": "t1"},
            {"files": [{"id": "f1"}]},
        ]
        idx = 0

        def fetch_page(page_token):
            nonlocal idx
            page = pages[idx]
            idx += 1
            return page

        iterator = PageIterator(fetch_page, items_key="files")
        items = list(iterator)

        assert len(items) == 1
        assert items[0]["id"] == "f1"

    def test_different_items_key(self):
        """Test using a different items_key (e.g., 'messages')."""
        def fetch_page(page_token):
            return {"messages": [{"id": "m1"}, {"id": "m2"}]}

        iterator = PageIterator(fetch_page, items_key="messages")
        items = list(iterator)

        assert len(items) == 2
