"""Typed response models for Google Sheets API."""

from dataclasses import dataclass, field
from typing import Any

from .._models import GoogleModel


@dataclass
class SheetProperties(GoogleModel):
    """Properties of a single sheet tab."""

    sheet_id: int = 0
    title: str = ""
    index: int = 0

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "SheetProperties":
        props = data.get("properties", data)
        return cls(
            sheet_id=props.get("sheetId", 0),
            title=props.get("title", ""),
            index=props.get("index", 0),
        )


@dataclass
class Spreadsheet(GoogleModel):
    """A Google Spreadsheet."""

    spreadsheet_id: str = ""
    title: str = ""
    sheets: list[SheetProperties] = field(default_factory=list)
    spreadsheet_url: str | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "Spreadsheet":
        props = data.get("properties", {})
        return cls(
            spreadsheet_id=data.get("spreadsheetId", ""),
            title=props.get("title", ""),
            sheets=[
                SheetProperties.from_api_response(s)
                for s in data.get("sheets", [])
            ],
            spreadsheet_url=data.get("spreadsheetUrl"),
        )


@dataclass
class ValueRange(GoogleModel):
    """Values from a spreadsheet range."""

    range: str = ""
    values: list[list[Any]] = field(default_factory=list)
    major_dimension: str = "ROWS"

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "ValueRange":
        return cls(
            range=data.get("range", ""),
            values=data.get("values", []),
            major_dimension=data.get("majorDimension", "ROWS"),
        )


@dataclass
class UpdateResult(GoogleModel):
    """Result of a spreadsheet update operation."""

    spreadsheet_id: str = ""
    updated_range: str = ""
    updated_rows: int = 0
    updated_columns: int = 0
    updated_cells: int = 0

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "UpdateResult":
        return cls(
            spreadsheet_id=data.get("spreadsheetId", ""),
            updated_range=data.get("updatedRange", ""),
            updated_rows=data.get("updatedRows", 0),
            updated_columns=data.get("updatedColumns", 0),
            updated_cells=data.get("updatedCells", 0),
        )


@dataclass
class BatchUpdateResponse(GoogleModel):
    """Result of a batch update operation."""

    spreadsheet_id: str = ""
    replies: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "BatchUpdateResponse":
        return cls(
            spreadsheet_id=data.get("spreadsheetId", ""),
            replies=data.get("replies", []),
        )
