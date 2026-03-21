"""Google Meet API wrapper (gRPC-based).

Uses the ``google-apps-meet`` gRPC client library instead of the REST
discovery-based approach.  Install the optional dependency::

    pip install google-apps-meet
    # or
    uv add google-apps-meet
"""

from __future__ import annotations

import logging
import random
import time
import uuid
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar

from .._exceptions import (
    APIError,
    AuthenticationError,
    BackendError,
    ConflictError,
    EasyGoogleAPIError,
    InvalidRequestError,
    MaxRetriesExceededError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    ServerError,
)
from .models import (
    ConferenceRecord,
    Participant,
    ParticipantSession,
    Space,
    Transcript,
    TranscriptEntry,
)

if TYPE_CHECKING:
    from .._base import RetryConfig
    from .._middleware import MiddlewareChain

T = TypeVar("T")

logger = logging.getLogger("easygoogleapi")

# gRPC status code → library exception mapping.
# Codes are integers so we avoid importing grpc at module level.
_GRPC_STATUS_MAP: dict[int, type[APIError]] = {
    3: InvalidRequestError,    # INVALID_ARGUMENT
    5: NotFoundError,          # NOT_FOUND
    6: ConflictError,          # ALREADY_EXISTS
    7: PermissionDeniedError,  # PERMISSION_DENIED
    8: RateLimitError,         # RESOURCE_EXHAUSTED
    14: BackendError,          # UNAVAILABLE
}

# These codes map to retryable exceptions handled separately:
# 4 = DEADLINE_EXCEEDED → ServerError (retryable)
# 16 = UNAUTHENTICATED → AuthenticationError (non-retryable)


def _lazy_import(name: str) -> Any:
    """Lazily import a Meet gRPC class."""
    try:
        from google.apps import meet_v2
        if name == "meet_v2":
            return meet_v2
        return getattr(meet_v2, name)
    except ImportError as exc:
        raise ImportError(
            "The 'google-apps-meet' package is required for Meet "
            "support. Install it with:  pip install google-apps-meet"
        ) from exc


class MeetService:
    """Wrapper for Google Meet API operations (gRPC).

    Unlike other services, MeetService uses the gRPC
    ``SpacesServiceClient`` rather than a REST discovery resource.
    Provides retry logic with exponential backoff and maps gRPC
    status codes to the library's exception hierarchy.

    Args:
        credentials: Authenticated Google credentials object.
        retry_config: Retry behaviour configuration. Uses
            defaults (3 retries, exponential backoff) when *None*.
        middleware: Optional :class:`MiddlewareChain` for
            before/after request hooks.
    """

    def __init__(
        self,
        credentials: Any,
        retry_config: RetryConfig | None = None,
        middleware: MiddlewareChain | None = None,
    ) -> None:
        from .._base import RetryConfig as _RC

        self._credentials = credentials
        self._retry_config = retry_config or _RC()
        self._middleware = middleware

        SpacesServiceClient = _lazy_import("SpacesServiceClient")
        self._client = SpacesServiceClient(credentials=credentials)
        self._records_client: Any = None

    @property
    def raw(self) -> Any:
        """Access the underlying gRPC SpacesServiceClient."""
        return self._client

    def _get_records_client(self) -> Any:
        """Get or create the ConferenceRecordsServiceClient."""
        if self._records_client is None:
            ConferenceRecordsServiceClient = _lazy_import(
                "ConferenceRecordsServiceClient"
            )
            self._records_client = ConferenceRecordsServiceClient(
                credentials=self._credentials
            )
        return self._records_client

    # -----------------------------------------------------------------
    # Retry / error infrastructure
    # -----------------------------------------------------------------

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate backoff delay with exponential backoff + jitter."""
        delay = self._retry_config.base_delay * (
            self._retry_config.exponential_base ** attempt
        )
        delay = min(delay, self._retry_config.max_delay)
        if self._retry_config.jitter:
            delay = delay * (0.5 + random.random())
        return delay

    def _extract_grpc_code(self, exc: Exception) -> int | None:
        """Extract a gRPC status code integer from *exc*.

        Supports both ``google.api_core.exceptions.GoogleAPICallError``
        (has ``.grpc_status_code``) and raw ``grpc.RpcError`` (has
        ``.code()``).  Returns *None* when the code cannot be
        determined.
        """
        # google.api_core.exceptions.GoogleAPICallError
        grpc_code = getattr(exc, "grpc_status_code", None)
        if grpc_code is not None:
            if hasattr(grpc_code, "value"):
                return int(grpc_code.value[0])
            return int(grpc_code)

        # Raw grpc.RpcError
        code_fn = getattr(exc, "code", None)
        if callable(code_fn):
            try:
                code_obj = code_fn()
                # grpc.StatusCode is an enum whose .value is a (int, str) tuple
                if hasattr(code_obj, "value"):
                    return int(code_obj.value[0])
                return int(code_obj)
            except Exception:
                return None

        return None

    def _wrap_grpc_error(self, exc: Exception) -> EasyGoogleAPIError:
        """Map a gRPC / google-api-core exception to the library hierarchy."""
        code = self._extract_grpc_code(exc)
        message = str(exc)

        if code is None:
            return APIError(
                f"gRPC call failed: {message}",
                original_error=exc,
            )

        # DEADLINE_EXCEEDED (4) → ServerError (retryable)
        if code == 4:
            return ServerError(
                message,
                original_error=exc,
            )

        # UNAUTHENTICATED (16) → AuthenticationError
        if code == 16:
            return AuthenticationError(message)

        exc_cls = _GRPC_STATUS_MAP.get(code)
        if exc_cls is not None:
            return exc_cls(message, original_error=exc)

        return APIError(
            f"gRPC call failed (code={code}): {message}",
            original_error=exc,
        )

    def _execute_grpc(
        self,
        method_name: str,
        fn: Callable[[], T],
    ) -> T:
        """Execute a gRPC call with retry logic and error mapping.

        Args:
            method_name: Logical method name for logging / middleware.
            fn: Zero-argument callable that performs the actual gRPC
                call and returns the result.

        Returns:
            The value returned by *fn*.

        Raises:
            APIError: (or subclass) when the call fails permanently.
            MaxRetriesExceededError: when all retry attempts are
                exhausted.
        """
        from .._middleware import RequestContext, ResponseContext

        correlation_id = str(uuid.uuid4()) if self._middleware else ""
        last_error: Exception | None = None

        for attempt in range(self._retry_config.max_retries + 1):
            # --- before middleware ---
            req_ctx = None
            if self._middleware:
                req_ctx = RequestContext(
                    service_name="MeetService",
                    method_name=method_name,
                    attempt=attempt,
                    correlation_id=correlation_id,
                )
                self._middleware.fire_before(req_ctx)

            start = time.monotonic()

            try:
                logger.debug(
                    "[%s] gRPC %s attempt %d/%d",
                    correlation_id[:8],
                    method_name,
                    attempt + 1,
                    self._retry_config.max_retries + 1,
                )
                result = fn()
                duration_ms = (time.monotonic() - start) * 1000

                # --- after middleware (success) ---
                if self._middleware and req_ctx:
                    self._middleware.fire_after(
                        ResponseContext(
                            request=req_ctx,
                            duration_ms=duration_ms,
                            status_code=0,  # gRPC OK
                            retried=attempt > 0,
                        )
                    )

                if attempt > 0:
                    logger.info(
                        "[%s] Succeeded after %d attempts",
                        correlation_id[:8],
                        attempt + 1,
                    )

                return result

            except Exception as exc:
                duration_ms = (time.monotonic() - start) * 1000
                last_error = exc
                wrapped = self._wrap_grpc_error(exc)

                # --- after middleware (error) ---
                if self._middleware and req_ctx:
                    grpc_code = self._extract_grpc_code(exc)
                    self._middleware.fire_after(
                        ResponseContext(
                            request=req_ctx,
                            duration_ms=duration_ms,
                            status_code=grpc_code,
                            error=wrapped,
                            retried=attempt > 0,
                        )
                    )

                if (
                    not wrapped.retryable
                    or attempt >= self._retry_config.max_retries
                ):
                    logger.error(
                        "[%s] Non-retryable or final attempt: %s",
                        correlation_id[:8],
                        wrapped.message,
                    )
                    raise wrapped from exc

                delay = self._calculate_backoff(attempt)
                logger.warning(
                    "[%s] Retryable error: %s. Retrying in %.2fs",
                    correlation_id[:8],
                    wrapped.message,
                    delay,
                )
                time.sleep(delay)

        # Should be unreachable, but keeps type checkers happy.
        raise MaxRetriesExceededError(
            f"gRPC call '{method_name}' failed after "
            f"{self._retry_config.max_retries + 1} attempts",
            attempts=self._retry_config.max_retries + 1,
            last_error=last_error,
        )

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
            space_kwargs["config"] = meet.SpaceConfig(
                access_type=access_enum
            )
        request = meet.CreateSpaceRequest(
            space=meet.Space(**space_kwargs)
        )

        def _call() -> Space:
            raw = self._client.create_space(request=request)
            return Space.from_api_response(_space_to_dict(raw))

        return self._execute_grpc("create_space", _call)

    def get_space(self, space_name: str) -> Space:
        """Get a meeting space by resource name."""
        meet = _lazy_import("meet_v2")
        request = meet.GetSpaceRequest(name=space_name)

        def _call() -> Space:
            raw = self._client.get_space(request=request)
            return Space.from_api_response(_space_to_dict(raw))

        return self._execute_grpc("get_space", _call)

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
            space.config = meet.SpaceConfig(
                access_type=access_enum
            )
            update_paths.append("config.access_type")

        request = meet.UpdateSpaceRequest(
            space=space,
            update_mask=field_mask_pb2.FieldMask(
                paths=update_paths
            ),
        )

        def _call() -> Space:
            raw = self._client.update_space(request=request)
            return Space.from_api_response(_space_to_dict(raw))

        return self._execute_grpc("update_space", _call)

    def end_active_conference(self, space_name: str) -> None:
        """End the active conference in a space."""
        meet = _lazy_import("meet_v2")
        request = meet.EndActiveConferenceRequest(name=space_name)

        def _call() -> None:
            self._client.end_active_conference(request=request)

        self._execute_grpc("end_active_conference", _call)

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

        def _call() -> list[ConferenceRecord]:
            return [
                ConferenceRecord.from_api_response(
                    _conference_record_to_dict(r)
                )
                for r in client.list_conference_records(
                    request=request
                )
            ]

        return self._execute_grpc("list_conference_records", _call)

    def list_participants(
        self, conference_record_name: str
    ) -> list[Participant]:
        """List participants of a conference record."""
        meet = _lazy_import("meet_v2")
        client = self._get_records_client()
        request = meet.ListParticipantsRequest(
            parent=conference_record_name
        )

        def _call() -> list[Participant]:
            return [
                Participant.from_api_response(
                    _participant_to_dict(p)
                )
                for p in client.list_participants(
                    request=request
                )
            ]

        return self._execute_grpc("list_participants", _call)

    def list_participant_sessions(
        self, participant_name: str
    ) -> list[ParticipantSession]:
        """List sessions for a participant (join/leave pairs)."""
        meet = _lazy_import("meet_v2")
        client = self._get_records_client()
        request = meet.ListParticipantSessionsRequest(
            parent=participant_name
        )

        def _call() -> list[ParticipantSession]:
            return [
                ParticipantSession.from_api_response(
                    _session_to_dict(s)
                )
                for s in client.list_participant_sessions(
                    request=request
                )
            ]

        return self._execute_grpc(
            "list_participant_sessions", _call
        )

    # -----------------------------------------------------------------
    # Transcripts
    # -----------------------------------------------------------------

    def list_transcripts(
        self, conference_record_name: str
    ) -> list[Transcript]:
        """List transcripts for a conference record."""
        meet = _lazy_import("meet_v2")
        client = self._get_records_client()
        request = meet.ListTranscriptsRequest(
            parent=conference_record_name
        )

        def _call() -> list[Transcript]:
            return [
                Transcript.from_api_response(
                    _transcript_to_dict(t)
                )
                for t in client.list_transcripts(request=request)
            ]

        return self._execute_grpc("list_transcripts", _call)

    def list_transcript_entries(
        self, transcript_name: str
    ) -> list[TranscriptEntry]:
        """List individual transcript entries (utterances)."""
        meet = _lazy_import("meet_v2")
        client = self._get_records_client()
        request = meet.ListTranscriptEntriesRequest(
            parent=transcript_name
        )

        def _call() -> list[TranscriptEntry]:
            return [
                TranscriptEntry.from_api_response(
                    _transcript_entry_to_dict(e)
                )
                for e in client.list_transcript_entries(
                    request=request
                )
            ]

        return self._execute_grpc(
            "list_transcript_entries", _call
        )


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
            "entryPointAccess": (
                space.config.entry_point_access.name
                if space.config.entry_point_access
                else None
            ),
        }
    if space.active_conference:
        result["activeConference"] = {
            "conferenceRecord": (
                space.active_conference.conference_record
            ),
        }
    return result


def _conference_record_to_dict(
    record: Any,
) -> dict[str, Any]:
    result: dict[str, Any] = {"name": record.name}
    if record.space:
        result["space"] = record.space
    if record.start_time:
        result["startTime"] = record.start_time.isoformat()
    if record.end_time:
        result["endTime"] = record.end_time.isoformat()
    return result


def _participant_to_dict(
    participant: Any,
) -> dict[str, Any]:
    result: dict[str, Any] = {"name": participant.name}
    if participant.signedin_user:
        result["signedinUser"] = {
            "user": participant.signedin_user.user,
            "displayName": (
                participant.signedin_user.display_name or ""
            ),
        }
    elif participant.anonymous_user:
        result["anonymousUser"] = {
            "displayName": (
                participant.anonymous_user.display_name or ""
            ),
        }
    elif participant.phone_user:
        result["phoneUser"] = {
            "displayName": (
                participant.phone_user.display_name or ""
            ),
        }
    if participant.earliest_start_time:
        result["earliestStartTime"] = (
            participant.earliest_start_time.isoformat()
        )
    if participant.latest_end_time:
        result["latestEndTime"] = (
            participant.latest_end_time.isoformat()
        )
    return result


def _session_to_dict(session: Any) -> dict[str, Any]:
    result: dict[str, Any] = {"name": session.name}
    if session.start_time:
        result["startTime"] = session.start_time.isoformat()
    if session.end_time:
        result["endTime"] = session.end_time.isoformat()
    return result


def _transcript_to_dict(
    transcript: Any,
) -> dict[str, Any]:
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


def _transcript_entry_to_dict(
    entry: Any,
) -> dict[str, Any]:
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
