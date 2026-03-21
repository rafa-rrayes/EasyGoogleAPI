"""Google Forms API wrapper."""

from typing import Any

from .._base import BaseService
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
        page_token: str | None = None,
    ) -> FormResponseList:
        """List form responses with pagination."""
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
