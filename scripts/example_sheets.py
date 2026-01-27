#!/usr/bin/env python3
"""Example: Google Sheets - Create, read, and write."""

from pathlib import Path

from easygoogleapi import GoogleService

CREDENTIALS_PATH = Path(__file__).parent.parent / "tests" / "credentials.json"


def main():
    google = GoogleService(
        credentials_path=CREDENTIALS_PATH,
        services=["sheets", "drive"],  # Need drive to delete the spreadsheet
    )

    print("=== Creating Test Spreadsheet ===")
    spreadsheet = google.sheets.create_spreadsheet("EasyGoogleAPI Test Sheet")
    spreadsheet_id = spreadsheet["spreadsheetId"]
    print(f"  Created: {spreadsheet['properties']['title']}")
    print(f"  URL: {spreadsheet['spreadsheetUrl']}")

    print("\n=== Writing Data ===")
    data = [
        ["Name", "Age", "City"],
        ["Alice", 30, "New York"],
        ["Bob", 25, "Los Angeles"],
        ["Charlie", 35, "Chicago"],
    ]
    google.sheets.write_range(spreadsheet_id, "Sheet1!A1:C4", data)
    print(f"  Wrote {len(data)} rows")

    print("\n=== Reading Data ===")
    result = google.sheets.read_range(spreadsheet_id, "Sheet1!A1:C4")
    for row in result:
        print(f"  {row}")

    print("\n=== Appending Row ===")
    google.sheets.append_rows(
        spreadsheet_id,
        "Sheet1!A:C",
        [["Diana", 28, "Houston"]],
    )
    print("  Appended 1 row")

    print("\n=== Final Data ===")
    result = google.sheets.read_range(spreadsheet_id, "Sheet1!A1:C5")
    for row in result:
        print(f"  {row}")

    # Clean up
    google.drive.delete_file(spreadsheet_id)
    print("\n  (Spreadsheet deleted)")


if __name__ == "__main__":
    main()
