"""Service configuration registry."""

from dataclasses import dataclass, field
from typing import Any

from ._types import ServiceName


@dataclass(frozen=True)
class ServiceConfig:
    """Configuration for a Google API service."""

    name: ServiceName
    api_name: str
    api_version: str
    scopes: tuple[str, ...]
    build_kwargs: dict[str, Any] = field(default_factory=dict)


SERVICE_REGISTRY: dict[ServiceName, ServiceConfig] = {
    "calendar": ServiceConfig(
        name="calendar",
        api_name="calendar",
        api_version="v3",
        scopes=("https://www.googleapis.com/auth/calendar",),
    ),
    "drive": ServiceConfig(
        name="drive",
        api_name="drive",
        api_version="v3",
        scopes=("https://www.googleapis.com/auth/drive",),
    ),
    "meet": ServiceConfig(
        name="meet",
        api_name="meet",
        api_version="v2",
        scopes=("https://www.googleapis.com/auth/meetings.space.created",),
    ),
    "gmail": ServiceConfig(
        name="gmail",
        api_name="gmail",
        api_version="v1",
        scopes=("https://www.googleapis.com/auth/gmail.modify",),
    ),
    "docs": ServiceConfig(
        name="docs",
        api_name="docs",
        api_version="v1",
        scopes=("https://www.googleapis.com/auth/documents",),
    ),
    "forms": ServiceConfig(
        name="forms",
        api_name="forms",
        api_version="v1",
        scopes=("https://www.googleapis.com/auth/forms",),
        build_kwargs={"static_discovery": False},
    ),
    "sheets": ServiceConfig(
        name="sheets",
        api_name="sheets",
        api_version="v4",
        scopes=("https://www.googleapis.com/auth/spreadsheets",),
    ),
}


def get_scopes_for_services(services: list[ServiceName]) -> list[str]:
    """Get combined scopes for the specified services."""
    scopes: set[str] = set()
    for service_name in services:
        config = SERVICE_REGISTRY[service_name]
        scopes.update(config.scopes)
    return list(scopes)
