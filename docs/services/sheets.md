# Google Sheets

`SheetsService` wraps the Google Sheets API v4. It inherits from `BaseService`, providing automatic retry, error handling, and `.raw` access.

```python
google = GoogleService(credentials_path="creds.json", services=["sheets"])
sheets = google.sheets
```

## Methods

### read_range

```python
def read_range(
    self,
    spreadsheet_id: str,
    range: str,
    value_render_option: str = "FORMATTED_VALUE",
) -> list[list[Any]]
```

Read values from a range. Returns a 2D list of cell values. An empty range returns `[]`.

- `value_render_option`: How values are rendered. Options: `"FORMATTED_VALUE"` (default), `"UNFORMATTED_VALUE"`, `"FORMULA"`.

```python
data = google.sheets.read_range("spreadsheet_id", "Sheet1!A1:D10")
for row in data:
    print(row)
```

### write_range

```python
def write_range(
    self,
    spreadsheet_id: str,
    range: str,
    values: list[list[Any]],
    value_input_option: str = "USER_ENTERED",
) -> dict[str, Any]
```

Write values to a range. Returns the update response.

- `value_input_option`: How input data is interpreted. `"USER_ENTERED"` (default) parses values as if typed into the UI. `"RAW"` stores values as-is.

```python
google.sheets.write_range(
    "spreadsheet_id",
    "Sheet1!A1:B2",
    values=[["Name", "Score"], ["Alice", 95]],
)
```

### append_rows

```python
def append_rows(
    self,
    spreadsheet_id: str,
    range: str,
    values: list[list[Any]],
    value_input_option: str = "USER_ENTERED",
) -> dict[str, Any]
```

Append rows after the last row with data in the specified range.

```python
google.sheets.append_rows(
    "spreadsheet_id",
    "Sheet1!A:B",
    values=[["Bob", 87], ["Charlie", 92]],
)
```

### get_spreadsheet

```python
def get_spreadsheet(self, spreadsheet_id: str) -> dict[str, Any]
```

Get spreadsheet metadata, including sheet properties and named ranges.

```python
info = google.sheets.get_spreadsheet("spreadsheet_id")
for sheet in info["sheets"]:
    print(sheet["properties"]["title"])
```

### create_spreadsheet

```python
def create_spreadsheet(
    self,
    title: str,
    sheets: list[str] | None = None,
) -> dict[str, Any]
```

Create a new spreadsheet. Returns the full spreadsheet resource.

- `title`: Spreadsheet title.
- `sheets`: Optional list of sheet (tab) names. If provided, the spreadsheet is created with these named sheets instead of the default single sheet. Each sheet is assigned an index corresponding to its position in the list.

```python
# Default single sheet
ss = google.sheets.create_spreadsheet("Q4 Report")
print(ss["spreadsheetId"])

# With named tabs
ss = google.sheets.create_spreadsheet("Budget", sheets=["Summary", "Q1", "Q2", "Q3", "Q4"])
```

### clear_range

```python
def clear_range(self, spreadsheet_id: str, range: str) -> dict[str, Any]
```

Clear all values from a range (formatting is preserved).

```python
google.sheets.clear_range("spreadsheet_id", "Sheet1!A1:Z100")
```

### add_sheet

```python
def add_sheet(
    self,
    spreadsheet_id: str,
    title: str,
    index: int | None = None,
) -> dict[str, Any]
```

Add a new sheet (tab) to an existing spreadsheet. Returns the `batchUpdate` response.

- `title`: Name of the new sheet.
- `index`: Optional 0-based position for the sheet.

Internally calls `batch_update` with an `addSheet` request.

```python
google.sheets.add_sheet("spreadsheet_id", "New Tab")
google.sheets.add_sheet("spreadsheet_id", "First Tab", index=0)
```

### batch_update

```python
def batch_update(
    self,
    spreadsheet_id: str,
    requests: list[dict[str, Any]],
) -> dict[str, Any]
```

Send a batch update to a spreadsheet. Use this for advanced operations like formatting, merging cells, conditional formatting, etc.

- `requests`: List of Sheets API request objects (see [Google Sheets API batchUpdate reference](https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/request)).

```python
google.sheets.batch_update("spreadsheet_id", [
    {
        "repeatCell": {
            "range": {"sheetId": 0, "startRowIndex": 0, "endRowIndex": 1},
            "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
            "fields": "userEnteredFormat.textFormat.bold",
        }
    }
])
```
