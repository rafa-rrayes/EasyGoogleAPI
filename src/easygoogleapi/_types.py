"""Type definitions for EasyGoogleAPI."""

from enum import Enum
from typing import Literal

ServiceName = Literal[
    "calendar", "docs", "drive", "forms", "gmail", "meet", "sheets"
]


class CredentialType(Enum):
    OAUTH = "oauth"
    SERVICE_ACCOUNT = "service_account"
