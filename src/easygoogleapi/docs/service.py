"""Google Docs API wrapper."""

from typing import Any

from .._base import BaseService


class DocsService(BaseService):
    """Wrapper for Google Docs API operations."""

    def get_document(self, document_id: str) -> dict[str, Any]:
        """Get a document by ID."""
        request = self._resource.documents().get(documentId=document_id)
        return self._execute_request(request)

    def create_document(self, title: str) -> dict[str, Any]:
        """Create a new document."""
        body = {"title": title}
        request = self._resource.documents().create(body=body)
        return self._execute_request(request)

    def batch_update(
        self, document_id: str, requests: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Apply batch updates to a document."""
        body = {"requests": requests}
        request = self._resource.documents().batchUpdate(
            documentId=document_id, body=body
        )
        return self._execute_request(request)

    def insert_text(
        self, document_id: str, text: str, index: int = 1
    ) -> dict[str, Any]:
        """Insert text at a specific index."""
        requests = [
            {"insertText": {"location": {"index": index}, "text": text}}
        ]
        return self.batch_update(document_id, requests)

    def replace_text(
        self, document_id: str, old_text: str, new_text: str
    ) -> dict[str, Any]:
        """Replace all occurrences of text."""
        requests = [
            {
                "replaceAllText": {
                    "containsText": {"text": old_text, "matchCase": True},
                    "replaceText": new_text,
                }
            }
        ]
        return self.batch_update(document_id, requests)
