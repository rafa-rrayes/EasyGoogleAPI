"""Typed response models for Gmail API."""

from dataclasses import dataclass, field
from typing import Any

from .._models import GoogleModel


@dataclass
class Label(GoogleModel):
    """A Gmail label."""

    id: str = ""
    name: str = ""
    type: str | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "Label":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            type=data.get("type"),
        )


@dataclass
class Message(GoogleModel):
    """A Gmail message."""

    id: str = ""
    thread_id: str | None = None
    label_ids: list[str] = field(default_factory=list)
    snippet: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    internal_date: str | None = None
    raw: str | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "Message":
        return cls(
            id=data.get("id", ""),
            thread_id=data.get("threadId"),
            label_ids=data.get("labelIds", []),
            snippet=data.get("snippet"),
            payload=data.get("payload", {}),
            internal_date=data.get("internalDate"),
            raw=data.get("raw"),
        )


@dataclass
class MessageList(GoogleModel):
    """A page of Gmail message results."""

    messages: list[Message] = field(default_factory=list)
    next_page_token: str | None = None
    result_size_estimate: int = 0

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "MessageList":
        return cls(
            messages=[
                Message.from_api_response(m)
                for m in data.get("messages", [])
            ],
            next_page_token=data.get("nextPageToken"),
            result_size_estimate=data.get("resultSizeEstimate", 0),
        )


@dataclass
class Thread(GoogleModel):
    """A Gmail thread (conversation)."""

    id: str = ""
    snippet: str | None = None
    messages: list[Message] = field(default_factory=list)

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "Thread":
        return cls(
            id=data.get("id", ""),
            snippet=data.get("snippet"),
            messages=[
                Message.from_api_response(m)
                for m in data.get("messages", [])
            ],
        )


@dataclass
class Draft(GoogleModel):
    """A Gmail draft."""

    id: str = ""
    message: Message | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "Draft":
        msg_data = data.get("message")
        return cls(
            id=data.get("id", ""),
            message=Message.from_api_response(msg_data) if msg_data else None,
        )
