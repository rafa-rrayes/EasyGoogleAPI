"""Google Sheets API wrapper."""

from typing import Any

from .._base import BaseService


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
        result = self._execute_request(request)
        return result.get("values", [])

    def write_range(
        self,
        spreadsheet_id: str,
        range: str,
        values: list[list[Any]],
        value_input_option: str = "USER_ENTERED",
    ) -> dict[str, Any]:
        """Write values to a range."""
        body = {"values": values}
        request = self._resource.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range,
            valueInputOption=value_input_option,
            body=body,
        )
        return self._execute_request(request)

    def append_rows(
        self,
        spreadsheet_id: str,
        range: str,
        values: list[list[Any]],
        value_input_option: str = "USER_ENTERED",
    ) -> dict[str, Any]:
        """Append rows to a sheet."""
        body = {"values": values}
        request = self._resource.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=range,
            valueInputOption=value_input_option,
            body=body,
        )
        return self._execute_request(request)

    def get_spreadsheet(
        self, spreadsheet_id: str
    ) -> dict[str, Any]:
        """Get spreadsheet metadata."""
        request = self._resource.spreadsheets().get(
            spreadsheetId=spreadsheet_id
        )
        return self._execute_request(request)

    def create_spreadsheet(
        self, title: str
    ) -> dict[str, Any]:
        """Create a new spreadsheet."""
        body = {"properties": {"title": title}}
        request = self._resource.spreadsheets().create(body=body)
        return self._execute_request(request)

    def clear_range(
        self, spreadsheet_id: str, range: str
    ) -> dict[str, Any]:
        """Clear values from a range."""
        request = self._resource.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id, range=range, body={}
        )
        return self._execute_request(request)
