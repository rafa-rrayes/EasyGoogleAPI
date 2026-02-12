# Google Drive

`DriveService` wraps the Google Drive API v3. It inherits from `BaseService`, providing automatic retry, error handling, and `.raw` access.

```python
google = GoogleService(credentials_path="creds.json", services=["drive"])
drive = google.drive
```

## Methods

### list_files

```python
def list_files(
    self,
    query: str | None = None,
    page_size: int = 10,
    fields: str = "files(id, name, mimeType, modifiedTime)",
    folder_id: str | None = None,
    page_token: str | None = None,
    order_by: str | None = None,
) -> dict[str, Any]
```

List files in Drive. Returns a dict with `files` (list) and `nextPageToken` (str or None).

When both `query` and `folder_id` are provided, they are combined with `and`.

```python
result = google.drive.list_files(page_size=20, order_by="modifiedTime desc")
for f in result["files"]:
    print(f["name"])

# Paginate
next_page = google.drive.list_files(page_token=result["nextPageToken"])
```

### get_file

```python
def get_file(
    self,
    file_id: str,
    fields: str = "id, name, mimeType, modifiedTime, size, webViewLink",
) -> dict[str, Any]
```

Get file metadata by ID.

```python
meta = google.drive.get_file("abc123")
print(meta["name"], meta["size"])
```

### upload_file

```python
def upload_file(
    self,
    file: str | Path | BinaryIO | bytes,
    name: str | None = None,
    folder_id: str | None = None,
    mime_type: str | None = None,
    description: str | None = None,
    fields: str = "id, name, webViewLink",
    resumable: bool = True,
) -> dict[str, Any]
```

Upload a file to Drive. `file` can be a filesystem path, an open binary stream, or raw bytes.

When `file` is a path, the filename is inferred from it unless `name` is provided. When `file` is bytes or a stream, `name` defaults to `"untitled"` (for bytes) or the stream's `name` attribute.

```python
# From file path
result = google.drive.upload_file("report.pdf", folder_id="folder_id")

# From bytes
result = google.drive.upload_file(b"hello world", name="hello.txt", mime_type="text/plain")

# From stream (e.g. Django UploadedFile)
result = google.drive.upload_file(request.FILES["file"], name="upload.pdf")
```

### download_file

```python
def download_file(
    self,
    file_id: str,
    destination: str | Path | None = None,
) -> Path | bytes
```

Download a file from Drive. If `destination` is provided, the file is written to disk and the `Path` is returned. Otherwise, the file content is returned as `bytes`.

```python
# Download to file
path = google.drive.download_file("abc123", destination="local.pdf")

# Download to memory
content = google.drive.download_file("abc123")
```

### update_file

```python
def update_file(
    self,
    file_id: str,
    new_content: str | Path | BinaryIO | bytes | None = None,
    new_name: str | None = None,
    description: str | None = None,
    mime_type: str | None = None,
    fields: str = "id, name, modifiedTime",
) -> dict[str, Any]
```

Update a file's content and/or metadata. `new_content` accepts the same types as `upload_file`.

```python
# Rename
google.drive.update_file("abc123", new_name="renamed.pdf")

# Replace content
google.drive.update_file("abc123", new_content=b"new content")
```

### copy_file

```python
def copy_file(
    self,
    file_id: str,
    name: str | None = None,
    folder_id: str | None = None,
    fields: str = "id, name, webViewLink",
) -> dict[str, Any]
```

Copy a file. Optionally rename and/or place in a different folder.

```python
copy = google.drive.copy_file("abc123", name="Copy of Report")
```

### move_file

```python
def move_file(
    self,
    file_id: str,
    new_parent_id: str,
    fields: str = "id, name, parents",
) -> dict[str, Any]
```

Move a file to a different folder. The file is removed from its current parent(s) and added to `new_parent_id`.

```python
google.drive.move_file("abc123", new_parent_id="folder_456")
```

### delete_file

```python
def delete_file(self, file_id: str, permanent: bool = True) -> None
```

Delete a file. If `permanent` is `False`, the file is moved to trash instead (calls `trash_file` internally).

```python
google.drive.delete_file("abc123")                # Permanent delete
google.drive.delete_file("abc123", permanent=False)  # Trash
```

### trash_file

```python
def trash_file(self, file_id: str) -> dict[str, Any]
```

Move a file to the trash. Returns the updated file metadata with `trashed=True`.

```python
google.drive.trash_file("abc123")
```

### restore_file

```python
def restore_file(self, file_id: str) -> dict[str, Any]
```

Restore a file from the trash. Returns the updated file metadata with `trashed=False`.

```python
google.drive.restore_file("abc123")
```

### empty_trash

```python
def empty_trash(self) -> None
```

Permanently delete all files in the trash.

```python
google.drive.empty_trash()
```

### create_folder

```python
def create_folder(self, name: str, parent_id: str | None = None) -> dict[str, Any]
```

Create a folder in Drive. Returns a dict with `id` and `name`.

```python
folder = google.drive.create_folder("Project Docs")
folder = google.drive.create_folder("Subfolder", parent_id="parent_id")
```

### get_or_create_folder

```python
def get_or_create_folder(
    self,
    name: str,
    parent_id: str | None = None,
) -> dict[str, Any]
```

Get an existing folder by name, or create it if it doesn't exist. Searches for non-trashed folders matching the name (and optionally parent). Returns a dict with `id` and `name`.

```python
folder = google.drive.get_or_create_folder("Uploads")
```

### share_file

```python
def share_file(
    self,
    file_id: str,
    email: str,
    role: str = "reader",
    send_notification: bool = True,
) -> dict[str, Any]
```

Share a file with a specific user by email. `role` can be `"reader"`, `"commenter"`, `"writer"`, or `"organizer"`.

```python
google.drive.share_file("abc123", email="alice@example.com", role="writer")
```

### share_file_public

```python
def share_file_public(self, file_id: str, role: str = "reader") -> dict[str, Any]
```

Make a file publicly accessible (anyone with the link).

```python
google.drive.share_file_public("abc123")
```

### list_permissions

```python
def list_permissions(self, file_id: str) -> list[dict[str, Any]]
```

List all permissions on a file. Returns a list of permission dicts with `id`, `role`, `type`, and `emailAddress`.

```python
perms = google.drive.list_permissions("abc123")
```

### remove_permission

```python
def remove_permission(self, file_id: str, permission_id: str) -> None
```

Remove a specific permission from a file.

```python
google.drive.remove_permission("abc123", permission_id="perm_456")
```

### export_file

```python
def export_file(
    self,
    file_id: str,
    mime_type: str,
    destination: str | Path | None = None,
) -> Path | bytes
```

Export a Google Workspace file (Docs, Sheets, Slides) to the specified MIME type. `mime_type` can be a full MIME string (e.g. `"application/pdf"`) or a short alias from `EXPORT_MIME_TYPES` (e.g. `"pdf"`).

If `destination` is provided, the file is written to disk and the `Path` is returned. Otherwise bytes are returned.

```python
# Export Google Doc as PDF
pdf_bytes = google.drive.export_file("doc_id", "pdf")

# Export to file
google.drive.export_file("doc_id", "docx", destination="document.docx")
```

### get_storage_quota

```python
def get_storage_quota(self) -> dict[str, Any]
```

Get Drive storage quota information. Returns a dict with `limit`, `usage`, `usageInDrive`, and `usageInDriveTrash` (all as strings representing bytes).

```python
quota = google.drive.get_storage_quota()
print(f"Used: {quota['usage']} / {quota['limit']}")
```

## EXPORT_MIME_TYPES

A dict mapping short aliases to full MIME types, used by `export_file()`:

| Alias | MIME Type |
|-------|-----------|
| `pdf` | `application/pdf` |
| `docx` | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` |
| `xlsx` | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` |
| `pptx` | `application/vnd.openxmlformats-officedocument.presentationml.presentation` |
| `csv` | `text/csv` |
| `tsv` | `text/tab-separated-values` |
| `txt` | `text/plain` |
| `html` | `text/html` |
| `rtf` | `application/rtf` |
| `odt` | `application/vnd.oasis.opendocument.text` |
| `ods` | `application/vnd.oasis.opendocument.spreadsheet` |
| `png` | `image/png` |
| `jpeg` | `image/jpeg` |
| `svg` | `image/svg+xml` |
| `epub` | `application/epub+zip` |
