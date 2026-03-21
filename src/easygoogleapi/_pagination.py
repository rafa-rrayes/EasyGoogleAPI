"""Auto-paginating iterator for Google API list results."""

from collections.abc import Iterator
from typing import Any, Callable, TypeVar

T = TypeVar("T")


class PageIterator(Iterator[T]):
    """Auto-paginating iterator over Google API list results.

    Fetches pages lazily as items are consumed. Users can simply iterate
    over results without manually handling ``nextPageToken``::

        for file in google.drive.list_files():
            print(file.name)

    Or collect all results::

        all_files = list(google.drive.list_files())
    """

    def __init__(
        self,
        fetch_page: Callable[[str | None], dict[str, Any]],
        items_key: str = "files",
        model_class: type[T] | None = None,
    ):
        self._fetch_page = fetch_page
        self._items_key = items_key
        self._model_class = model_class
        self._page_token: str | None = None
        self._buffer: list[Any] = []
        self._exhausted = False
        self._first_page = True

    def __next__(self) -> T:
        while not self._buffer:
            if self._exhausted:
                raise StopIteration
            result = self._fetch_page(self._page_token)
            items = result.get(self._items_key, [])
            self._page_token = result.get("nextPageToken")
            if not self._page_token:
                self._exhausted = True
            if self._model_class:
                self._buffer = [
                    self._model_class.from_api_response(item)  # type: ignore[attr-defined]
                    for item in items
                ]
            else:
                self._buffer = list(items)
            self._first_page = False
            if not self._buffer and self._exhausted:
                raise StopIteration
        return self._buffer.pop(0)

    def __iter__(self) -> "PageIterator[T]":
        return self
