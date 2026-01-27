#!/usr/bin/env python3
"""Example: Gmail - List messages and labels."""

from pathlib import Path

from easygoogleapi import GoogleService

CREDENTIALS_PATH = Path(__file__).parent.parent / "tests" / "credentials.json"


def main():
    google = GoogleService(
        credentials_path=CREDENTIALS_PATH,
        services=["gmail"],
    )

    print("=== Gmail Labels ===")
    labels = google.gmail.list_labels()
    for label in labels[:10]:
        print(f"  - {label['name']}")

    print("\n=== Recent Messages ===")
    messages = google.gmail.list_messages(max_results=5)
    if not messages:
        print("  No messages found.")
    for msg in messages:
        details = google.gmail.get_message(msg["id"])
        headers = {h["name"]: h["value"] for h in details["payload"]["headers"]}
        subject = headers.get("Subject", "(no subject)")
        sender = headers.get("From", "(unknown)")
        print(f"  - {subject[:50]}")
        print(f"    From: {sender[:50]}")

    print("\n=== Unread Count ===")
    unread = google.gmail.list_messages(query="is:unread", max_results=100)
    print(f"  Unread messages: {len(unread)}")

    # Example: Send an email (commented out to avoid accidents)
    # google.gmail.send(
    #     to="recipient@example.com",
    #     subject="Test from EasyGoogleAPI",
    #     body="This is a test email sent using EasyGoogleAPI!",
    # )


if __name__ == "__main__":
    main()
