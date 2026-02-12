"""Google Meet API wrapper (gRPC-based).

Uses the ``google-apps-meet`` gRPC client library instead of the REST
discovery-based approach.  Install the optional dependency::

    pip install google-apps-meet
    # or
    uv add google-apps-meet
"""

from __future__ import annotations

from typing import Any


def _get_spaces_client():
    """Lazily import and return the SpacesServiceClient class."""
    try:
        from google.apps.meet_v2 import SpacesServiceClient
    except ImportError as exc:
        raise ImportError(
            "The 'google-apps-meet' package is required for Meet support. "
            "Install it with:  pip install google-apps-meet"
        ) from exc
    return SpacesServiceClient


def _get_meet_types():
    """Lazily import meet_v2 types."""
    try:
        from google.apps import meet_v2
    except ImportError as exc:
        raise ImportError(
            "The 'google-apps-meet' package is required for Meet support. "
            "Install it with:  pip install google-apps-meet"
        ) from exc
    return meet_v2


class MeetService:
    """Wrapper for Google Meet API operations (gRPC).

    Unlike other services, MeetService does **not** inherit from
    ``BaseService`` because it uses the gRPC ``SpacesServiceClient``
    rather than a REST discovery resource.

    Args:
        credentials: Authenticated Google credentials object.
    """

    def __init__(self, credentials: Any) -> None:
        SpacesServiceClient = _get_spaces_client()
        self._client = SpacesServiceClient(credentials=credentials)

    def create_space(self) -> dict[str, Any]:
        """Create a new meeting space."""
        meet = _get_meet_types()
        request = meet.CreateSpaceRequest(space=meet.Space())
        space = self._client.create_space(request=request)
        return _space_to_dict(space)

    def get_space(self, space_name: str) -> dict[str, Any]:
        """Get a meeting space by resource name."""
        meet = _get_meet_types()
        request = meet.GetSpaceRequest(name=space_name)
        space = self._client.get_space(request=request)
        return _space_to_dict(space)

    def end_active_conference(self, space_name: str) -> None:
        """End the active conference in a space."""
        meet = _get_meet_types()
        request = meet.EndActiveConferenceRequest(name=space_name)
        self._client.end_active_conference(request=request)


def _space_to_dict(space: Any) -> dict[str, Any]:
    """Convert a gRPC Space proto to a plain dict."""
    result: dict[str, Any] = {"name": space.name}
    if space.meeting_uri:
        result["meetingUri"] = space.meeting_uri
    if space.meeting_code:
        result["meetingCode"] = space.meeting_code
    if space.config:
        result["config"] = {
            "accessType": space.config.access_type.name
            if space.config.access_type
            else None,
            "entryPointAccess": space.config.entry_point_access.name
            if space.config.entry_point_access
            else None,
        }
    if space.active_conference:
        result["activeConference"] = {
            "conferenceRecord": space.active_conference.conference_record,
        }
    return result
