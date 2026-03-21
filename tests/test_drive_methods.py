"""Unit tests for DriveService methods (mock-based, v2.0 typed models)."""

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from easygoogleapi.drive.service import EXPORT_MIME_TYPES, DriveService
from easygoogleapi.drive.models import FileMetadata, FileList, Permission, StorageQuota


@pytest.fixture
def drive():
    """Create a DriveService with a mocked resource."""
    resource = MagicMock()
    return DriveService(resource)


class TestListFilesPage:
    """Tests for list_files_page (single-page)."""

    def test_returns_file_list_model(self, drive):
        drive._resource.files().list().execute.return_value = {
            "files": [{"id": "1", "name": "a.txt"}],
            "nextPageToken": "abc",
        }
        result = drive.list_files_page()
        assert isinstance(result, FileList)
        assert len(result.files) == 1
        assert result.files[0].id == "1"
        assert result.next_page_token == "abc"

    def test_folder_id_filter(self, drive):
        drive._resource.files().list().execute.return_value = {"files": []}
        drive.list_files_page(folder_id="folder_123")
        call_kwargs = drive._resource.files().list.call_args
        assert "'folder_123' in parents" in call_kwargs.kwargs.get("q", "")


class TestListFiles:
    """Tests for list_files (PageIterator)."""

    def test_returns_iterator(self, drive):
        drive._resource.files().list().execute.return_value = {
            "files": [{"id": "1", "name": "a.txt"}],
        }
        result = drive.list_files()
        from easygoogleapi._pagination import PageIterator
        assert isinstance(result, PageIterator)


class TestGetFile:

    def test_returns_file_metadata(self, drive):
        drive._resource.files().get().execute.return_value = {
            "id": "f1", "name": "test.txt", "mimeType": "text/plain"
        }
        result = drive.get_file("f1")
        assert isinstance(result, FileMetadata)
        assert result.id == "f1"
        assert result.name == "test.txt"


class TestUploadFile:

    def test_upload_bytes(self, drive):
        drive._resource.files().create().execute.return_value = {
            "id": "new_id", "name": "data.bin",
        }
        result = drive.upload_file(b"hello world", name="data.bin")
        assert isinstance(result, FileMetadata)
        assert result.id == "new_id"

    def test_upload_bytesio(self, drive):
        drive._resource.files().create().execute.return_value = {
            "id": "new_id", "name": "stream.bin",
        }
        buf = io.BytesIO(b"stream data")
        result = drive.upload_file(buf, name="stream.bin")
        assert isinstance(result, FileMetadata)
        assert result.id == "new_id"


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

    def test_update_metadata_returns_model(self, drive):
        drive._resource.files().update().execute.return_value = {
            "id": "f1", "name": "renamed.txt",
        }
        result = drive.update_file("f1", new_name="renamed.txt")
        assert isinstance(result, FileMetadata)
        assert result.name == "renamed.txt"


class TestCopyFile:

    def test_copy_file(self, drive):
        drive._resource.files().copy().execute.return_value = {
            "id": "copy_id", "name": "Copy of file",
        }
        result = drive.copy_file("f1", name="Copy of file")
        assert isinstance(result, FileMetadata)
        assert result.id == "copy_id"


class TestMoveFile:

    def test_move_file(self, drive):
        drive._resource.files().get().execute.return_value = {"parents": ["old"]}
        drive._resource.files().update().execute.return_value = {
            "id": "f1", "name": "file.txt", "parents": ["new_parent"],
        }
        result = drive.move_file("f1", "new_parent")
        assert isinstance(result, FileMetadata)
        assert result.parents == ["new_parent"]


class TestTrashAndRestore:

    def test_trash_file(self, drive):
        drive._resource.files().update().execute.return_value = {
            "id": "f1", "trashed": True,
        }
        result = drive.trash_file("f1")
        assert isinstance(result, FileMetadata)
        assert result.trashed is True

    def test_restore_file(self, drive):
        drive._resource.files().update().execute.return_value = {
            "id": "f1", "trashed": False,
        }
        result = drive.restore_file("f1")
        assert result.trashed is False

    def test_delete_file_permanent_false_calls_trash(self, drive):
        drive._resource.files().update().execute.return_value = {
            "id": "f1", "trashed": True,
        }
        drive.delete_file("f1", permanent=False)
        drive._resource.files().update.assert_called()

    def test_empty_trash(self, drive):
        drive._resource.files().emptyTrash().execute.return_value = None
        drive.empty_trash()


class TestPermissions:

    def test_share_file(self, drive):
        drive._resource.permissions().create().execute.return_value = {
            "id": "perm1", "role": "reader", "emailAddress": "u@x.com",
        }
        result = drive.share_file("f1", "u@x.com")
        assert isinstance(result, Permission)
        assert result.role == "reader"

    def test_share_file_public(self, drive):
        drive._resource.permissions().create().execute.return_value = {
            "id": "perm2", "role": "reader",
        }
        result = drive.share_file_public("f1")
        assert isinstance(result, Permission)
        assert result.role == "reader"

    def test_list_permissions(self, drive):
        drive._resource.permissions().list().execute.return_value = {
            "permissions": [{"id": "p1", "role": "owner"}],
        }
        result = drive.list_permissions("f1")
        assert len(result) == 1
        assert isinstance(result[0], Permission)

    def test_remove_permission(self, drive):
        drive._resource.permissions().delete().execute.return_value = None
        drive.remove_permission("f1", "perm1")


class TestGetOrCreateFolder:

    def test_returns_existing_folder(self, drive):
        drive._resource.files().list().execute.return_value = {
            "files": [{"id": "existing", "name": "MyFolder"}],
        }
        result = drive.get_or_create_folder("MyFolder")
        assert isinstance(result, FileMetadata)
        assert result.id == "existing"

    def test_creates_folder_if_not_found(self, drive):
        drive._resource.files().list().execute.return_value = {"files": []}
        drive._resource.files().create().execute.return_value = {
            "id": "new_folder", "name": "MyFolder",
        }
        result = drive.get_or_create_folder("MyFolder")
        assert isinstance(result, FileMetadata)
        assert result.id == "new_folder"

    def test_escapes_single_quotes_in_name(self, drive):
        """Test query injection fix."""
        drive._resource.files().list().execute.return_value = {"files": []}
        drive._resource.files().create().execute.return_value = {
            "id": "new", "name": "Bob's Folder",
        }
        drive.get_or_create_folder("Bob's Folder")
        call_kwargs = drive._resource.files().list.call_args
        q = call_kwargs.kwargs.get("q", "")
        assert "Bob\\'s Folder" in q


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
        assert isinstance(result, StorageQuota)
        assert result.limit == "16106127360"
        assert result.usage == "1234567890"


class TestNewMethods:
    """Tests for Phase 7 new methods."""

    def test_search_returns_iterator(self, drive):
        result = drive.search("fullText contains 'report'")
        from easygoogleapi._pagination import PageIterator
        assert isinstance(result, PageIterator)

    def test_create_shortcut(self, drive):
        drive._resource.files().create().execute.return_value = {
            "id": "sc1", "name": "Shortcut", "mimeType": "application/vnd.google-apps.shortcut",
        }
        result = drive.create_shortcut("target_id", "Shortcut")
        assert isinstance(result, FileMetadata)
        assert result.id == "sc1"

    def test_list_shared_drives(self, drive):
        drive._resource.drives().list().execute.return_value = {
            "drives": [{"id": "d1", "name": "Shared"}],
        }
        result = drive.list_shared_drives()
        assert len(result) == 1
        assert isinstance(result[0], FileMetadata)

    def test_list_file_versions(self, drive):
        drive._resource.revisions().list().execute.return_value = {
            "revisions": [{"id": "rev1"}],
        }
        result = drive.list_file_versions("f1")
        assert len(result) == 1
