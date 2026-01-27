"""Integration tests for Calendar service."""

from datetime import datetime, timedelta, timezone

import pytest


@pytest.mark.integration
class TestCalendarService:
    """Integration tests for CalendarService."""

    def test_list_calendars(self, google_calendar):
        """Test listing calendars."""
        calendars = google_calendar.calendar.list_calendars()
        assert isinstance(calendars, list)
        # User should have at least a primary calendar
        assert len(calendars) > 0

    def test_get_primary_calendar(self, google_calendar):
        """Test getting primary calendar."""
        calendar = google_calendar.calendar.get_calendar("primary")
        assert "id" in calendar
        assert "summary" in calendar

    def test_list_events(self, google_calendar):
        """Test listing events."""
        events = google_calendar.calendar.list_events(max_results=5)
        assert isinstance(events, list)

    def test_create_and_delete_event(self, google_calendar):
        """Test creating and deleting an event."""
        start = datetime.now(timezone.utc) + timedelta(days=1)
        end = start + timedelta(hours=1)

        # Create event
        event = google_calendar.calendar.create_event(
            summary="Test Event from EasyGoogleAPI",
            start=start,
            end=end,
            description="This is a test event",
        )

        assert "id" in event
        assert event["summary"] == "Test Event from EasyGoogleAPI"

        # Clean up - delete the event
        google_calendar.calendar.delete_event(event["id"])

    def test_create_event_with_attendees(self, google_calendar):
        """Test creating an event with attendees."""
        start = datetime.now(timezone.utc) + timedelta(days=1)
        end = start + timedelta(hours=1)

        event = google_calendar.calendar.create_event(
            summary="Test Event with Attendees",
            start=start,
            end=end,
            attendees=["test@example.com"],
        )

        assert "id" in event
        # Clean up
        google_calendar.calendar.delete_event(event["id"])

    def test_update_event(self, google_calendar):
        """Test updating an event."""
        start = datetime.now(timezone.utc) + timedelta(days=1)
        end = start + timedelta(hours=1)

        # Create event
        event = google_calendar.calendar.create_event(
            summary="Original Title",
            start=start,
            end=end,
        )

        # Update event
        updated = google_calendar.calendar.update_event(
            event["id"],
            summary="Updated Title",
        )

        assert updated["summary"] == "Updated Title"

        # Clean up
        google_calendar.calendar.delete_event(event["id"])
