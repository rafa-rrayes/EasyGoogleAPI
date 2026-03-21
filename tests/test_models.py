"""Tests for typed response models (v2.0)."""

import pytest

from easygoogleapi._models import GoogleModel
from easygoogleapi.calendar.models import Attendee, CalendarMeta, Event, EventList
from easygoogleapi.drive.models import FileList, FileMetadata, Permission, StorageQuota
from easygoogleapi.gmail.models import Draft, Label, Message, MessageList, Thread


class TestGoogleModelBase:
    """Tests for the GoogleModel base class."""

    def test_from_api_response_raises_not_implemented(self):
        """Test that base GoogleModel.from_api_response raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            GoogleModel.from_api_response({"key": "value"})


class TestFileMetadata:
    """Tests for Drive FileMetadata model."""

    def test_from_api_response_full(self):
        """Test from_api_response with full data."""
        data = {
            "id": "file_123",
            "name": "test.txt",
            "mimeType": "text/plain",
            "modifiedTime": "2025-01-15T10:30:00Z",
            "size": "1024",
            "webViewLink": "https://drive.google.com/file/123",
            "parents": ["folder_abc"],
            "trashed": False,
            "description": "A test file",
        }
        file = FileMetadata.from_api_response(data)

        assert file.id == "file_123"
        assert file.name == "test.txt"
        assert file.mime_type == "text/plain"
        assert file.modified_time == "2025-01-15T10:30:00Z"
        assert file.size == "1024"
        assert file.web_view_link == "https://drive.google.com/file/123"
        assert file.parents == ["folder_abc"]
        assert file.trashed is False
        assert file.description == "A test file"

    def test_from_api_response_minimal(self):
        """Test from_api_response with minimal data."""
        data = {"id": "file_456"}
        file = FileMetadata.from_api_response(data)

        assert file.id == "file_456"
        assert file.name == ""
        assert file.mime_type == ""
        assert file.modified_time is None
        assert file.size is None
        assert file.web_view_link is None
        assert file.parents == []
        assert file.trashed is False
        assert file.description is None

    def test_missing_optional_fields_default_to_none(self):
        """Test that missing optional fields default to None."""
        file = FileMetadata.from_api_response({})
        assert file.modified_time is None
        assert file.size is None
        assert file.web_view_link is None
        assert file.description is None

    def test_attribute_access(self):
        """Test attribute access (model.name, not model['name'])."""
        file = FileMetadata.from_api_response({"id": "x", "name": "hello.txt"})
        assert file.name == "hello.txt"
        assert file.id == "x"

    def test_to_dict_round_trip(self):
        """Test to_dict produces a plain dict that preserves all data."""
        data = {
            "id": "file_123",
            "name": "test.txt",
            "mimeType": "text/plain",
            "parents": ["folder_abc"],
        }
        file = FileMetadata.from_api_response(data)
        result = file.to_dict()

        assert isinstance(result, dict)
        assert result["id"] == "file_123"
        assert result["name"] == "test.txt"
        assert result["mime_type"] == "text/plain"
        assert result["parents"] == ["folder_abc"]

    def test_repr_produces_readable_output(self):
        """Test that __repr__ produces readable output."""
        file = FileMetadata.from_api_response({"id": "f1", "name": "doc.pdf"})
        repr_str = repr(file)

        assert "FileMetadata(" in repr_str
        assert "id=" in repr_str
        assert "name=" in repr_str


class TestFileList:
    """Tests for Drive FileList model."""

    def test_from_api_response(self):
        """Test FileList.from_api_response."""
        data = {
            "files": [
                {"id": "f1", "name": "a.txt"},
                {"id": "f2", "name": "b.txt"},
            ],
            "nextPageToken": "page2",
        }
        result = FileList.from_api_response(data)

        assert len(result.files) == 2
        assert isinstance(result.files[0], FileMetadata)
        assert result.files[0].id == "f1"
        assert result.next_page_token == "page2"

    def test_from_api_response_empty(self):
        """Test FileList with empty files."""
        result = FileList.from_api_response({"files": []})
        assert result.files == []
        assert result.next_page_token is None


class TestPermission:
    """Tests for Drive Permission model."""

    def test_from_api_response(self):
        """Test Permission.from_api_response."""
        data = {
            "id": "perm1",
            "role": "reader",
            "type": "user",
            "emailAddress": "user@example.com",
        }
        perm = Permission.from_api_response(data)

        assert perm.id == "perm1"
        assert perm.role == "reader"
        assert perm.type == "user"
        assert perm.email_address == "user@example.com"

    def test_missing_email(self):
        """Test Permission with missing email."""
        perm = Permission.from_api_response(
            {"id": "p1", "role": "owner", "type": "user"},
        )
        assert perm.email_address is None


class TestStorageQuota:
    """Tests for Drive StorageQuota model."""

    def test_from_api_response(self):
        """Test StorageQuota.from_api_response."""
        data = {
            "limit": "16106127360",
            "usage": "1234567890",
            "usageInDrive": "999999999",
            "usageInDriveTrash": "100000",
        }
        quota = StorageQuota.from_api_response(data)

        assert quota.limit == "16106127360"
        assert quota.usage == "1234567890"
        assert quota.usage_in_drive == "999999999"
        assert quota.usage_in_drive_trash == "100000"

    def test_all_none(self):
        """Test StorageQuota with empty data."""
        quota = StorageQuota.from_api_response({})
        assert quota.limit is None
        assert quota.usage is None


class TestEvent:
    """Tests for Calendar Event model."""

    def test_from_api_response_full(self):
        """Test Event.from_api_response with all fields."""
        data = {
            "id": "evt_123",
            "summary": "Team Meeting",
            "description": "Weekly sync",
            "location": "Room 42",
            "start": {"dateTime": "2025-01-15T10:00:00Z"},
            "end": {"dateTime": "2025-01-15T11:00:00Z"},
            "attendees": [
                {
                    "email": "a@example.com",
                    "displayName": "Alice",
                    "responseStatus": "accepted",
                },
            ],
            "status": "confirmed",
            "htmlLink": "https://calendar.google.com/...",
            "created": "2025-01-01T00:00:00Z",
            "updated": "2025-01-14T12:00:00Z",
        }
        event = Event.from_api_response(data)

        assert event.id == "evt_123"
        assert event.summary == "Team Meeting"
        assert event.description == "Weekly sync"
        assert event.location == "Room 42"
        assert event.start == {"dateTime": "2025-01-15T10:00:00Z"}
        assert event.status == "confirmed"
        assert len(event.attendees) == 1
        assert isinstance(event.attendees[0], Attendee)
        assert event.attendees[0].email == "a@example.com"
        assert event.attendees[0].display_name == "Alice"

    def test_from_api_response_minimal(self):
        """Test Event with minimal data."""
        event = Event.from_api_response({"id": "e1"})
        assert event.id == "e1"
        assert event.summary is None
        assert event.attendees == []
        assert event.start == {}

    def test_to_dict_with_nested_models(self):
        """Test to_dict with nested Attendee models."""
        data = {
            "id": "e1",
            "attendees": [{"email": "user@test.com"}],
        }
        event = Event.from_api_response(data)
        result = event.to_dict()

        assert isinstance(result["attendees"], list)
        assert isinstance(result["attendees"][0], dict)
        assert result["attendees"][0]["email"] == "user@test.com"


class TestAttendee:
    """Tests for Calendar Attendee model."""

    def test_from_api_response(self):
        """Test Attendee.from_api_response."""
        attendee = Attendee.from_api_response({
            "email": "bob@test.com",
            "displayName": "Bob",
            "responseStatus": "tentative",
        })
        assert attendee.email == "bob@test.com"
        assert attendee.display_name == "Bob"
        assert attendee.response_status == "tentative"

    def test_missing_optional(self):
        """Test Attendee with missing optional fields."""
        attendee = Attendee.from_api_response({"email": "test@test.com"})
        assert attendee.display_name is None
        assert attendee.response_status is None


class TestMessage:
    """Tests for Gmail Message model."""

    def test_from_api_response_full(self):
        """Test Message.from_api_response with full data."""
        data = {
            "id": "msg_123",
            "threadId": "thread_456",
            "labelIds": ["INBOX", "UNREAD"],
            "snippet": "Hello world...",
            "payload": {"mimeType": "text/plain"},
            "internalDate": "1705302000000",
            "raw": None,
        }
        msg = Message.from_api_response(data)

        assert msg.id == "msg_123"
        assert msg.thread_id == "thread_456"
        assert msg.label_ids == ["INBOX", "UNREAD"]
        assert msg.snippet == "Hello world..."
        assert msg.payload == {"mimeType": "text/plain"}

    def test_from_api_response_minimal(self):
        """Test Message with minimal data."""
        msg = Message.from_api_response({"id": "m1"})
        assert msg.id == "m1"
        assert msg.thread_id is None
        assert msg.label_ids == []
        assert msg.snippet is None

    def test_attribute_access(self):
        """Test attribute access on Message."""
        msg = Message.from_api_response({"id": "m1", "snippet": "test"})
        assert msg.snippet == "test"


class TestLabel:
    """Tests for Gmail Label model."""

    def test_from_api_response(self):
        """Test Label.from_api_response."""
        label = Label.from_api_response(
            {"id": "INBOX", "name": "Inbox", "type": "system"},
        )
        assert label.id == "INBOX"
        assert label.name == "Inbox"
        assert label.type == "system"


class TestThread:
    """Tests for Gmail Thread model."""

    def test_from_api_response(self):
        """Test Thread.from_api_response."""
        data = {
            "id": "t1",
            "snippet": "Thread snippet",
            "messages": [{"id": "m1"}, {"id": "m2"}],
        }
        thread = Thread.from_api_response(data)
        assert thread.id == "t1"
        assert len(thread.messages) == 2
        assert isinstance(thread.messages[0], Message)


class TestDraft:
    """Tests for Gmail Draft model."""

    def test_from_api_response_with_message(self):
        """Test Draft.from_api_response with a message."""
        data = {
            "id": "draft_1",
            "message": {"id": "m1", "snippet": "Draft content"},
        }
        draft = Draft.from_api_response(data)
        assert draft.id == "draft_1"
        assert isinstance(draft.message, Message)
        assert draft.message.id == "m1"

    def test_from_api_response_without_message(self):
        """Test Draft.from_api_response without a message."""
        draft = Draft.from_api_response({"id": "draft_2"})
        assert draft.id == "draft_2"
        assert draft.message is None


class TestCalendarMeta:
    """Tests for CalendarMeta model."""

    def test_from_api_response(self):
        """Test CalendarMeta.from_api_response."""
        data = {
            "id": "cal_1",
            "summary": "My Calendar",
            "description": "Personal calendar",
            "timeZone": "America/New_York",
        }
        cal = CalendarMeta.from_api_response(data)
        assert cal.id == "cal_1"
        assert cal.summary == "My Calendar"
        assert cal.time_zone == "America/New_York"


class TestEventList:
    """Tests for Calendar EventList model."""

    def test_from_api_response(self):
        """Test EventList.from_api_response with items key."""
        data = {
            "items": [{"id": "e1"}, {"id": "e2"}],
            "nextPageToken": "next",
        }
        result = EventList.from_api_response(data)
        assert len(result.events) == 2
        assert isinstance(result.events[0], Event)
        assert result.next_page_token == "next"


class TestMessageList:
    """Tests for Gmail MessageList model."""

    def test_from_api_response(self):
        """Test MessageList.from_api_response."""
        data = {
            "messages": [{"id": "m1"}, {"id": "m2"}],
            "nextPageToken": "tok",
            "resultSizeEstimate": 42,
        }
        result = MessageList.from_api_response(data)
        assert len(result.messages) == 2
        assert result.next_page_token == "tok"
        assert result.result_size_estimate == 42


class TestModelRepr:
    """Tests for model __repr__ output."""

    def test_repr_shows_all_fields(self):
        """Test that repr includes all dataclass fields."""
        file = FileMetadata.from_api_response({
            "id": "f1", "name": "test.txt", "mimeType": "text/plain",
            "modifiedTime": "2025-01-01",
        })
        repr_str = repr(file)
        assert "FileMetadata(" in repr_str
        assert "id=" in repr_str
        assert "name=" in repr_str

    def test_repr_short_model(self):
        """Test repr for a model with 3 or fewer fields."""
        label = Label.from_api_response({"id": "INBOX", "name": "Inbox"})
        repr_str = repr(label)
        assert "Label(" in repr_str
        assert "id=" in repr_str
        assert "name=" in repr_str


class TestToDictRoundTrip:
    """Tests for to_dict producing serializable output."""

    def test_file_metadata_round_trip(self):
        """Test FileMetadata to_dict produces a plain dict."""
        original = {
            "id": "f1",
            "name": "test.txt",
            "mimeType": "text/plain",
            "parents": ["folder1"],
        }
        file = FileMetadata.from_api_response(original)
        result = file.to_dict()

        assert isinstance(result, dict)
        assert result["id"] == "f1"
        assert result["name"] == "test.txt"

    def test_nested_model_round_trip(self):
        """Test to_dict with nested models (Event -> Attendee)."""
        data = {
            "id": "e1",
            "summary": "Meeting",
            "attendees": [
                {"email": "a@test.com", "displayName": "Alice"},
                {"email": "b@test.com", "displayName": "Bob"},
            ],
        }
        event = Event.from_api_response(data)
        result = event.to_dict()

        assert isinstance(result["attendees"], list)
        assert all(isinstance(a, dict) for a in result["attendees"])
        assert result["attendees"][0]["email"] == "a@test.com"

    def test_draft_nested_model_round_trip(self):
        """Test to_dict with Draft containing a nested Message."""
        draft = Draft.from_api_response({
            "id": "d1",
            "message": {"id": "m1", "snippet": "Hello"},
        })
        result = draft.to_dict()

        assert isinstance(result["message"], dict)
        assert result["message"]["id"] == "m1"
