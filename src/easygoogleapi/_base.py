"""Base class for service wrappers."""

from abc import ABC
from typing import Any

from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError

from ._exceptions import APIError


class BaseService(ABC):
    """Base class for all Google API service wrappers.

    Provides common functionality and access to the underlying
    Google API resource for advanced usage.
    """

    def __init__(self, resource: Resource):
        """Initialize the service wrapper.

        Args:
            resource: The Google API resource from googleapiclient.discovery.build()
        """
        self._resource = resource

    @property
    def raw(self) -> Resource:
        """Access the underlying Google API resource.

        Use this for operations not yet wrapped by EasyGoogleAPI.

        Returns:
            The raw Google API resource object.
        """
        return self._resource

    def _execute_request(self, request: Any) -> Any:
        """Execute an API request with error handling.

        Args:
            request: The API request to execute.

        Returns:
            The API response.

        Raises:
            APIError: If the request fails.
        """
        try:
            return request.execute()
        except HttpError as e:
            raise APIError(
                f"API request failed: {e.reason}",
                original_error=e,
            )
