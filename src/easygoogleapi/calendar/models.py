"""Typed response models for Google Calendar API."""

from dataclasses import dataclass, field
from typing import Any

from .._models import GoogleModel


@dataclass
class CalendarMeta(GoogleModel):
    """Metadata for a Google Calendar."""

    id: str = ""
    summary: str = ""
    description: str | None = None
    time_zone: str | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "CalendarMeta":
        return cls(
            id=data.get("id", ""),
            summary=data.get("summary", ""),
            description=data.get("description"),
            time_zone=data.get("timeZone"),
        )


@dataclass
class Attendee(GoogleModel):
    """An event attendee."""

    email: str = ""
    display_name: str | None = None
    response_status: str | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "Attendee":
        return cls(
            email=data.get("email", ""),
            display_name=data.get("displayName"),
            response_status=data.get("responseStatus"),
        )


@dataclass
class Event(GoogleModel):
    """A Google Calendar event."""

    id: str = ""
    summary: str | None = None
    description: str | None = None
    location: str | None = None
    start: dict[str, Any] = field(default_factory=dict)
    end: dict[str, Any] = field(default_factory=dict)
    attendees: list[Attendee] = field(default_factory=list)
    status: str | None = None
    html_link: str | None = None
    created: str | None = None
    updated: str | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "Event":
        return cls(
            id=data.get("id", ""),
            summary=data.get("summary"),
            description=data.get("description"),
            location=data.get("location"),
            start=data.get("start", {}),
            end=data.get("end", {}),
            attendees=[
                Attendee.from_api_response(a)
                for a in data.get("attendees", [])
            ],
            status=data.get("status"),
            html_link=data.get("htmlLink"),
            created=data.get("created"),
            updated=data.get("updated"),
        )


@dataclass
class EventList(GoogleModel):
    """A page of calendar event results."""

    events: list[Event] = field(default_factory=list)
    next_page_token: str | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "EventList":
        return cls(
            events=[
                Event.from_api_response(e) for e in data.get("items", [])
            ],
            next_page_token=data.get("nextPageToken"),
        )
