"""Google Meet API wrapper."""

from typing import Any

from .._base import BaseService


class MeetService(BaseService):
    """Wrapper for Google Meet API operations."""

    def create_space(self) -> dict[str, Any]:
        """Create a new meeting space."""
        request = self._resource.spaces().create(body={})
        return self._execute_request(request)

    def get_space(self, space_name: str) -> dict[str, Any]:
        """Get a meeting space by name."""
        request = self._resource.spaces().get(name=space_name)
        return self._execute_request(request)

    def end_active_conference(self, space_name: str) -> None:
        """End the active conference in a space."""
        request = self._resource.spaces().endActiveConference(
            name=space_name, body={}
        )
        self._execute_request(request)

    def list_participants(
        self, conference_record_name: str, page_size: int = 50
    ) -> list[dict[str, Any]]:
        """List participants of a conference."""
        request = (
            self._resource.conferenceRecords()
            .participants()
            .list(parent=conference_record_name, pageSize=page_size)
        )
        result = self._execute_request(request)
        return result.get("participants", [])

    def list_recordings(
        self, conference_record_name: str
    ) -> list[dict[str, Any]]:
        """List recordings of a conference."""
        request = (
            self._resource.conferenceRecords()
            .recordings()
            .list(parent=conference_record_name)
        )
        result = self._execute_request(request)
        return result.get("recordings", [])
