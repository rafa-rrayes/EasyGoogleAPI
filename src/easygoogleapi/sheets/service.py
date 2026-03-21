"""Google Sheets API wrapper."""

from typing import Any

from .._base import BaseService
from .models import BatchUpdateResponse, Spreadsheet, UpdateResult


class SheetsService(BaseService):
    """Wrapper for Google Sheets API operations."""

    def read_range(
        self,
        spreadsheet_id: str,
        range: str,
        value_render_option: str = "FORMATTED_VALUE",
    ) -> list[list[Any]]:
        """Read values from a range."""
        request = self._resource.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range,
            valueRenderOption=value_render_option,
        )
        result: dict[str, Any] = (
            self._execute_request(request)
        )
        values: list[list[Any]] = result.get("values", [])
        return values

    def write_range(
        self,
        spreadsheet_id: str,
        range: str,
        values: list[list[Any]],
        value_input_option: str = "USER_ENTERED",
    ) -> UpdateResult:
        """Write values to a range."""
        body = {"values": values}
        request = self._resource.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range,
            valueInputOption=value_input_option,
            body=body,
        )
        result = self._execute_request(request)
        return UpdateResult.from_api_response(result)

    def append_rows(
        self,
        spreadsheet_id: str,
        range: str,
        values: list[list[Any]],
        value_input_option: str = "USER_ENTERED",
    ) -> UpdateResult:
        """Append rows to a sheet."""
        body = {"values": values}
        request = self._resource.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=range,
            valueInputOption=value_input_option,
            body=body,
        )
        result = self._execute_request(request)
        return UpdateResult.from_api_response(
            result.get("updates", result)
        )

    def get_spreadsheet(
        self, spreadsheet_id: str
    ) -> Spreadsheet:
        """Get spreadsheet metadata."""
        request = self._resource.spreadsheets().get(
            spreadsheetId=spreadsheet_id
        )
        result = self._execute_request(request)
        return Spreadsheet.from_api_response(result)

    def create_spreadsheet(
        self,
        title: str,
        sheets: list[str] | None = None,
    ) -> Spreadsheet:
        """Create a new spreadsheet."""
        body: dict[str, Any] = {"properties": {"title": title}}
        if sheets:
            body["sheets"] = [
                {"properties": {"title": name, "index": idx}}
                for idx, name in enumerate(sheets)
            ]
        request = self._resource.spreadsheets().create(body=body)
        result = self._execute_request(request)
        return Spreadsheet.from_api_response(result)

    def clear_range(
        self, spreadsheet_id: str, range: str
    ) -> dict[str, Any]:
        """Clear values from a range."""
        request = (
            self._resource.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id,
                range=range,
                body={},
            )
        )
        result: dict[str, Any] = (
            self._execute_request(request)
        )
        return result

    def add_sheet(
        self,
        spreadsheet_id: str,
        title: str,
        index: int | None = None,
    ) -> BatchUpdateResponse:
        """Add a new sheet (tab) to an existing spreadsheet."""
        props: dict[str, Any] = {"title": title}
        if index is not None:
            props["index"] = index
        return self.batch_update(
            spreadsheet_id,
            [{"addSheet": {"properties": props}}],
        )

    def batch_update(
        self,
        spreadsheet_id: str,
        requests: list[dict[str, Any]],
    ) -> BatchUpdateResponse:
        """Send a batch update to a spreadsheet."""
        body = {"requests": requests}
        request = self._resource.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body=body
        )
        result = self._execute_request(request)
        return BatchUpdateResponse.from_api_response(result)

    # ------------------------------------------------------------------
    # Multi-range / Sheet management
    # ------------------------------------------------------------------

    def batch_get(
        self,
        spreadsheet_id: str,
        ranges: list[str],
        value_render_option: str = "FORMATTED_VALUE",
    ) -> dict[str, list[list[Any]]]:
        """Read multiple ranges in a single request.

        Returns a dict mapping each range string to its values.
        """
        request = self._resource.spreadsheets().values().batchGet(
            spreadsheetId=spreadsheet_id,
            ranges=ranges,
            valueRenderOption=value_render_option,
        )
        result = self._execute_request(request)
        return {
            vr.get("range", ""): vr.get("values", [])
            for vr in result.get("valueRanges", [])
        }

    def delete_sheet(
        self, spreadsheet_id: str, sheet_id: int
    ) -> BatchUpdateResponse:
        """Delete a sheet (tab) from a spreadsheet."""
        return self.batch_update(
            spreadsheet_id,
            [{"deleteSheet": {"sheetId": sheet_id}}],
        )

    def rename_sheet(
        self, spreadsheet_id: str, sheet_id: int, new_title: str
    ) -> BatchUpdateResponse:
        """Rename a sheet (tab) in a spreadsheet."""
        return self.batch_update(
            spreadsheet_id,
            [
                {
                    "updateSheetProperties": {
                        "properties": {"sheetId": sheet_id, "title": new_title},
                        "fields": "title",
                    }
                }
            ],
        )

    def auto_resize_columns(
        self, spreadsheet_id: str, sheet_id: int
    ) -> BatchUpdateResponse:
        """Auto-resize all columns in a sheet to fit their content."""
        return self.batch_update(
            spreadsheet_id,
            [
                {
                    "autoResizeDimensions": {
                        "dimensions": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                        }
                    }
                }
            ],
        )
