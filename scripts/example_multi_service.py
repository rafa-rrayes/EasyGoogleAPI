#!/usr/bin/env python3
"""Example: Using multiple Google services together.

This example shows how to:
1. Create a meeting in Google Meet
2. Add it to Google Calendar
3. Create a meeting notes doc in Google Drive
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from easygoogleapi import GoogleService

CREDENTIALS_PATH = Path(__file__).parent.parent / "tests" / "credentials.json"


def main():
    google = GoogleService(
        credentials_path=CREDENTIALS_PATH,
        services=["meet", "calendar", "drive"],
    )

    print("=" * 50)
    print("Creating a complete meeting setup...")
    print("=" * 50)

    # Step 1: Create a Meet space
    print("\n[1/3] Creating Google Meet space...")
    space = google.meet.create_space()
    meet_link = space.get("meetingUri", "")
    meet_code = space.get("meetingCode", "")
    print(f"  Meet link: {meet_link}")
    print(f"  Meet code: {meet_code}")

    # Step 2: Create a calendar event with the Meet link
    print("\n[2/3] Creating Calendar event...")
    start = datetime.now(timezone.utc) + timedelta(days=1)
    end = start + timedelta(hours=1)

    event = google.calendar.create_event(
        summary="Team Sync - Created by EasyGoogleAPI",
        start=start,
        end=end,
        description=f"Join the meeting: {meet_link}\n\nMeeting code: {meet_code}",
        location=meet_link,
    )
    print(f"  Event: {event['summary']}")
    print(f"  When: {start.strftime('%Y-%m-%d %H:%M')} UTC")

    # Step 3: Create a meeting notes folder and doc placeholder
    print("\n[3/3] Creating meeting notes folder...")
    folder = google.drive.create_folder("Meeting Notes - EasyGoogleAPI Demo")
    print(f"  Folder: {folder['name']}")

    # Create a simple notes file
    notes_file = Path("/tmp/meeting_notes.txt")
    notes_content = f"""Meeting Notes Template
=====================

Meeting: Team Sync
Date: {start.strftime('%Y-%m-%d %H:%M')} UTC
Meet Link: {meet_link}

Attendees:
-

Agenda:
1.
2.
3.

Notes:


Action Items:
-
"""
    notes_file.write_text(notes_content)
    uploaded = google.drive.upload_file(str(notes_file), folder_id=folder["id"])
    notes_file.unlink()
    print(f"  Notes template: {uploaded['name']}")

    # Summary
    print("\n" + "=" * 50)
    print("SETUP COMPLETE!")
    print("=" * 50)
    print(f"\nMeet Link: {meet_link}")
    print(f"Calendar Event: {event.get('htmlLink', 'N/A')}")
    print(f"Notes Folder: https://drive.google.com/drive/folders/{folder['id']}")

    # Clean up
    print("\n[Cleaning up test resources...]")
    google.calendar.delete_event(event["id"])
    google.drive.delete_file(uploaded["id"])
    google.drive.delete_file(folder["id"])
    print("Done!")


if __name__ == "__main__":
    main()
