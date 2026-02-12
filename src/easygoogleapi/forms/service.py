"""Google Forms API wrapper."""

from typing import Any

from .._base import BaseService


class FormsService(BaseService):
    """Wrapper for Google Forms API operations."""

    def get_form(self, form_id: str) -> dict[str, Any]:
        """Get a form by ID."""
        request = self._resource.forms().get(formId=form_id)
        return self._execute_request(request)

    def list_responses(
        self,
        form_id: str,
        page_size: int = 50,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        """List form responses with pagination.

        Returns a dict with ``responses`` and ``nextPageToken`` keys.
        """
        kwargs: dict[str, Any] = {"formId": form_id, "pageSize": page_size}
        if page_token:
            kwargs["pageToken"] = page_token

        request = self._resource.forms().responses().list(**kwargs)
        result = self._execute_request(request)
        return {
            "responses": result.get("responses", []),
            "nextPageToken": result.get("nextPageToken"),
        }

    def get_response(
        self, form_id: str, response_id: str
    ) -> dict[str, Any]:
        """Get a specific form response."""
        request = self._resource.forms().responses().get(
            formId=form_id, responseId=response_id
        )
        return self._execute_request(request)

    def create_form(self, title: str) -> dict[str, Any]:
        """Create a new form."""
        body = {"info": {"title": title}}
        request = self._resource.forms().create(body=body)
        return self._execute_request(request)

    def batch_update(
        self, form_id: str, requests: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Apply batch updates to a form."""
        body = {"requests": requests}
        request = self._resource.forms().batchUpdate(
            formId=form_id, body=body
        )
        return self._execute_request(request)
