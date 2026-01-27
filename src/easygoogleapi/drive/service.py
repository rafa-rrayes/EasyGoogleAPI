"""Google Drive API wrapper."""

from pathlib import Path
from typing import Any

from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

from .._base import BaseService


class DriveService(BaseService):
    """Wrapper for Google Drive API operations."""

    def list_files(
        self,
        query: str | None = None,
        page_size: int = 10,
        fields: str = "files(id, name, mimeType, modifiedTime)",
    ) -> list[dict[str, Any]]:
        """List files in Drive."""
        kwargs: dict[str, Any] = {
            "pageSize": page_size,
            "fields": f"nextPageToken, {fields}",
        }
        if query:
            kwargs["q"] = query

        request = self._resource.files().list(**kwargs)
        result = self._execute_request(request)
        return result.get("files", [])

    def upload_file(
        self,
        file_path: str | Path,
        name: str | None = None,
        folder_id: str | None = None,
        mime_type: str | None = None,
    ) -> dict[str, Any]:
        """Upload a file to Drive."""
        file_path = Path(file_path)
        file_name = name or file_path.name

        file_metadata: dict[str, Any] = {"name": file_name}
        if folder_id:
            file_metadata["parents"] = [folder_id]

        media = MediaFileUpload(str(file_path), mimetype=mime_type)
        request = self._resource.files().create(
            body=file_metadata, media_body=media, fields="id, name, webViewLink"
        )
        return self._execute_request(request)

    def download_file(
        self, file_id: str, destination: str | Path
    ) -> Path:
        """Download a file from Drive."""
        destination = Path(destination)
        request = self._resource.files().get_media(fileId=file_id)

        with open(destination, "wb") as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

        return destination

    def delete_file(self, file_id: str) -> None:
        """Delete a file from Drive."""
        request = self._resource.files().delete(fileId=file_id)
        self._execute_request(request)

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
