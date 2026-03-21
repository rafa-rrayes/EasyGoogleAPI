"""Google Docs API wrapper."""

from typing import Any

from .._base import BaseService
from .models import BatchUpdateResponse, Document


class DocsService(BaseService):
    """Wrapper for Google Docs API operations."""

    def get_document(self, document_id: str) -> Document:
        """Get a document by ID."""
        request = self._resource.documents().get(documentId=document_id)
        result = self._execute_request(request)
        return Document.from_api_response(result)

    def create_document(self, title: str) -> Document:
        """Create a new document."""
        body = {"title": title}
        request = self._resource.documents().create(body=body)
        result = self._execute_request(request)
        return Document.from_api_response(result)

    def batch_update(
        self, document_id: str, requests: list[dict[str, Any]]
    ) -> BatchUpdateResponse:
        """Apply batch updates to a document."""
        body = {"requests": requests}
        request = self._resource.documents().batchUpdate(
            documentId=document_id, body=body
        )
        result = self._execute_request(request)
        return BatchUpdateResponse.from_api_response(result)

    def insert_text(
        self, document_id: str, text: str, index: int = 1
    ) -> BatchUpdateResponse:
        """Insert text at a specific index."""
        requests = [
            {"insertText": {"location": {"index": index}, "text": text}}
        ]
        return self.batch_update(document_id, requests)

    def replace_text(
        self, document_id: str, old_text: str, new_text: str
    ) -> BatchUpdateResponse:
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
