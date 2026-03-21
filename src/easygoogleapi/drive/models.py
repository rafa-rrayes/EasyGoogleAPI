"""Typed response models for Google Drive API."""

from dataclasses import dataclass, field
from typing import Any

from .._models import GoogleModel


@dataclass
class FileMetadata(GoogleModel):
    """Metadata for a Google Drive file or folder."""

    id: str = ""
    name: str = ""
    mime_type: str = ""
    modified_time: str | None = None
    size: str | None = None
    web_view_link: str | None = None
    parents: list[str] = field(default_factory=list)
    trashed: bool = False
    description: str | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "FileMetadata":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            mime_type=data.get("mimeType", ""),
            modified_time=data.get("modifiedTime"),
            size=data.get("size"),
            web_view_link=data.get("webViewLink"),
            parents=data.get("parents", []),
            trashed=data.get("trashed", False),
            description=data.get("description"),
        )


@dataclass
class Permission(GoogleModel):
    """A permission on a Drive file."""

    id: str = ""
    role: str = ""
    type: str = ""
    email_address: str | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "Permission":
        return cls(
            id=data.get("id", ""),
            role=data.get("role", ""),
            type=data.get("type", ""),
            email_address=data.get("emailAddress"),
        )


@dataclass
class StorageQuota(GoogleModel):
    """Drive storage quota information."""

    limit: str | None = None
    usage: str | None = None
    usage_in_drive: str | None = None
    usage_in_drive_trash: str | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "StorageQuota":
        return cls(
            limit=data.get("limit"),
            usage=data.get("usage"),
            usage_in_drive=data.get("usageInDrive"),
            usage_in_drive_trash=data.get("usageInDriveTrash"),
        )


@dataclass
class FileList(GoogleModel):
    """A page of Drive file results."""

    files: list[FileMetadata] = field(default_factory=list)
    next_page_token: str | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "FileList":
        return cls(
            files=[
                FileMetadata.from_api_response(f)
                for f in data.get("files", [])
            ],
            next_page_token=data.get("nextPageToken"),
        )
