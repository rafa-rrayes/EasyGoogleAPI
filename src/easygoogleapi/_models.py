"""Base model class for typed API responses."""

from dataclasses import dataclass, fields
from typing import Any


@dataclass
class GoogleModel:
    """Base for all response models.

    Provides ``to_dict()``, ``from_api_response()``, and readable ``__repr__``.
    Users access fields as attributes (e.g. ``file.name``), not via dict access.
    Call ``.to_dict()`` when a plain dict is needed for serialization.
    """

    def to_dict(self) -> dict[str, Any]:
        """Convert to plain dict for serialization or interop."""
        result: dict[str, Any] = {}
        for f in fields(self):
            val = getattr(self, f.name)
            if isinstance(val, GoogleModel):
                result[f.name] = val.to_dict()
            elif isinstance(val, list):
                result[f.name] = [
                    item.to_dict() if isinstance(item, GoogleModel) else item
                    for item in val
                ]
            else:
                result[f.name] = val
        return result

    def __repr__(self) -> str:
        """Readable repr with class name and key fields."""
        all_fields = fields(self)
        field_strs = ", ".join(
            f"{f.name}={getattr(self, f.name)!r}" for f in all_fields[:3]
        )
        if len(all_fields) > 3:
            field_strs += ", ..."
        return f"{self.__class__.__name__}({field_strs})"

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "GoogleModel":
        """Override in subclasses to map API response keys to model fields."""
        raise NotImplementedError
