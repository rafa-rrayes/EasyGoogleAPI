"""Integration tests for Drive service."""

import tempfile
from pathlib import Path

import pytest


@pytest.mark.integration
class TestDriveService:
    """Integration tests for DriveService."""

    def test_list_files(self, google_drive):
        """Test listing files."""
        files = google_drive.drive.list_files(page_size=5)
        assert isinstance(files, list)

    def test_upload_and_delete_file(self, google_drive):
        """Test uploading and deleting a file."""
        # Create a temp file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        ) as f:
            f.write("Test content from EasyGoogleAPI")
            temp_path = Path(f.name)

        try:
            # Upload file
            result = google_drive.drive.upload_file(
                temp_path, name="test_upload.txt"
            )

            assert "id" in result
            assert result["name"] == "test_upload.txt"

            # Clean up - delete from Drive
            google_drive.drive.delete_file(result["id"])
        finally:
            # Clean up local file
            temp_path.unlink()

    def test_create_and_delete_folder(self, google_drive):
        """Test creating and deleting a folder."""
        folder = google_drive.drive.create_folder("TestFolder_EasyGoogleAPI")

        assert "id" in folder
        assert folder["name"] == "TestFolder_EasyGoogleAPI"

        # Clean up
        google_drive.drive.delete_file(folder["id"])

    def test_upload_to_folder(self, google_drive):
        """Test uploading a file to a specific folder."""
        # Create folder
        folder = google_drive.drive.create_folder("TestUploadFolder")

        # Create and upload file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        ) as f:
            f.write("Test content")
            temp_path = Path(f.name)

        try:
            result = google_drive.drive.upload_file(
                temp_path, folder_id=folder["id"]
            )
            assert "id" in result

            # Clean up
            google_drive.drive.delete_file(result["id"])
            google_drive.drive.delete_file(folder["id"])
        finally:
            temp_path.unlink()

    def test_download_file(self, google_drive):
        """Test downloading a file."""
        # First upload a file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        ) as f:
            f.write("Download test content")
            upload_path = Path(f.name)

        try:
            uploaded = google_drive.drive.upload_file(upload_path)

            # Download it
            with tempfile.TemporaryDirectory() as tmpdir:
                download_path = Path(tmpdir) / "downloaded.txt"
                google_drive.drive.download_file(uploaded["id"], download_path)

                assert download_path.exists()
                assert download_path.read_text() == "Download test content"

            # Clean up
            google_drive.drive.delete_file(uploaded["id"])
        finally:
            upload_path.unlink()
