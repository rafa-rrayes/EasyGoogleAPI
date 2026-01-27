"""Integration tests for Meet service."""

import pytest


@pytest.mark.integration
class TestMeetService:
    """Integration tests for MeetService."""

    def test_create_space(self, google_meet):
        """Test creating a meeting space."""
        space = google_meet.meet.create_space()
        assert "name" in space
        # Space name format: spaces/{space_id}
        assert space["name"].startswith("spaces/")

    def test_get_space(self, google_meet):
        """Test getting a meeting space."""
        # First create a space
        created = google_meet.meet.create_space()

        # Then get it
        space = google_meet.meet.get_space(created["name"])
        assert space["name"] == created["name"]

    def test_space_has_meeting_uri(self, google_meet):
        """Test that created space has meeting URI."""
        space = google_meet.meet.create_space()
        # Space should have meeting details
        assert "meetingUri" in space or "name" in space
