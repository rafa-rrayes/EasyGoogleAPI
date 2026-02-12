# Google Meet

`MeetService` wraps the Google Meet API using the gRPC `google-apps-meet` client library. Unlike other services, **MeetService does not inherit from `BaseService`** because it uses the gRPC `SpacesServiceClient` rather than a REST discovery resource.

## Installation

Meet support requires the optional `google-apps-meet` dependency:

```bash
pip install easygoogleapi[meet]
```

Or install the dependency directly:

```bash
pip install google-apps-meet
```

If the dependency is not installed, importing or accessing `google.meet` will raise an `ImportError` with installation instructions.

## Usage

```python
google = GoogleService(credentials_path="creds.json", services=["meet"])
meet = google.meet
```

## Return Format

All methods return plain Python dicts converted from gRPC protobuf objects. The conversion extracts available fields from the `Space` proto.

## Methods

### create_space

```python
def create_space(self) -> dict[str, Any]
```

Create a new meeting space. Returns a dict with available fields:

- `name`: The space resource name (e.g. `"spaces/abc123"`)
- `meetingUri`: The URL to join the meeting (if available)
- `meetingCode`: The meeting code (if available)
- `config`: Space configuration with `accessType` and `entryPointAccess` (if available)
- `activeConference`: Active conference info with `conferenceRecord` (if available)

```python
space = google.meet.create_space()
print(f"Join: {space['meetingUri']}")
print(f"Code: {space['meetingCode']}")
```

### get_space

```python
def get_space(self, space_name: str) -> dict[str, Any]
```

Get a meeting space by its resource name. Returns the same dict format as `create_space()`.

- `space_name`: The space resource name (e.g. `"spaces/abc123"`).

```python
space = google.meet.get_space("spaces/abc123")
```

### end_active_conference

```python
def end_active_conference(self, space_name: str) -> None
```

End the active conference in a space.

- `space_name`: The space resource name.

```python
google.meet.end_active_conference("spaces/abc123")
```

## Differences from Other Services

| Feature | Other services | MeetService |
|---------|---------------|-------------|
| Base class | `BaseService` | None (standalone) |
| API client | REST discovery (`googleapiclient`) | gRPC (`google.apps.meet_v2.SpacesServiceClient`) |
| `.raw` property | Yes | No |
| Automatic retry | Yes | No |
| Error wrapping | Yes (`APIError` subclasses) | No (raises gRPC exceptions directly) |
| Dependency | Included | Optional (`google-apps-meet`) |
