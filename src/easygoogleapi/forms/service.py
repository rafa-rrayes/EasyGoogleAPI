"""Google Forms API wrapper."""

from typing import Any

from .._base import BaseService
from .._pagination import PageIterator
from .models import BatchUpdateResponse, Form, FormResponse, FormResponseList


class FormsService(BaseService):
    """Wrapper for Google Forms API operations."""

    def get_form(self, form_id: str) -> Form:
        """Get a form by ID."""
        request = self._resource.forms().get(formId=form_id)
        result = self._execute_request(request)
        return Form.from_api_response(result)

    def list_responses(
        self,
        form_id: str,
        page_size: int = 50,
    ) -> PageIterator[FormResponse]:
        """List form responses with automatic pagination."""
        def fetch_page(page_token: str | None) -> dict[str, Any]:
            kwargs: dict[str, Any] = {"formId": form_id, "pageSize": page_size}
            if page_token:
                kwargs["pageToken"] = page_token
            request = self._resource.forms().responses().list(**kwargs)
            return self._execute_request(request)

        return PageIterator(fetch_page, items_key="responses", model_class=FormResponse)

    def list_responses_page(
        self,
        form_id: str,
        page_size: int = 50,
        page_token: str | None = None,
    ) -> FormResponseList:
        """List a single page of form responses."""
        kwargs: dict[str, Any] = {"formId": form_id, "pageSize": page_size}
        if page_token:
            kwargs["pageToken"] = page_token
        request = self._resource.forms().responses().list(**kwargs)
        result = self._execute_request(request)
        return FormResponseList.from_api_response(result)

    def get_response(
        self, form_id: str, response_id: str
    ) -> FormResponse:
        """Get a specific form response."""
        request = self._resource.forms().responses().get(
            formId=form_id, responseId=response_id
        )
        result = self._execute_request(request)
        return FormResponse.from_api_response(result)

    def create_form(self, title: str) -> Form:
        """Create a new form."""
        body = {"info": {"title": title}}
        request = self._resource.forms().create(body=body)
        result = self._execute_request(request)
        return Form.from_api_response(result)

    def batch_update(
        self, form_id: str, requests: list[dict[str, Any]]
    ) -> BatchUpdateResponse:
        """Apply batch updates to a form."""
        body = {"requests": requests}
        request = self._resource.forms().batchUpdate(
            formId=form_id, body=body
        )
        result = self._execute_request(request)
        return BatchUpdateResponse.from_api_response(result)

    # ------------------------------------------------------------------
    # Questions / Form info
    # ------------------------------------------------------------------

    def add_question(
        self,
        form_id: str,
        title: str,
        question_type: str = "SHORT_ANSWER",
        required: bool = False,
        index: int | None = None,
    ) -> BatchUpdateResponse:
        """Add a question to a form.

        ``question_type`` should be one of the Forms API question types,
        e.g. ``"SHORT_ANSWER"``, ``"PARAGRAPH"``, ``"MULTIPLE_CHOICE"``,
        ``"CHECKBOX"``, ``"DROP_DOWN"``, ``"SCALE"``, etc.
        """
        question_item: dict[str, Any] = {
            "required": required,
            question_type.lower(): {},
        }

        item: dict[str, Any] = {
            "title": title,
            "questionItem": {"question": question_item},
        }

        create_request: dict[str, Any] = {
            "createItem": {
                "item": item,
                "location": {"index": index if index is not None else 0},
            }
        }
        return self.batch_update(form_id, [create_request])

    def delete_question(
        self, form_id: str, question_index: int
    ) -> BatchUpdateResponse:
        """Delete a question (item) from a form by its index."""
        return self.batch_update(
            form_id,
            [{"deleteItem": {"location": {"index": question_index}}}],
        )

    def update_form_info(
        self,
        form_id: str,
        title: str | None = None,
        description: str | None = None,
    ) -> BatchUpdateResponse:
        """Update the form's title and/or description."""
        info: dict[str, Any] = {}
        update_mask_parts: list[str] = []

        if title is not None:
            info["title"] = title
            update_mask_parts.append("title")
        if description is not None:
            info["description"] = description
            update_mask_parts.append("description")

        return self.batch_update(
            form_id,
            [
                {
                    "updateFormInfo": {
                        "info": info,
                        "updateMask": ",".join(update_mask_parts),
                    }
                }
            ],
        )
