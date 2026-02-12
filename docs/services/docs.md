# Google Docs

`DocsService` wraps the Google Docs API v1. It inherits from `BaseService`, providing automatic retry, error handling, and `.raw` access.

```python
google = GoogleService(credentials_path="creds.json", services=["docs"])
docs = google.docs
```

## Methods

### get_document

```python
def get_document(self, document_id: str) -> dict[str, Any]
```

Get a document by ID. Returns the full document resource including `title`, `body`, `headers`, `footers`, etc.

```python
doc = google.docs.get_document("document_id_here")
print(doc["title"])
```

### create_document

```python
def create_document(self, title: str) -> dict[str, Any]
```

Create a new blank document with the given title.

```python
doc = google.docs.create_document("Meeting Notes")
print(doc["documentId"])
```

### batch_update

```python
def batch_update(
    self,
    document_id: str,
    requests: list[dict[str, Any]],
) -> dict[str, Any]
```

Apply batch updates to a document. Use this for advanced operations like formatting, inserting tables, images, etc.

- `requests`: List of Docs API request objects (see [Google Docs API batchUpdate reference](https://developers.google.com/docs/api/reference/rest/v1/documents/batchUpdate)).

```python
google.docs.batch_update("doc_id", [
    {"insertText": {"location": {"index": 1}, "text": "Hello World\n"}},
    {
        "updateTextStyle": {
            "range": {"startIndex": 1, "endIndex": 12},
            "textStyle": {"bold": True},
            "fields": "bold",
        }
    },
])
```

### insert_text

```python
def insert_text(
    self,
    document_id: str,
    text: str,
    index: int = 1,
) -> dict[str, Any]
```

Insert text at a specific index in the document. Defaults to the beginning of the document body (index 1).

Internally calls `batch_update` with an `insertText` request.

```python
google.docs.insert_text("doc_id", "Hello World\n")
google.docs.insert_text("doc_id", "Appended text", index=50)
```

### replace_text

```python
def replace_text(
    self,
    document_id: str,
    old_text: str,
    new_text: str,
) -> dict[str, Any]
```

Replace all occurrences of `old_text` with `new_text` in the document. The search is case-sensitive.

Internally calls `batch_update` with a `replaceAllText` request.

```python
google.docs.replace_text("doc_id", "{{name}}", "Alice Johnson")
```
