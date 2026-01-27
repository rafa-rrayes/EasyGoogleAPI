"""Integration tests for Gmail service."""

import pytest


@pytest.mark.integration
class TestGmailService:
    """Integration tests for GmailService."""

    def test_list_labels(self, google_gmail):
        """Test listing labels."""
        labels = google_gmail.gmail.list_labels()
        assert isinstance(labels, list)
        # Gmail always has some default labels
        assert len(labels) > 0

    def test_list_messages(self, google_gmail):
        """Test listing messages."""
        messages = google_gmail.gmail.list_messages(max_results=5)
        assert isinstance(messages, list)

    def test_list_messages_with_query(self, google_gmail):
        """Test listing messages with a search query."""
        messages = google_gmail.gmail.list_messages(
            query="is:unread", max_results=5
        )
        assert isinstance(messages, list)

    def test_get_message(self, google_gmail):
        """Test getting a specific message."""
        # First get a message ID
        messages = google_gmail.gmail.list_messages(max_results=1)
        if not messages:
            pytest.skip("No messages in mailbox to test with")

        message = google_gmail.gmail.get_message(messages[0]["id"])
        assert "id" in message
        assert "payload" in message

    # Note: send() test is commented out to avoid sending actual emails
    # def test_send_email(self, google_gmail):
    #     """Test sending an email."""
    #     result = google_gmail.gmail.send(
    #         to="test@example.com",
    #         subject="Test from EasyGoogleAPI",
    #         body="This is a test email.",
    #     )
    #     assert "id" in result
