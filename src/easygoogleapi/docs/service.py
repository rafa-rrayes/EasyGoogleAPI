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

    # ------------------------------------------------------------------
    # Append / Images / Tables / Styling
    # ------------------------------------------------------------------

    def append_text(
        self, document_id: str, text: str
    ) -> BatchUpdateResponse:
        """Append text at the end of the document.

        Reads the document to determine the current end index, then
        inserts text at that position.
        """
        doc = self.get_document(document_id)
        body_content = doc.body.get("content", [])
        end_index = body_content[-1].get("endIndex", 1) - 1 if body_content else 1
        return self.insert_text(document_id, text, index=end_index)

    def insert_image(
        self, document_id: str, image_url: str, index: int = 1
    ) -> BatchUpdateResponse:
        """Insert an image from a URL at the given index."""
        requests = [
            {
                "insertInlineImage": {
                    "location": {"index": index},
                    "uri": image_url,
                }
            }
        ]
        return self.batch_update(document_id, requests)

    def insert_table(
        self, document_id: str, rows: int, cols: int, index: int = 1
    ) -> BatchUpdateResponse:
        """Insert a table at the given index."""
        requests = [
            {
                "insertTable": {
                    "rows": rows,
                    "columns": cols,
                    "location": {"index": index},
                }
            }
        ]
        return self.batch_update(document_id, requests)

    def apply_style(
        self,
        document_id: str,
        start_index: int,
        end_index: int,
        style: dict,
    ) -> BatchUpdateResponse:
        """Apply a text style to a range of the document.

        ``style`` should be a dict of Docs API TextStyle fields, e.g.
        ``{"bold": True, "fontSize": {"magnitude": 14, "unit": "PT"}}``.
        """
        fields = ",".join(style.keys())
        requests = [
            {
                "updateTextStyle": {
                    "range": {
                        "startIndex": start_index,
                        "endIndex": end_index,
                    },
                    "textStyle": style,
                    "fields": fields,
                }
            }
        ]
        return self.batch_update(document_id, requests)
