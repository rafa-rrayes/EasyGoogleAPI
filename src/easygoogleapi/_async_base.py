"""Async base class for service wrappers."""

import asyncio
import logging
import random
from typing import Any

from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError

from ._base import RetryConfig
from ._exceptions import MaxRetriesExceededError

logger = logging.getLogger("easygoogleapi")


class AsyncBaseService:
    """Async base class for Google API service wrappers.

    Uses ``asyncio.to_thread()`` to run synchronous Google API calls
    without blocking the event loop, combined with ``asyncio.sleep()``
    for non-blocking backoff.
    """

    def __init__(
        self,
        resource: Resource,
        retry_config: RetryConfig | None = None,
    ):
        self._resource = resource
        self._retry_config = retry_config or RetryConfig()

    @property
    def raw(self) -> Resource:
        """Access the underlying Google API resource."""
        return self._resource

    def _should_retry(self, error: HttpError, attempt: int) -> bool:
        if attempt >= self._retry_config.max_retries:
            return False
        status = error.resp.status
        return status == 429 or status >= 500

    def _calculate_backoff(self, attempt: int, error: HttpError | None = None) -> float:
        if error and error.resp.status == 429:
            retry_after = error.resp.get("retry-after")
            if retry_after:
                try:
                    return float(retry_after)
                except (ValueError, TypeError):
                    pass
        delay = self._retry_config.base_delay * (
            self._retry_config.exponential_base ** attempt
        )
        delay = min(delay, self._retry_config.max_delay)
        if self._retry_config.jitter:
            delay = delay * (0.5 + random.random())
        return delay

    def _wrap_http_error(self, error: HttpError) -> Any:
        # Reuse the sync version's error mapping
        from ._base import BaseService
        # Create a temporary instance just to call the method
        return BaseService._wrap_http_error(self, error)  # type: ignore[arg-type]

    async def _execute_request(self, request: Any) -> Any:
        """Execute an API request asynchronously with retry and backoff."""
        last_error = None

        for attempt in range(self._retry_config.max_retries + 1):
            try:
                result = await asyncio.to_thread(request.execute)
                return result
            except HttpError as e:
                last_error = e
                wrapped_error = self._wrap_http_error(e)

                if not self._should_retry(e, attempt):
                    raise wrapped_error

                delay = self._calculate_backoff(attempt, e)
                logger.warning(
                    f"Request failed: {e.reason}. Retrying in {delay:.2f}s "
                    f"(attempt {attempt + 1}/{self._retry_config.max_retries + 1})",
                )
                await asyncio.sleep(delay)

        raise MaxRetriesExceededError(
            f"Request failed after {self._retry_config.max_retries + 1} attempts",
            attempts=self._retry_config.max_retries + 1,
            last_error=last_error,
        )
