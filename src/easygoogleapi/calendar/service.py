"""Google Calendar API wrapper."""

from datetime import UTC, datetime, timezone
from typing import Any

from .._base import BaseService


def _to_rfc3339(dt: datetime) -> str:
    """Convert a datetime to an RFC3339 string with timezone offset.

    Naive datetimes get a ``Z`` suffix (assumed UTC).  Aware datetimes
    use their own UTC offset so the result is always valid RFC3339.
    """
    if dt.tzinfo is None:
        return dt.isoformat() + "Z"
    # Convert to UTC and format with Z suffix for consistency
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class CalendarService(BaseService):
    """Wrapper for Google Calendar API operations."""

    # ------------------------------------------------------------------
    # Calendar management
    # ------------------------------------------------------------------

    def list_calendars(self) -> list[dict[str, Any]]:
        """List all calendars the user has access to."""
        request = self._resource.calendarList().list()
        result = self._execute_request(request)
        return result.get("items", [])

    def get_calendar(self, calendar_id: str = "primary") -> dict[str, Any]:
        """Get details of a specific calendar."""
        request = self._resource.calendars().get(calendarId=calendar_id)
        return self._execute_request(request)

    def create_calendar(
        self,
        summary: str,
        description: str | None = None,
        timezone: str | None = None,
    ) -> dict[str, Any]:
        """Create a new secondary calendar.

        Args:
            summary: Calendar title.
            description: Optional calendar description.
            timezone: IANA timezone (e.g. ``"America/New_York"``).
        """
        body: dict[str, Any] = {"summary": summary}
        if description is not None:
            body["description"] = description
        if timezone is not None:
            body["timeZone"] = timezone
        request = self._resource.calendars().insert(body=body)
        return self._execute_request(request)

    def delete_calendar(self, calendar_id: str) -> None:
        """Delete a secondary calendar."""
        request = self._resource.calendars().delete(calendarId=calendar_id)
        self._execute_request(request)

    def add_calendar_to_list(
        self,
        calendar_id: str,
        color_id: str | None = None,
        hidden: bool = False,
    ) -> dict[str, Any]:
        """Add an existing calendar to the user's calendar list.

        Args:
            calendar_id: ID of the calendar to add.
            color_id: Optional color ID (1-24).
            hidden: If ``True`` the calendar is hidden in the UI.
        """
        body: dict[str, Any] = {"id": calendar_id}
        if color_id is not None:
            body["colorId"] = color_id
        if hidden:
            body["hidden"] = True
        request = self._resource.calendarList().insert(body=body)
        return self._execute_request(request)

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

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
            "timeMin": _to_rfc3339(time_min),
            "maxResults": max_results,
            "singleEvents": single_events,
            "orderBy": order_by,
        }
        if time_max:
            kwargs["timeMax"] = _to_rfc3339(time_max)

        request = self._resource.events().list(**kwargs)
        result = self._execute_request(request)
        return result.get("items", [])

    def get_event(
        self,
        event_id: str,
        calendar_id: str = "primary",
    ) -> dict[str, Any]:
        """Get a single event by ID."""
        request = self._resource.events().get(
            calendarId=calendar_id, eventId=event_id
        )
        return self._execute_request(request)

    def create_event(
        self,
        summary: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        calendar_id: str = "primary",
        description: str | None = None,
        location: str | None = None,
        attendees: list[str] | None = None,
        timezone: str = "UTC",
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new calendar event.

        Pass a raw ``body`` dict for full control over the event resource,
        or use the convenience parameters.  When *body* is provided the
        convenience parameters are merged on top of it (so you can
        override individual fields).
        """
        event_body: dict[str, Any] = body.copy() if body else {}

        if summary is not None:
            event_body["summary"] = summary
        if start is not None:
            event_body["start"] = {"dateTime": start.isoformat(), "timeZone": timezone}
        if end is not None:
            event_body["end"] = {"dateTime": end.isoformat(), "timeZone": timezone}
        if description is not None:
            event_body["description"] = description
        if location is not None:
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
        body: dict[str, Any] | None = None,
        **updates: Any,
    ) -> dict[str, Any]:
        """Update an existing calendar event.

        Pass a raw ``body`` dict to replace the entire event resource, or
        use keyword arguments to patch individual top-level fields.
        """
        if body is not None:
            event = body
        else:
            get_request = self._resource.events().get(
                calendarId=calendar_id, eventId=event_id
            )
            event = self._execute_request(get_request)
            event.update(updates)

        update_request = self._resource.events().update(
            calendarId=calendar_id, eventId=event_id, body=event
        )
        return self._execute_request(update_request)
