"""Google Meet API wrapper (gRPC-based).

Uses the ``google-apps-meet`` gRPC client library instead of the REST
discovery-based approach.  Install the optional dependency::

    pip install google-apps-meet
    # or
    uv add google-apps-meet
"""

from __future__ import annotations

from typing import Any

from .models import (
    ConferenceRecord,
    Participant,
    ParticipantSession,
    Space,
    Transcript,
    TranscriptEntry,
)


def _lazy_import(name: str) -> Any:
    """Lazily import a Meet gRPC class."""
    try:
        from google.apps import meet_v2
        if name == "meet_v2":
            return meet_v2
        return getattr(meet_v2, name)
    except ImportError as exc:
        raise ImportError(
            "The 'google-apps-meet' package is required for Meet support. "
            "Install it with:  pip install google-apps-meet"
        ) from exc


class MeetService:
    """Wrapper for Google Meet API operations (gRPC).

    Unlike other services, MeetService uses the gRPC ``SpacesServiceClient``
    rather than a REST discovery resource.

    Args:
        credentials: Authenticated Google credentials object.
    """

    def __init__(self, credentials: Any) -> None:
        self._credentials = credentials
        SpacesServiceClient = _lazy_import("SpacesServiceClient")
        self._client = SpacesServiceClient(credentials=credentials)
        self._records_client: Any = None

    @property
    def raw(self) -> Any:
        """Access the underlying gRPC SpacesServiceClient."""
        return self._client

    def _get_records_client(self) -> Any:
        """Get or create the ConferenceRecordsServiceClient (lazy)."""
        if self._records_client is None:
            ConferenceRecordsServiceClient = _lazy_import(
                "ConferenceRecordsServiceClient"
            )
            self._records_client = ConferenceRecordsServiceClient(
                credentials=self._credentials
            )
        return self._records_client

    # -----------------------------------------------------------------
    # Space operations
    # -----------------------------------------------------------------

    def create_space(
        self, access_type: str | None = None
    ) -> Space:
        """Create a new meeting space."""
        meet = _lazy_import("meet_v2")
        space_kwargs: dict[str, Any] = {}
        if access_type is not None:
            access_enum = meet.SpaceConfig.AccessType[access_type]
            space_kwargs["config"] = meet.SpaceConfig(access_type=access_enum)
        request = meet.CreateSpaceRequest(space=meet.Space(**space_kwargs))
        space = self._client.create_space(request=request)
        return Space.from_api_response(_space_to_dict(space))

    def get_space(self, space_name: str) -> Space:
        """Get a meeting space by resource name."""
        meet = _lazy_import("meet_v2")
        request = meet.GetSpaceRequest(name=space_name)
        space = self._client.get_space(request=request)
        return Space.from_api_response(_space_to_dict(space))

    def update_space(
        self,
        space_name: str,
        access_type: str | None = None,
    ) -> Space:
        """Update a meeting space's configuration."""
        meet = _lazy_import("meet_v2")
        from google.protobuf import field_mask_pb2

        space = meet.Space(name=space_name)
        update_paths: list[str] = []

        if access_type is not None:
            access_enum = meet.SpaceConfig.AccessType[access_type]
            space.config = meet.SpaceConfig(access_type=access_enum)
            update_paths.append("config.access_type")

        request = meet.UpdateSpaceRequest(
            space=space,
            update_mask=field_mask_pb2.FieldMask(paths=update_paths),
        )
        updated = self._client.update_space(request=request)
        return Space.from_api_response(_space_to_dict(updated))

    def end_active_conference(self, space_name: str) -> None:
        """End the active conference in a space."""
        meet = _lazy_import("meet_v2")
        request = meet.EndActiveConferenceRequest(name=space_name)
        self._client.end_active_conference(request=request)

    # -----------------------------------------------------------------
    # Conference records
    # -----------------------------------------------------------------

    def list_conference_records(
        self, space_name: str
    ) -> list[ConferenceRecord]:
        """List conference records for a space."""
        meet = _lazy_import("meet_v2")
        client = self._get_records_client()
        request = meet.ListConferenceRecordsRequest(
            filter=f'space.name = "{space_name}"'
        )
        return [
            ConferenceRecord.from_api_response(_conference_record_to_dict(r))
            for r in client.list_conference_records(request=request)
        ]

    def list_participants(
        self, conference_record_name: str
    ) -> list[Participant]:
        """List participants of a conference record."""
        meet = _lazy_import("meet_v2")
        client = self._get_records_client()
        request = meet.ListParticipantsRequest(parent=conference_record_name)
        return [
            Participant.from_api_response(_participant_to_dict(p))
            for p in client.list_participants(request=request)
        ]

    def list_participant_sessions(
        self, participant_name: str
    ) -> list[ParticipantSession]:
        """List sessions for a participant (join/leave pairs)."""
        meet = _lazy_import("meet_v2")
        client = self._get_records_client()
        request = meet.ListParticipantSessionsRequest(parent=participant_name)
        return [
            ParticipantSession.from_api_response(_session_to_dict(s))
            for s in client.list_participant_sessions(request=request)
        ]

    # -----------------------------------------------------------------
    # Transcripts
    # -----------------------------------------------------------------

    def list_transcripts(
        self, conference_record_name: str
    ) -> list[Transcript]:
        """List transcripts for a conference record."""
        meet = _lazy_import("meet_v2")
        client = self._get_records_client()
        request = meet.ListTranscriptsRequest(parent=conference_record_name)
        return [
            Transcript.from_api_response(_transcript_to_dict(t))
            for t in client.list_transcripts(request=request)
        ]

    def list_transcript_entries(
        self, transcript_name: str
    ) -> list[TranscriptEntry]:
        """List individual transcript entries (utterances)."""
        meet = _lazy_import("meet_v2")
        client = self._get_records_client()
        request = meet.ListTranscriptEntriesRequest(parent=transcript_name)
        return [
            TranscriptEntry.from_api_response(_transcript_entry_to_dict(e))
            for e in client.list_transcript_entries(request=request)
        ]


# =====================================================================
# Proto -> dict helpers
# =====================================================================


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


def _conference_record_to_dict(record: Any) -> dict[str, Any]:
    result: dict[str, Any] = {"name": record.name}
    if record.space:
        result["space"] = record.space
    if record.start_time:
        result["startTime"] = record.start_time.isoformat()
    if record.end_time:
        result["endTime"] = record.end_time.isoformat()
    return result


def _participant_to_dict(participant: Any) -> dict[str, Any]:
    result: dict[str, Any] = {"name": participant.name}
    if participant.signedin_user:
        result["signedinUser"] = {
            "user": participant.signedin_user.user,
            "displayName": participant.signedin_user.display_name or "",
        }
    elif participant.anonymous_user:
        result["anonymousUser"] = {
            "displayName": participant.anonymous_user.display_name or "",
        }
    elif participant.phone_user:
        result["phoneUser"] = {
            "displayName": participant.phone_user.display_name or "",
        }
    if participant.earliest_start_time:
        result["earliestStartTime"] = participant.earliest_start_time.isoformat()
    if participant.latest_end_time:
        result["latestEndTime"] = participant.latest_end_time.isoformat()
    return result


def _session_to_dict(session: Any) -> dict[str, Any]:
    result: dict[str, Any] = {"name": session.name}
    if session.start_time:
        result["startTime"] = session.start_time.isoformat()
    if session.end_time:
        result["endTime"] = session.end_time.isoformat()
    return result


def _transcript_to_dict(transcript: Any) -> dict[str, Any]:
    result: dict[str, Any] = {"name": transcript.name}
    if transcript.docs_destination:
        result["docsDestination"] = {
            "document": transcript.docs_destination.document,
            "exportUri": transcript.docs_destination.export_uri,
        }
    if transcript.start_time:
        result["startTime"] = transcript.start_time.isoformat()
    if transcript.end_time:
        result["endTime"] = transcript.end_time.isoformat()
    return result


def _transcript_entry_to_dict(entry: Any) -> dict[str, Any]:
    result: dict[str, Any] = {"name": entry.name}
    if entry.participant:
        result["participant"] = entry.participant
    if entry.text:
        result["text"] = entry.text
    if entry.language_code:
        result["languageCode"] = entry.language_code
    if entry.start_time:
        result["startTime"] = entry.start_time.isoformat()
    if entry.end_time:
        result["endTime"] = entry.end_time.isoformat()
    return result
