"""Integration tests for Sheets service."""

import pytest


@pytest.mark.integration
class TestSheetsService:
    """Integration tests for SheetsService."""

    @pytest.fixture
    def test_spreadsheet(self, google_sheets):
        """Create a test spreadsheet and clean it up after."""
        spreadsheet = google_sheets.sheets.create_spreadsheet(
            "Test_EasyGoogleAPI"
        )
        yield spreadsheet
        # Clean up - need drive to delete
        # Note: Sheets API can't delete, would need Drive API

    def test_create_spreadsheet(self, google_sheets):
        """Test creating a spreadsheet."""
        spreadsheet = google_sheets.sheets.create_spreadsheet(
            "Test_Create_Spreadsheet"
        )
        assert "spreadsheetId" in spreadsheet
        assert spreadsheet["properties"]["title"] == "Test_Create_Spreadsheet"

    def test_get_spreadsheet(self, google_sheets, test_spreadsheet):
        """Test getting spreadsheet metadata."""
        spreadsheet = google_sheets.sheets.get_spreadsheet(
            test_spreadsheet["spreadsheetId"]
        )
        assert "spreadsheetId" in spreadsheet
        assert "sheets" in spreadsheet

    def test_write_and_read_range(self, google_sheets, test_spreadsheet):
        """Test writing and reading values."""
        spreadsheet_id = test_spreadsheet["spreadsheetId"]

        # Write values
        values = [["Name", "Age"], ["Alice", 30], ["Bob", 25]]
        google_sheets.sheets.write_range(
            spreadsheet_id, "Sheet1!A1:B3", values
        )

        # Read values back
        result = google_sheets.sheets.read_range(
            spreadsheet_id, "Sheet1!A1:B3"
        )
        assert result == [["Name", "Age"], ["Alice", "30"], ["Bob", "25"]]

    def test_append_rows(self, google_sheets, test_spreadsheet):
        """Test appending rows."""
        spreadsheet_id = test_spreadsheet["spreadsheetId"]

        # Write initial data
        google_sheets.sheets.write_range(
            spreadsheet_id, "Sheet1!A1:B1", [["Name", "Age"]]
        )

        # Append rows
        google_sheets.sheets.append_rows(
            spreadsheet_id, "Sheet1!A:B", [["Charlie", 35]]
        )

        # Verify
        result = google_sheets.sheets.read_range(
            spreadsheet_id, "Sheet1!A1:B2"
        )
        assert len(result) == 2
        assert result[1] == ["Charlie", "35"]

    def test_clear_range(self, google_sheets, test_spreadsheet):
        """Test clearing a range."""
        spreadsheet_id = test_spreadsheet["spreadsheetId"]

        # Write values
        google_sheets.sheets.write_range(
            spreadsheet_id, "Sheet1!A1:B2", [["A", "B"], ["C", "D"]]
        )

        # Clear
        google_sheets.sheets.clear_range(spreadsheet_id, "Sheet1!A1:B2")

        # Verify empty
        result = google_sheets.sheets.read_range(
            spreadsheet_id, "Sheet1!A1:B2"
        )
        assert result == []
