"""Typed response models for Google Meet API."""

from dataclasses import dataclass, field
from typing import Any

from .._models import GoogleModel


@dataclass
class SpaceConfig(GoogleModel):
    """Configuration for a Meet space."""

    access_type: str | None = None
    entry_point_access: str | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "SpaceConfig":
        return cls(
            access_type=data.get("accessType"),
            entry_point_access=data.get("entryPointAccess"),
        )


@dataclass
class ActiveConference(GoogleModel):
    """An active conference in a space."""

    conference_record: str = ""

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "ActiveConference":
        return cls(conference_record=data.get("conferenceRecord", ""))


@dataclass
class Space(GoogleModel):
    """A Google Meet space."""

    name: str = ""
    meeting_uri: str | None = None
    meeting_code: str | None = None
    config: SpaceConfig | None = None
    active_conference: ActiveConference | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "Space":
        config_data = data.get("config")
        active_data = data.get("activeConference")
        return cls(
            name=data.get("name", ""),
            meeting_uri=data.get("meetingUri"),
            meeting_code=data.get("meetingCode"),
            config=SpaceConfig.from_api_response(config_data) if config_data else None,
            active_conference=ActiveConference.from_api_response(active_data)
            if active_data
            else None,
        )


@dataclass
class ConferenceRecord(GoogleModel):
    """A post-meeting conference record."""

    name: str = ""
    space: str | None = None
    start_time: str | None = None
    end_time: str | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "ConferenceRecord":
        return cls(
            name=data.get("name", ""),
            space=data.get("space"),
            start_time=data.get("startTime"),
            end_time=data.get("endTime"),
        )


@dataclass
class Participant(GoogleModel):
    """A conference participant."""

    name: str = ""
    display_name: str | None = None
    user_type: str | None = None
    earliest_start_time: str | None = None
    latest_end_time: str | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "Participant":
        display = None
        user_type = None
        if "signedinUser" in data:
            display = data["signedinUser"].get("displayName")
            user_type = "signed_in"
        elif "anonymousUser" in data:
            display = data["anonymousUser"].get("displayName")
            user_type = "anonymous"
        elif "phoneUser" in data:
            display = data["phoneUser"].get("displayName")
            user_type = "phone"

        return cls(
            name=data.get("name", ""),
            display_name=display,
            user_type=user_type,
            earliest_start_time=data.get("earliestStartTime"),
            latest_end_time=data.get("latestEndTime"),
        )


@dataclass
class ParticipantSession(GoogleModel):
    """A participant's session (join/leave pair)."""

    name: str = ""
    start_time: str | None = None
    end_time: str | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "ParticipantSession":
        return cls(
            name=data.get("name", ""),
            start_time=data.get("startTime"),
            end_time=data.get("endTime"),
        )


@dataclass
class TranscriptEntry(GoogleModel):
    """A single transcript utterance."""

    name: str = ""
    participant: str | None = None
    text: str | None = None
    language_code: str | None = None
    start_time: str | None = None
    end_time: str | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "TranscriptEntry":
        return cls(
            name=data.get("name", ""),
            participant=data.get("participant"),
            text=data.get("text"),
            language_code=data.get("languageCode"),
            start_time=data.get("startTime"),
            end_time=data.get("endTime"),
        )


@dataclass
class Transcript(GoogleModel):
    """A meeting transcript."""

    name: str = ""
    docs_destination: dict[str, Any] = field(default_factory=dict)
    start_time: str | None = None
    end_time: str | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "Transcript":
        return cls(
            name=data.get("name", ""),
            docs_destination=data.get("docsDestination", {}),
            start_time=data.get("startTime"),
            end_time=data.get("endTime"),
        )
