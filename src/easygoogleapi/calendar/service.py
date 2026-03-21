"""Google Calendar API wrapper."""

import uuid
from datetime import UTC, datetime, timezone
from typing import Any

from .._base import BaseService
from .._pagination import PageIterator
from .models import CalendarMeta, Event, EventList


def _to_rfc3339(dt: datetime) -> str:
    """Convert a datetime to an RFC3339 string with timezone offset."""
    if dt.tzinfo is None:
        return dt.isoformat() + "Z"
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class CalendarService(BaseService):
    """Wrapper for Google Calendar API operations."""

    # ------------------------------------------------------------------
    # Calendar management
    # ------------------------------------------------------------------

    def list_calendars(self) -> list[CalendarMeta]:
        """List all calendars the user has access to."""
        request = self._resource.calendarList().list()
        result = self._execute_request(request)
        return [
            CalendarMeta.from_api_response(c)
            for c in result.get("items", [])
        ]

    def get_calendar(self, calendar_id: str = "primary") -> CalendarMeta:
        """Get details of a specific calendar."""
        request = self._resource.calendars().get(calendarId=calendar_id)
        result = self._execute_request(request)
        return CalendarMeta.from_api_response(result)

    def create_calendar(
        self,
        summary: str,
        description: str | None = None,
        timezone: str | None = None,
    ) -> CalendarMeta:
        """Create a new secondary calendar."""
        body: dict[str, Any] = {"summary": summary}
        if description is not None:
            body["description"] = description
        if timezone is not None:
            body["timeZone"] = timezone
        request = self._resource.calendars().insert(body=body)
        result = self._execute_request(request)
        return CalendarMeta.from_api_response(result)

    def delete_calendar(self, calendar_id: str) -> None:
        """Delete a secondary calendar."""
        request = self._resource.calendars().delete(calendarId=calendar_id)
        self._execute_request(request)

    def add_calendar_to_list(
        self,
        calendar_id: str,
        color_id: str | None = None,
        hidden: bool = False,
    ) -> CalendarMeta:
        """Add an existing calendar to the user's calendar list."""
        body: dict[str, Any] = {"id": calendar_id}
        if color_id is not None:
            body["colorId"] = color_id
        if hidden:
            body["hidden"] = True
        request = self._resource.calendarList().insert(body=body)
        result = self._execute_request(request)
        return CalendarMeta.from_api_response(result)

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def list_events(
        self,
        calendar_id: str = "primary",
        time_min: datetime | None = None,
        time_max: datetime | None = None,
        max_results: int = 250,
        single_events: bool = True,
        order_by: str = "startTime",
    ) -> PageIterator[Event]:
        """List events with automatic pagination.

        Returns a ``PageIterator`` that yields ``Event`` objects::

            for event in google.calendar.list_events():
                print(event.summary)
        """
        effective_time_min = time_min or datetime.now(UTC)

        def fetch_page(page_token: str | None) -> dict[str, Any]:
            kwargs: dict[str, Any] = {
                "calendarId": calendar_id,
                "timeMin": _to_rfc3339(effective_time_min),
                "maxResults": max_results,
                "singleEvents": single_events,
                "orderBy": order_by,
            }
            if time_max:
                kwargs["timeMax"] = _to_rfc3339(time_max)
            if page_token:
                kwargs["pageToken"] = page_token
            request = self._resource.events().list(**kwargs)
            return self._execute_request(request)

        return PageIterator(fetch_page, items_key="items", model_class=Event)

    def list_events_page(
        self,
        calendar_id: str = "primary",
        time_min: datetime | None = None,
        time_max: datetime | None = None,
        max_results: int = 250,
        single_events: bool = True,
        order_by: str = "startTime",
        page_token: str | None = None,
    ) -> EventList:
        """List a single page of events."""
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
        if page_token:
            kwargs["pageToken"] = page_token

        request = self._resource.events().list(**kwargs)
        result = self._execute_request(request)
        return EventList.from_api_response(result)

    def get_event(
        self,
        event_id: str,
        calendar_id: str = "primary",
    ) -> Event:
        """Get a single event by ID."""
        request = self._resource.events().get(
            calendarId=calendar_id, eventId=event_id
        )
        result = self._execute_request(request)
        return Event.from_api_response(result)

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
    ) -> Event:
        """Create a new calendar event."""
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
        result = self._execute_request(request)
        return Event.from_api_response(result)

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
    ) -> Event:
        """Update an existing calendar event."""
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
        result = self._execute_request(update_request)
        return Event.from_api_response(result)

    # ------------------------------------------------------------------
    # Quick-add / Recurring / Free-busy / Watch
    # ------------------------------------------------------------------

    def quick_add(
        self, text: str, calendar_id: str = "primary"
    ) -> Event:
        """Create an event from a simple text string (natural language).

        Example: ``quick_add("Lunch with Bob at noon tomorrow")``
        """
        request = self._resource.events().quickAdd(
            calendarId=calendar_id, text=text
        )
        result = self._execute_request(request)
        return Event.from_api_response(result)

    def list_recurring_instances(
        self, event_id: str, calendar_id: str = "primary"
    ) -> list[Event]:
        """List all instances of a recurring event."""
        request = self._resource.events().instances(
            calendarId=calendar_id, eventId=event_id
        )
        result = self._execute_request(request)
        return [
            Event.from_api_response(e)
            for e in result.get("items", [])
        ]

    def get_freebusy(
        self,
        time_min: datetime,
        time_max: datetime,
        calendars: list[str],
    ) -> dict[str, Any]:
        """Query free/busy information for a set of calendars."""
        body: dict[str, Any] = {
            "timeMin": _to_rfc3339(time_min),
            "timeMax": _to_rfc3339(time_max),
            "items": [{"id": cal} for cal in calendars],
        }
        request = self._resource.freebusy().query(body=body)
        return self._execute_request(request)

    def watch(
        self,
        calendar_id: str,
        webhook_url: str,
        channel_id: str | None = None,
    ) -> dict[str, Any]:
        """Subscribe to push notifications for calendar events."""
        body: dict[str, Any] = {
            "id": channel_id or str(uuid.uuid4()),
            "type": "web_hook",
            "address": webhook_url,
        }
        request = self._resource.events().watch(
            calendarId=calendar_id, body=body
        )
        return self._execute_request(request)
