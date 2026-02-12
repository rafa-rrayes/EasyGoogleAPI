"""Google Drive API wrapper."""

import io
from pathlib import Path
from typing import Any, BinaryIO

from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload, MediaIoBaseUpload

from .._base import BaseService

# Mapping from Google Workspace MIME types to export formats
EXPORT_MIME_TYPES: dict[str, str] = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "csv": "text/csv",
    "tsv": "text/tab-separated-values",
    "txt": "text/plain",
    "html": "text/html",
    "rtf": "application/rtf",
    "odt": "application/vnd.oasis.opendocument.text",
    "ods": "application/vnd.oasis.opendocument.spreadsheet",
    "png": "image/png",
    "jpeg": "image/jpeg",
    "svg": "image/svg+xml",
    "epub": "application/epub+zip",
}


class DriveService(BaseService):
    """Wrapper for Google Drive API operations."""

    # ------------------------------------------------------------------
    # List / Query
    # ------------------------------------------------------------------

    def list_files(
        self,
        query: str | None = None,
        page_size: int = 10,
        fields: str = "files(id, name, mimeType, modifiedTime)",
        folder_id: str | None = None,
        page_token: str | None = None,
        order_by: str | None = None,
    ) -> dict[str, Any]:
        """List files in Drive.

        Returns a dict with ``files`` and ``nextPageToken`` keys.
        """
        kwargs: dict[str, Any] = {
            "pageSize": page_size,
            "fields": f"nextPageToken, {fields}",
        }

        # Build query
        parts: list[str] = []
        if query:
            parts.append(query)
        if folder_id:
            parts.append(f"'{folder_id}' in parents")
        if parts:
            kwargs["q"] = " and ".join(parts)

        if page_token:
            kwargs["pageToken"] = page_token
        if order_by:
            kwargs["orderBy"] = order_by

        request = self._resource.files().list(**kwargs)
        result = self._execute_request(request)
        return {
            "files": result.get("files", []),
            "nextPageToken": result.get("nextPageToken"),
        }

    # ------------------------------------------------------------------
    # Get / Upload / Download
    # ------------------------------------------------------------------

    def get_file(
        self,
        file_id: str,
        fields: str = "id, name, mimeType, modifiedTime, size, webViewLink",
    ) -> dict[str, Any]:
        """Get file metadata."""
        request = self._resource.files().get(fileId=file_id, fields=fields)
        return self._execute_request(request)

    def upload_file(
        self,
        file: str | Path | BinaryIO | bytes,
        name: str | None = None,
        folder_id: str | None = None,
        mime_type: str | None = None,
        description: str | None = None,
        fields: str = "id, name, webViewLink",
        resumable: bool = True,
    ) -> dict[str, Any]:
        """Upload a file to Drive.

        ``file`` can be a filesystem path, an open binary stream, or raw bytes.
        """
        if isinstance(file, (str, Path)):
            file_path = Path(file)
            file_name = name or file_path.name
            media = MediaFileUpload(
                str(file_path), mimetype=mime_type, resumable=resumable
            )
        elif isinstance(file, bytes):
            file_name = name or "untitled"
            media = MediaIoBaseUpload(
                io.BytesIO(file),
                mimetype=mime_type or "application/octet-stream",
                resumable=resumable,
            )
        else:
            # BinaryIO / file-like
            file_name = name or getattr(file, "name", "untitled")
            media = MediaIoBaseUpload(
                file,
                mimetype=mime_type or "application/octet-stream",
                resumable=resumable,
            )

        file_metadata: dict[str, Any] = {"name": file_name}
        if folder_id:
            file_metadata["parents"] = [folder_id]
        if description:
            file_metadata["description"] = description

        request = self._resource.files().create(
            body=file_metadata, media_body=media, fields=fields
        )
        return self._execute_request(request)

    def download_file(
        self,
        file_id: str,
        destination: str | Path | None = None,
    ) -> Path | bytes:
        """Download a file from Drive.

        If *destination* is provided the file is written to disk and the
        ``Path`` is returned.  Otherwise the file content is returned as
        ``bytes``.
        """
        request = self._resource.files().get_media(fileId=file_id)

        if destination is not None:
            destination = Path(destination)
            with open(destination, "wb") as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    _, done = downloader.next_chunk()
            return destination

        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return buf.getvalue()

    # ------------------------------------------------------------------
    # Update / Copy / Move
    # ------------------------------------------------------------------

    def update_file(
        self,
        file_id: str,
        new_content: str | Path | BinaryIO | bytes | None = None,
        new_name: str | None = None,
        description: str | None = None,
        mime_type: str | None = None,
        fields: str = "id, name, modifiedTime",
    ) -> dict[str, Any]:
        """Update a file's content and/or metadata."""
        body: dict[str, Any] = {}
        if new_name:
            body["name"] = new_name
        if description is not None:
            body["description"] = description

        media = None
        if new_content is not None:
            if isinstance(new_content, (str, Path)):
                media = MediaFileUpload(str(new_content), mimetype=mime_type)
            elif isinstance(new_content, bytes):
                media = MediaIoBaseUpload(
                    io.BytesIO(new_content),
                    mimetype=mime_type or "application/octet-stream",
                )
            else:
                media = MediaIoBaseUpload(
                    new_content,
                    mimetype=mime_type or "application/octet-stream",
                )

        kwargs: dict[str, Any] = {"fileId": file_id, "fields": fields}
        if body:
            kwargs["body"] = body
        if media:
            kwargs["media_body"] = media

        request = self._resource.files().update(**kwargs)
        return self._execute_request(request)

    def copy_file(
        self,
        file_id: str,
        name: str | None = None,
        folder_id: str | None = None,
        fields: str = "id, name, webViewLink",
    ) -> dict[str, Any]:
        """Copy a file."""
        body: dict[str, Any] = {}
        if name:
            body["name"] = name
        if folder_id:
            body["parents"] = [folder_id]
        request = self._resource.files().copy(
            fileId=file_id, body=body, fields=fields
        )
        return self._execute_request(request)

    def move_file(
        self,
        file_id: str,
        new_parent_id: str,
        fields: str = "id, name, parents",
    ) -> dict[str, Any]:
        """Move a file to a different folder."""
        # Get current parents
        current = self._execute_request(
            self._resource.files().get(fileId=file_id, fields="parents")
        )
        previous_parents = ",".join(current.get("parents", []))

        request = self._resource.files().update(
            fileId=file_id,
            addParents=new_parent_id,
            removeParents=previous_parents,
            fields=fields,
        )
        return self._execute_request(request)

    # ------------------------------------------------------------------
    # Delete / Trash
    # ------------------------------------------------------------------

    def delete_file(self, file_id: str, permanent: bool = True) -> None:
        """Delete a file from Drive.

        If *permanent* is ``False`` the file is moved to trash instead.
        """
        if permanent:
            request = self._resource.files().delete(fileId=file_id)
            self._execute_request(request)
        else:
            self.trash_file(file_id)

    def trash_file(self, file_id: str) -> dict[str, Any]:
        """Move a file to the trash."""
        request = self._resource.files().update(
            fileId=file_id, body={"trashed": True}, fields="id, name, trashed"
        )
        return self._execute_request(request)

    def restore_file(self, file_id: str) -> dict[str, Any]:
        """Restore a file from the trash."""
        request = self._resource.files().update(
            fileId=file_id, body={"trashed": False}, fields="id, name, trashed"
        )
        return self._execute_request(request)

    def empty_trash(self) -> None:
        """Permanently delete all files in the trash."""
        request = self._resource.files().emptyTrash()
        self._execute_request(request)

    # ------------------------------------------------------------------
    # Permissions / Sharing
    # ------------------------------------------------------------------

    def share_file(
        self,
        file_id: str,
        email: str,
        role: str = "reader",
        send_notification: bool = True,
    ) -> dict[str, Any]:
        """Share a file with a specific user.

        Args:
            file_id: The file to share.
            email: Email address of the user to share with.
            role: Permission role (``reader``, ``commenter``, ``writer``,
                ``organizer``).
            send_notification: Whether to send an email notification.
        """
        body = {"type": "user", "role": role, "emailAddress": email}
        request = self._resource.permissions().create(
            fileId=file_id,
            body=body,
            sendNotificationEmail=send_notification,
            fields="id, role, emailAddress",
        )
        return self._execute_request(request)

    def share_file_public(
        self,
        file_id: str,
        role: str = "reader",
    ) -> dict[str, Any]:
        """Make a file publicly accessible."""
        body = {"type": "anyone", "role": role}
        request = self._resource.permissions().create(
            fileId=file_id, body=body, fields="id, role"
        )
        return self._execute_request(request)

    def list_permissions(self, file_id: str) -> list[dict[str, Any]]:
        """List permissions on a file."""
        request = self._resource.permissions().list(
            fileId=file_id, fields="permissions(id, role, type, emailAddress)"
        )
        result = self._execute_request(request)
        return result.get("permissions", [])

    def remove_permission(self, file_id: str, permission_id: str) -> None:
        """Remove a permission from a file."""
        request = self._resource.permissions().delete(
            fileId=file_id, permissionId=permission_id
        )
        self._execute_request(request)

    # ------------------------------------------------------------------
    # Folders
    # ------------------------------------------------------------------

    def create_folder(
        self, name: str, parent_id: str | None = None
    ) -> dict[str, Any]:
        """Create a folder in Drive."""
        file_metadata: dict[str, Any] = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_id:
            file_metadata["parents"] = [parent_id]

        request = self._resource.files().create(
            body=file_metadata, fields="id, name"
        )
        return self._execute_request(request)

    def get_or_create_folder(
        self,
        name: str,
        parent_id: str | None = None,
    ) -> dict[str, Any]:
        """Get an existing folder by name, or create it if it doesn't exist."""
        parts = [
            f"name = '{name}'",
            "mimeType = 'application/vnd.google-apps.folder'",
            "trashed = false",
        ]
        if parent_id:
            parts.append(f"'{parent_id}' in parents")

        result = self._execute_request(
            self._resource.files().list(
                q=" and ".join(parts),
                fields="files(id, name)",
                pageSize=1,
            )
        )
        files = result.get("files", [])
        if files:
            return files[0]
        return self.create_folder(name, parent_id)

    # ------------------------------------------------------------------
    # Export (Google Workspace → other formats)
    # ------------------------------------------------------------------

    def export_file(
        self,
        file_id: str,
        mime_type: str,
        destination: str | Path | None = None,
    ) -> Path | bytes:
        """Export a Google Workspace file to the specified MIME type.

        ``mime_type`` can be a full MIME string (e.g. ``"application/pdf"``)
        or a short alias defined in ``EXPORT_MIME_TYPES`` (e.g. ``"pdf"``).
        """
        resolved_mime = EXPORT_MIME_TYPES.get(mime_type, mime_type)
        request = self._resource.files().export_media(
            fileId=file_id, mimeType=resolved_mime
        )

        if destination is not None:
            destination = Path(destination)
            with open(destination, "wb") as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    _, done = downloader.next_chunk()
            return destination

        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return buf.getvalue()

    # ------------------------------------------------------------------
    # Quota
    # ------------------------------------------------------------------

    def get_storage_quota(self) -> dict[str, Any]:
        """Get Drive storage quota information.

        Returns a dict with ``limit``, ``usage``, ``usageInDrive``,
        ``usageInDriveTrash`` (all in bytes as strings).
        """
        request = self._resource.about().get(
            fields="storageQuota"
        )
        result = self._execute_request(request)
        return result.get("storageQuota", {})
