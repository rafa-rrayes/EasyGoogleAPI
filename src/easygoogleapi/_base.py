"""Base class for service wrappers."""

from __future__ import annotations

import json
import logging
import random
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError

from ._exceptions import (
    APIError,
    BackendError,
    ConflictError,
    InvalidRequestError,
    MaxRetriesExceededError,
    NotFoundError,
    PermissionDeniedError,
    QuotaExceededError,
    RateLimitError,
    ServerError,
)

if TYPE_CHECKING:
    from ._middleware import MiddlewareChain

logger = logging.getLogger("easygoogleapi")


@dataclass
class RetryConfig:
    """Configuration for retry behavior.

    Attributes:
        max_retries: Maximum number of retry attempts (default: 3).
        base_delay: Base delay in seconds for exponential backoff (default: 1.0).
        max_delay: Maximum delay in seconds between retries (default: 60.0).
        exponential_base: Base for exponential backoff calculation (default: 2.0).
        jitter: Whether to add random jitter to delay (default: True).
    """

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True


class BaseService:
    """Base class for all Google API service wrappers.

    Provides retry logic, error mapping, middleware integration,
    and access to the underlying Google API resource.
    """

    def __init__(
        self,
        resource: Resource,
        retry_config: RetryConfig | None = None,
        middleware: MiddlewareChain | None = None,
    ):
        self._resource = resource
        self._retry_config = retry_config or RetryConfig()
        self._middleware = middleware

    @property
    def raw(self) -> Resource:
        """Access the underlying Google API resource."""
        return self._resource

    def _should_retry(self, error: HttpError, attempt: int) -> bool:
        """Determine if the request should be retried."""
        if attempt >= self._retry_config.max_retries:
            return False
        status = error.resp.status
        return bool(status == 429 or status >= 500)

    def _calculate_backoff(self, attempt: int, error: HttpError | None = None) -> float:
        """Calculate backoff delay with exponential backoff and jitter."""
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

    def _wrap_http_error(self, error: HttpError) -> APIError:
        """Convert HttpError to appropriate EasyGoogleAPI exception."""
        status = error.resp.status
        reason = error.reason

        request_id = None
        error_details = None

        try:
            error_content = json.loads(error.content.decode("utf-8"))
            error_details = error_content.get("error", {})
            request_id = error_details.get("requestId")
        except Exception:
            pass

        error_reason = error_details.get("code") if error_details else None
        error_reason_str = error_details.get("reason", "") if error_details else ""

        if status == 400:
            return InvalidRequestError(
                reason, status_code=status, reason=error_reason,
                request_id=request_id, original_error=error,
            )
        elif status == 403:
            return PermissionDeniedError(
                reason, status_code=status, request_id=request_id,
                original_error=error,
            )
        elif status == 404:
            return NotFoundError(
                reason, status_code=status, request_id=request_id,
                original_error=error,
            )
        elif status == 409:
            return ConflictError(
                reason, status_code=status, request_id=request_id,
                original_error=error,
            )
        elif status == 429:
            if "quota" in error_reason_str.lower():
                return QuotaExceededError(
                    reason, status_code=status, request_id=request_id,
                    original_error=error,
                )
            retry_after = error.resp.get("retry-after")
            try:
                retry_after_int = int(retry_after) if retry_after else None
            except (ValueError, TypeError):
                retry_after_int = None
            return RateLimitError(
                reason, retry_after=retry_after_int, status_code=status,
                request_id=request_id, original_error=error,
            )
        elif status == 503:
            return BackendError(
                reason, status_code=status, request_id=request_id,
                original_error=error,
            )
        elif status >= 500:
            return ServerError(
                reason, status_code=status, request_id=request_id,
                original_error=error,
            )
        else:
            return APIError(
                f"API request failed: {reason}", status_code=status,
                request_id=request_id, original_error=error,
            )

    def _execute_request(
        self, request: Any, *, service_name: str = "", method_name: str = ""
    ) -> Any:
        """Execute an API request with retry, error handling, and middleware."""
        from ._middleware import RequestContext, ResponseContext

        correlation_id = ""
        if self._middleware:
            import uuid
            correlation_id = str(uuid.uuid4())

        last_error = None

        for attempt in range(self._retry_config.max_retries + 1):
            # Fire before-request middleware
            req_ctx = None
            if self._middleware:
                req_ctx = RequestContext(
                    service_name=service_name or self.__class__.__name__,
                    method_name=method_name,
                    attempt=attempt,
                    correlation_id=correlation_id,
                )
                self._middleware.fire_before(req_ctx)

            start_time = time.monotonic()

            try:
                logger.debug(
                    f"[{correlation_id[:8]}] API request attempt "
                    f"{attempt + 1}/{self._retry_config.max_retries + 1}"
                )
                result = request.execute()
                duration_ms = (time.monotonic() - start_time) * 1000

                # Fire after-request middleware
                if self._middleware and req_ctx:
                    self._middleware.fire_after(ResponseContext(
                        request=req_ctx, duration_ms=duration_ms,
                        status_code=200, retried=attempt > 0,
                    ))

                if attempt > 0:
                    logger.info(
                        f"[{correlation_id[:8]}] Succeeded after {attempt + 1} attempts"
                    )

                return result

            except HttpError as e:
                duration_ms = (time.monotonic() - start_time) * 1000
                last_error = e
                wrapped_error = self._wrap_http_error(e)

                # Fire after-request middleware
                if self._middleware and req_ctx:
                    self._middleware.fire_after(ResponseContext(
                        request=req_ctx, duration_ms=duration_ms,
                        status_code=e.resp.status, error=wrapped_error,
                        retried=attempt > 0,
                    ))

                if not self._should_retry(e, attempt):
                    logger.error(
                        f"[{correlation_id[:8]}] Non-retryable error: {e.reason}",
                        extra={"status": e.resp.status},
                    )
                    raise wrapped_error from e

                delay = self._calculate_backoff(attempt, e)
                logger.warning(
                    f"[{correlation_id[:8]}] Retryable error: {e.reason}. "
                    f"Retrying in {delay:.2f}s",
                    extra={"status": e.resp.status, "delay": delay},
                )
                time.sleep(delay)

        logger.error(
            f"[{correlation_id[:8]}] Failed after "
            f"{self._retry_config.max_retries + 1} attempts"
        )
        raise MaxRetriesExceededError(
            f"Request failed after {self._retry_config.max_retries + 1} attempts",
            attempts=self._retry_config.max_retries + 1,
            last_error=last_error,
        )
