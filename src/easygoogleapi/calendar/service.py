"""Google Calendar API wrapper."""

from datetime import UTC, datetime
from typing import Any

from .._base import BaseService


class CalendarService(BaseService):
    """Wrapper for Google Calendar API operations."""

    def list_calendars(self) -> list[dict[str, Any]]:
        """List all calendars the user has access to."""
        request = self._resource.calendarList().list()
        result = self._execute_request(request)
        return result.get("items", [])

    def get_calendar(self, calendar_id: str = "primary") -> dict[str, Any]:
        """Get details of a specific calendar."""
        request = self._resource.calendars().get(calendarId=calendar_id)
        return self._execute_request(request)

    def list_events(
        self,
        calendar_id: str = "primary",
        time_min: datetime | None = None,
        time_max: datetime | None = None,
        max_results: int = 10,
        single_events: bool = True,
        order_by: str = "startTime",
    ) -> list[dict[str, Any]]:
        """List events from a calendar."""
        if time_min is None:
            time_min = datetime.now(UTC)

        kwargs: dict[str, Any] = {
            "calendarId": calendar_id,
            "timeMin": time_min.isoformat() + "Z",
            "maxResults": max_results,
            "singleEvents": single_events,
            "orderBy": order_by,
        }
        if time_max:
            kwargs["timeMax"] = time_max.isoformat() + "Z"

        request = self._resource.events().list(**kwargs)
        result = self._execute_request(request)
        return result.get("items", [])

    def create_event(
        self,
        summary: str,
        start: datetime,
        end: datetime,
        calendar_id: str = "primary",
        description: str | None = None,
        location: str | None = None,
        attendees: list[str] | None = None,
        timezone: str = "UTC",
    ) -> dict[str, Any]:
        """Create a new calendar event."""
        event_body: dict[str, Any] = {
            "summary": summary,
            "start": {"dateTime": start.isoformat(), "timeZone": timezone},
            "end": {"dateTime": end.isoformat(), "timeZone": timezone},
        }

        if description:
            event_body["description"] = description
        if location:
            event_body["location"] = location
        if attendees:
            event_body["attendees"] = [{"email": email} for email in attendees]

        request = self._resource.events().insert(
            calendarId=calendar_id, body=event_body
        )
        return self._execute_request(request)

    def delete_event(
        self, event_id: str, calendar_id: str = "primary"
    ) -> None:
        """Delete a calendar event."""
        request = self._resource.events().delete(
            calendarId=calendar_id, eventId=event_id
        )
        self._execute_request(request)

    def update_event(
        self,
        event_id: str,
        calendar_id: str = "primary",
        **updates: Any,
    ) -> dict[str, Any]:
        """Update an existing calendar event."""
        get_request = self._resource.events().get(
            calendarId=calendar_id, eventId=event_id
        )
        event = self._execute_request(get_request)
        event.update(updates)

        update_request = self._resource.events().update(
            calendarId=calendar_id, eventId=event_id, body=event
        )
        return self._execute_request(update_request)
