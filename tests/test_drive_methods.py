"""Unit tests for new Drive service methods (mock-based)."""

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from easygoogleapi.drive.service import EXPORT_MIME_TYPES, DriveService


@pytest.fixture
def drive():
    """Create a DriveService with a mocked resource."""
    resource = MagicMock()
    return DriveService(resource)


class TestListFiles:
    """Tests for list_files method."""

    def test_returns_dict_with_files_and_next_page_token(self, drive):
        drive._resource.files().list().execute.return_value = {
            "files": [{"id": "1"}],
            "nextPageToken": "abc",
        }
        result = drive.list_files()
        assert "files" in result
        assert "nextPageToken" in result
        assert result["files"] == [{"id": "1"}]
        assert result["nextPageToken"] == "abc"

    def test_folder_id_appends_to_query(self, drive):
        drive._resource.files().list().execute.return_value = {"files": []}
        drive.list_files(folder_id="folder_123")
        call_kwargs = drive._resource.files().list.call_args
        assert "'folder_123' in parents" in call_kwargs.kwargs.get("q", "")

    def test_order_by_and_page_token(self, drive):
        drive._resource.files().list().execute.return_value = {"files": []}
        drive.list_files(order_by="modifiedTime desc", page_token="tok")
        call_kwargs = drive._resource.files().list.call_args
        assert call_kwargs.kwargs.get("orderBy") == "modifiedTime desc"
        assert call_kwargs.kwargs.get("pageToken") == "tok"


class TestGetFile:

    def test_get_file_calls_api(self, drive):
        drive._resource.files().get().execute.return_value = {"id": "f1", "name": "test.txt"}
        result = drive.get_file("f1")
        assert result["id"] == "f1"


class TestUploadFile:

    def test_upload_bytes(self, drive):
        drive._resource.files().create().execute.return_value = {
            "id": "new_id",
            "name": "data.bin",
        }
        result = drive.upload_file(b"hello world", name="data.bin")
        assert result["id"] == "new_id"

    def test_upload_bytesio(self, drive):
        drive._resource.files().create().execute.return_value = {
            "id": "new_id",
            "name": "stream.bin",
        }
        buf = io.BytesIO(b"stream data")
        result = drive.upload_file(buf, name="stream.bin")
        assert result["id"] == "new_id"


class TestDownloadFile:

    @patch("easygoogleapi.drive.service.MediaIoBaseDownload")
    def test_download_returns_bytes_when_no_destination(self, mock_dl, drive):
        mock_dl_instance = MagicMock()
        mock_dl_instance.next_chunk.return_value = (None, True)
        mock_dl.return_value = mock_dl_instance
        drive._resource.files().get_media.return_value = MagicMock()

        result = drive.download_file("f1")
        assert isinstance(result, bytes)


class TestUpdateFile:

    def test_update_metadata_only(self, drive):
        drive._resource.files().update().execute.return_value = {
            "id": "f1",
            "name": "renamed.txt",
        }
        result = drive.update_file("f1", new_name="renamed.txt")
        assert result["name"] == "renamed.txt"


class TestCopyFile:

    def test_copy_file(self, drive):
        drive._resource.files().copy().execute.return_value = {
            "id": "copy_id",
            "name": "Copy of file",
        }
        result = drive.copy_file("f1", name="Copy of file")
        assert result["id"] == "copy_id"


class TestMoveFile:

    def test_move_file(self, drive):
        drive._resource.files().get().execute.return_value = {"parents": ["old_parent"]}
        drive._resource.files().update().execute.return_value = {
            "id": "f1",
            "parents": ["new_parent"],
        }
        result = drive.move_file("f1", "new_parent")
        assert result["parents"] == ["new_parent"]


class TestTrashAndRestore:

    def test_trash_file(self, drive):
        drive._resource.files().update().execute.return_value = {
            "id": "f1",
            "trashed": True,
        }
        result = drive.trash_file("f1")
        assert result["trashed"] is True

    def test_restore_file(self, drive):
        drive._resource.files().update().execute.return_value = {
            "id": "f1",
            "trashed": False,
        }
        result = drive.restore_file("f1")
        assert result["trashed"] is False

    def test_delete_file_permanent_false_calls_trash(self, drive):
        drive._resource.files().update().execute.return_value = {
            "id": "f1",
            "trashed": True,
        }
        drive.delete_file("f1", permanent=False)
        # Should have called update (trash) not delete
        drive._resource.files().update.assert_called()

    def test_empty_trash(self, drive):
        drive._resource.files().emptyTrash().execute.return_value = None
        drive.empty_trash()


class TestPermissions:

    def test_share_file(self, drive):
        drive._resource.permissions().create().execute.return_value = {
            "id": "perm1",
            "role": "reader",
        }
        result = drive.share_file("f1", "user@example.com")
        assert result["role"] == "reader"

    def test_share_file_public(self, drive):
        drive._resource.permissions().create().execute.return_value = {
            "id": "perm2",
            "role": "reader",
        }
        result = drive.share_file_public("f1")
        assert result["role"] == "reader"

    def test_list_permissions(self, drive):
        drive._resource.permissions().list().execute.return_value = {
            "permissions": [{"id": "p1", "role": "owner"}],
        }
        result = drive.list_permissions("f1")
        assert len(result) == 1

    def test_remove_permission(self, drive):
        drive._resource.permissions().delete().execute.return_value = None
        drive.remove_permission("f1", "perm1")


class TestGetOrCreateFolder:

    def test_returns_existing_folder(self, drive):
        drive._resource.files().list().execute.return_value = {
            "files": [{"id": "existing", "name": "MyFolder"}],
        }
        result = drive.get_or_create_folder("MyFolder")
        assert result["id"] == "existing"

    def test_creates_folder_if_not_found(self, drive):
        drive._resource.files().list().execute.return_value = {"files": []}
        drive._resource.files().create().execute.return_value = {
            "id": "new_folder",
            "name": "MyFolder",
        }
        result = drive.get_or_create_folder("MyFolder")
        assert result["id"] == "new_folder"


class TestExportMimeTypes:

    def test_export_mime_types_contains_pdf(self):
        assert "pdf" in EXPORT_MIME_TYPES
        assert EXPORT_MIME_TYPES["pdf"] == "application/pdf"

    def test_export_mime_types_contains_common_formats(self):
        for fmt in ("docx", "xlsx", "csv", "html", "png"):
            assert fmt in EXPORT_MIME_TYPES


class TestGetStorageQuota:

    def test_get_storage_quota(self, drive):
        drive._resource.about().get().execute.return_value = {
            "storageQuota": {
                "limit": "16106127360",
                "usage": "1234567890",
            }
        }
        result = drive.get_storage_quota()
        assert "limit" in result
        assert "usage" in result
