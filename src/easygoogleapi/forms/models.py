"""Typed response models for Google Forms API."""

from dataclasses import dataclass, field
from typing import Any

from .._models import GoogleModel


@dataclass
class Form(GoogleModel):
    """A Google Form."""

    form_id: str = ""
    info: dict[str, Any] = field(default_factory=dict)
    items: list[dict[str, Any]] = field(default_factory=list)
    responder_uri: str | None = None
    revision_id: str | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "Form":
        return cls(
            form_id=data.get("formId", ""),
            info=data.get("info", {}),
            items=data.get("items", []),
            responder_uri=data.get("responderUri"),
            revision_id=data.get("revisionId"),
        )


@dataclass
class FormResponse(GoogleModel):
    """A response to a Google Form."""

    response_id: str = ""
    answers: dict[str, Any] = field(default_factory=dict)
    create_time: str | None = None
    last_submitted_time: str | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "FormResponse":
        return cls(
            response_id=data.get("responseId", ""),
            answers=data.get("answers", {}),
            create_time=data.get("createTime"),
            last_submitted_time=data.get("lastSubmittedTime"),
        )


@dataclass
class FormResponseList(GoogleModel):
    """A page of form response results."""

    responses: list[FormResponse] = field(default_factory=list)
    next_page_token: str | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "FormResponseList":
        return cls(
            responses=[
                FormResponse.from_api_response(r)
                for r in data.get("responses", [])
            ],
            next_page_token=data.get("nextPageToken"),
        )


@dataclass
class BatchUpdateResponse(GoogleModel):
    """Result of a Forms batch update."""

    form: Form | None = None
    replies: list[dict[str, Any]] = field(default_factory=list)
    write_control: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "BatchUpdateResponse":
        form_data = data.get("form")
        return cls(
            form=Form.from_api_response(form_data) if form_data else None,
            replies=data.get("replies", []),
            write_control=data.get("writeControl", {}),
        )
