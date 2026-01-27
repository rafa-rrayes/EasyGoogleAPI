#!/usr/bin/env python3
"""Example: Google Drive - List files and upload."""

from pathlib import Path

from easygoogleapi import GoogleService

CREDENTIALS_PATH = Path(__file__).parent.parent / "tests" / "credentials.json"


def main():
    google = GoogleService(
        credentials_path=CREDENTIALS_PATH,
        services=["drive"],
    )

    print("=== Recent Files ===")
    files = google.drive.list_files(max_results=10)
    if not files:
        print("  No files found.")
    for f in files:
        print(f"  - {f['name']} ({f['mimeType'][:30]}...)")

    print("\n=== Creating Test Folder ===")
    folder = google.drive.create_folder("EasyGoogleAPI Test Folder")
    print(f"  Created: {folder['name']}")
    print(f"  ID: {folder['id']}")

    print("\n=== Uploading Test File ===")
    # Create a temporary test file
    test_file = Path("/tmp/easygoogleapi_test.txt")
    test_file.write_text("Hello from EasyGoogleAPI!")

    uploaded = google.drive.upload_file(
        str(test_file),
        folder_id=folder["id"],
    )
    print(f"  Uploaded: {uploaded['name']}")
    print(f"  Link: {uploaded.get('webViewLink', 'N/A')}")

    # Clean up
    test_file.unlink()
    google.drive.delete_file(uploaded["id"])
    google.drive.delete_file(folder["id"])
    print("\n  (Test folder and file deleted)")


if __name__ == "__main__":
    main()
