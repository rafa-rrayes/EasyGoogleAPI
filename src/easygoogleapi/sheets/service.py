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
        self,
        title: str,
        sheets: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new spreadsheet.

        Args:
            title: Spreadsheet title.
            sheets: Optional list of sheet names. If provided, the
                spreadsheet is created with these named sheets instead
                of the default single sheet.
        """
        body: dict[str, Any] = {"properties": {"title": title}}
        if sheets:
            body["sheets"] = [
                {"properties": {"title": name, "index": idx}}
                for idx, name in enumerate(sheets)
            ]
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

    def add_sheet(
        self,
        spreadsheet_id: str,
        title: str,
        index: int | None = None,
    ) -> dict[str, Any]:
        """Add a new sheet (tab) to an existing spreadsheet.

        Args:
            spreadsheet_id: The spreadsheet to modify.
            title: Name of the new sheet.
            index: Optional 0-based position for the sheet.

        Returns:
            The ``batchUpdate`` response.
        """
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
    ) -> dict[str, Any]:
        """Send a batch update to a spreadsheet.

        Args:
            spreadsheet_id: Target spreadsheet.
            requests: List of Sheets API request objects.
        """
        body = {"requests": requests}
        request = self._resource.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body=body
        )
        return self._execute_request(request)
