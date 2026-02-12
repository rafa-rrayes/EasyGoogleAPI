# Google Calendar

`CalendarService` wraps the Google Calendar API v3. It inherits from `BaseService`, providing automatic retry, error handling, and `.raw` access.

```python
google = GoogleService(credentials_path="creds.json", services=["calendar"])
cal = google.calendar
```

## Methods

### list_calendars

```python
def list_calendars(self) -> list[dict[str, Any]]
```

List all calendars the user has access to.

```python
calendars = google.calendar.list_calendars()
for cal in calendars:
    print(cal["summary"])
```

### get_calendar

```python
def get_calendar(self, calendar_id: str = "primary") -> dict[str, Any]
```

Get details of a specific calendar. Defaults to `"primary"`.

```python
primary = google.calendar.get_calendar()
custom = google.calendar.get_calendar("calendar_id_here")
```

### create_calendar

```python
def create_calendar(
    self,
    summary: str,
    description: str | None = None,
    timezone: str | None = None,
) -> dict[str, Any]
```

Create a new secondary calendar.

- `summary`: Calendar title.
- `description`: Optional calendar description.
- `timezone`: IANA timezone (e.g. `"America/New_York"`). Optional.

```python
cal = google.calendar.create_calendar(
    summary="Team Events",
    description="Shared team calendar",
    timezone="America/New_York",
)
print(cal["id"])
```

### delete_calendar

```python
def delete_calendar(self, calendar_id: str) -> None
```

Delete a secondary calendar.

```python
google.calendar.delete_calendar("calendar_id_here")
```

### add_calendar_to_list

```python
def add_calendar_to_list(
    self,
    calendar_id: str,
    color_id: str | None = None,
    hidden: bool = False,
) -> dict[str, Any]
```

Add an existing calendar to the user's calendar list (makes it visible in their UI).

- `calendar_id`: ID of the calendar to add.
- `color_id`: Optional color ID (1-24).
- `hidden`: If `True`, the calendar is hidden in the UI.

```python
google.calendar.add_calendar_to_list("calendar_id_here", color_id="5")
```

### list_events

```python
def list_events(
    self,
    calendar_id: str = "primary",
    time_min: datetime | None = None,
    time_max: datetime | None = None,
    max_results: int = 10,
    single_events: bool = True,
    order_by: str = "startTime",
) -> list[dict[str, Any]]
```

List events from a calendar. If `time_min` is `None`, it defaults to `datetime.now(UTC)`.

```python
from datetime import datetime, timedelta, UTC

events = google.calendar.list_events(max_results=25)
for event in events:
    print(event["summary"], event["start"])

# Events in a date range
events = google.calendar.list_events(
    time_min=datetime.now(UTC),
    time_max=datetime.now(UTC) + timedelta(days=7),
    max_results=50,
)
```

### get_event

```python
def get_event(
    self,
    event_id: str,
    calendar_id: str = "primary",
) -> dict[str, Any]
```

Get a single event by ID.

```python
event = google.calendar.get_event("event_id_here")
```

### create_event

```python
def create_event(
    self,
    summary: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    calendar_id: str = "primary",
    description: str | None = None,
    location: str | None = None,
    attendees: list[str] | None = None,
    timezone: str = "UTC",
    body: dict[str, Any] | None = None,
) -> dict[str, Any]
```

Create a new calendar event. Use the convenience parameters for simple events, or pass a raw `body` dict for full control over the event resource.

When `body` is provided, the convenience parameters are merged on top of it (so you can use `body` as a base and override individual fields).

```python
from datetime import datetime, timedelta, UTC

# Simple event
start = datetime.now(UTC) + timedelta(days=1)
end = start + timedelta(hours=1)

event = google.calendar.create_event(
    summary="Team Meeting",
    start=start,
    end=end,
    description="Weekly sync",
    attendees=["alice@example.com", "bob@example.com"],
)

# Full control with body
event = google.calendar.create_event(body={
    "summary": "Conference",
    "start": {"dateTime": "2025-03-01T09:00:00", "timeZone": "America/New_York"},
    "end": {"dateTime": "2025-03-01T17:00:00", "timeZone": "America/New_York"},
    "recurrence": ["RRULE:FREQ=WEEKLY;COUNT=10"],
    "reminders": {"useDefault": False, "overrides": [{"method": "popup", "minutes": 30}]},
})
```

### delete_event

```python
def delete_event(self, event_id: str, calendar_id: str = "primary") -> None
```

Delete a calendar event.

```python
google.calendar.delete_event("event_id_here")
```

### update_event

```python
def update_event(
    self,
    event_id: str,
    calendar_id: str = "primary",
    body: dict[str, Any] | None = None,
    **updates: Any,
) -> dict[str, Any]
```

Update an existing calendar event. Pass a raw `body` dict to replace the entire event resource, or use keyword arguments to patch individual top-level fields.

When `body` is `None`, the current event is fetched first, then `**updates` are merged into it before sending the update.

```python
# Patch individual fields
google.calendar.update_event("event_id", summary="New Title")

# Replace with full body
google.calendar.update_event("event_id", body={
    "summary": "Updated Event",
    "start": {"dateTime": "2025-03-01T10:00:00Z"},
    "end": {"dateTime": "2025-03-01T11:00:00Z"},
})
```
