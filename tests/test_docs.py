"""Integration tests for Docs service."""

import pytest


@pytest.mark.integration
class TestDocsService:
    """Integration tests for DocsService."""

    @pytest.fixture
    def test_document(self, google_docs):
        """Create a test document and clean it up after."""
        document = google_docs.docs.create_document("Test_EasyGoogleAPI_Doc")
        yield document
        # Note: Docs API can't delete, would need Drive API

    def test_create_document(self, google_docs):
        """Test creating a document."""
        document = google_docs.docs.create_document("Test_Create_Document")
        assert "documentId" in document
        assert document["title"] == "Test_Create_Document"

    def test_get_document(self, google_docs, test_document):
        """Test getting document content."""
        document = google_docs.docs.get_document(test_document["documentId"])
        assert "documentId" in document
        assert "body" in document

    def test_insert_text(self, google_docs, test_document):
        """Test inserting text into a document."""
        doc_id = test_document["documentId"]

        result = google_docs.docs.insert_text(
            doc_id, "Hello from EasyGoogleAPI!", index=1
        )
        assert "replies" in result

        # Verify text was inserted
        document = google_docs.docs.get_document(doc_id)
        content = document["body"]["content"]
        # Content should contain our text
        text_found = False
        for element in content:
            if "paragraph" in element:
                for elem in element["paragraph"].get("elements", []):
                    if "textRun" in elem:
                        if "Hello from EasyGoogleAPI!" in elem["textRun"]["content"]:
                            text_found = True
        assert text_found

    def test_replace_text(self, google_docs, test_document):
        """Test replacing text in a document."""
        doc_id = test_document["documentId"]

        # First insert some text
        google_docs.docs.insert_text(doc_id, "PLACEHOLDER_TEXT", index=1)

        # Replace it
        result = google_docs.docs.replace_text(
            doc_id, "PLACEHOLDER_TEXT", "REPLACED_TEXT"
        )
        assert "replies" in result

    def test_batch_update(self, google_docs, test_document):
        """Test batch update with custom requests."""
        doc_id = test_document["documentId"]

        requests = [
            {
                "insertText": {
                    "location": {"index": 1},
                    "text": "Batch update text\n",
                }
            }
        ]

        result = google_docs.docs.batch_update(doc_id, requests)
        assert "replies" in result
