#!/usr/bin/env python3
"""Example: Google Calendar - List and create events."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from easygoogleapi import GoogleService

CREDENTIALS_PATH = Path(__file__).parent.parent / "tests" / "credentials.json"


def main():
    google = GoogleService(
        credentials_path=CREDENTIALS_PATH,
        services=["calendar"],
    )

    print("=== Your Calendars ===")
    calendars = google.calendar.list_calendars()
    for cal in calendars[:5]:
        print(f"  - {cal['summary']}")

    print("\n=== Upcoming Events ===")
    events = google.calendar.list_events(max_results=5)
    if not events:
        print("  No upcoming events.")
    for event in events:
        start = event["start"].get("dateTime", event["start"].get("date"))
        print(f"  - {event['summary']} ({start})")

    print("\n=== Creating Test Event ===")
    start = datetime.now(timezone.utc) + timedelta(days=1)
    end = start + timedelta(hours=1)

    event = google.calendar.create_event(
        summary="EasyGoogleAPI Test Event",
        start=start,
        end=end,
        description="This event was created by EasyGoogleAPI",
    )
    print(f"  Created: {event['summary']}")
    print(f"  Link: {event.get('htmlLink', 'N/A')}")

    # Clean up - delete the test event
    google.calendar.delete_event(event["id"])
    print("  (Event deleted)")


if __name__ == "__main__":
    main()
