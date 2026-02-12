# Gmail

`GmailService` wraps the Gmail API v1. It inherits from `BaseService`, providing automatic retry, error handling, and `.raw` access.

```python
google = GoogleService(credentials_path="creds.json", services=["gmail"])
gmail = google.gmail
```

## Methods

### send

```python
def send(
    self,
    to: str | list[str],
    subject: str,
    body: str,
    html: bool = False,
    cc: str | list[str] | None = None,
    bcc: str | list[str] | None = None,
    attachments: list[str | Path] | None = None,
    from_name: str | None = None,
    reply_to: str | None = None,
) -> dict[str, Any]
```

Send an email.

- `to`: Recipient email address(es). A list is joined with `", "`.
- `subject`: Email subject line.
- `body`: Email body text (plain text or HTML).
- `html`: If `True`, `body` is treated as HTML content.
- `cc`: CC recipient(s).
- `bcc`: BCC recipient(s).
- `attachments`: List of file paths to attach. Each file is read, base64-encoded, and attached as `application/octet-stream`.
- `from_name`: Display name for the `From` header (e.g. `"My App"`). The email address is filled automatically by Gmail.
- `reply_to`: Sets the `Reply-To` header.

```python
# Simple text email
google.gmail.send(
    to="recipient@example.com",
    subject="Hello",
    body="This is the body.",
)

# HTML email with attachments
google.gmail.send(
    to=["alice@example.com", "bob@example.com"],
    subject="Monthly Report",
    body="<h1>Report</h1><p>Please review.</p>",
    html=True,
    attachments=["report.pdf", "data.xlsx"],
    from_name="My App",
    reply_to="noreply@myapp.com",
)
```

### list_messages

```python
def list_messages(
    self,
    query: str | None = None,
    label_ids: list[str] | None = None,
    max_results: int = 10,
) -> list[dict[str, Any]]
```

List messages matching criteria. Returns a list of message stubs (with `id` and `threadId`). Use `get_message()` to fetch full message content.

- `query`: Gmail search query (same syntax as the Gmail search box, e.g. `"is:unread"`, `"from:alice"`, `"subject:report"`).
- `label_ids`: Filter by label IDs (e.g. `["INBOX"]`, `["UNREAD"]`).

```python
messages = google.gmail.list_messages(query="is:unread", max_results=20)
for msg in messages:
    print(msg["id"])
```

### get_message

```python
def get_message(self, message_id: str, format: str = "full") -> dict[str, Any]
```

Get a specific message by ID. The `format` parameter controls what data is returned:

- `"full"` (default): Returns full message including headers, body, and attachments.
- `"metadata"`: Returns only headers.
- `"minimal"`: Returns only the message ID and labels.
- `"raw"`: Returns the full raw email as a base64url-encoded string.

```python
message = google.gmail.get_message("msg_id_here")
headers = message["payload"]["headers"]
subject = next(h["value"] for h in headers if h["name"] == "Subject")
```

### list_labels

```python
def list_labels(self) -> list[dict[str, Any]]
```

List all labels in the user's mailbox.

```python
labels = google.gmail.list_labels()
for label in labels:
    print(label["name"], label["id"])
```

### trash_message

```python
def trash_message(self, message_id: str) -> dict[str, Any]
```

Move a message to the trash.

```python
google.gmail.trash_message("msg_id_here")
```
