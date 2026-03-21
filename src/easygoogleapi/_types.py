"""Type definitions for EasyGoogleAPI."""

from enum import Enum
from typing import Literal

ServiceName = Literal[
    "calendar", "docs", "drive", "forms", "gmail", "meet", "sheets"
]


class CredentialType(Enum):
    OAUTH = "oauth"
    SERVICE_ACCOUNT = "service_account"


SCOPE_PRESETS: dict[str, dict[str, tuple[str, ...]]] = {
    "readonly": {
        "drive": ("https://www.googleapis.com/auth/drive.readonly",),
        "gmail": ("https://www.googleapis.com/auth/gmail.readonly",),
        "calendar": ("https://www.googleapis.com/auth/calendar.readonly",),
        "sheets": ("https://www.googleapis.com/auth/spreadsheets.readonly",),
        "docs": ("https://www.googleapis.com/auth/documents.readonly",),
    },
    "full": {
        "calendar": ("https://www.googleapis.com/auth/calendar",),
        "drive": ("https://www.googleapis.com/auth/drive",),
        "gmail": ("https://www.googleapis.com/auth/gmail.modify",),
        "docs": ("https://www.googleapis.com/auth/documents",),
        "forms": ("https://www.googleapis.com/auth/forms",),
        "sheets": ("https://www.googleapis.com/auth/spreadsheets",),
        "meet": ("https://www.googleapis.com/auth/meetings.space.created",),
    },
}
