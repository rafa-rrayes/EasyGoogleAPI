"""Typed response models for Google Docs API."""

from dataclasses import dataclass, field
from typing import Any

from .._models import GoogleModel


@dataclass
class Document(GoogleModel):
    """A Google Docs document."""

    document_id: str = ""
    title: str = ""
    body: dict[str, Any] = field(default_factory=dict)
    revision_id: str | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "Document":
        return cls(
            document_id=data.get("documentId", ""),
            title=data.get("title", ""),
            body=data.get("body", {}),
            revision_id=data.get("revisionId"),
        )


@dataclass
class BatchUpdateResponse(GoogleModel):
    """Result of a Docs batch update."""

    document_id: str = ""
    replies: list[dict[str, Any]] = field(default_factory=list)
    write_control: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "BatchUpdateResponse":
        return cls(
            document_id=data.get("documentId", ""),
            replies=data.get("replies", []),
            write_control=data.get("writeControl", {}),
        )
