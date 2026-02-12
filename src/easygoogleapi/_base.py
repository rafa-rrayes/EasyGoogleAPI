"""Base class for service wrappers."""

import logging
import random
import time
from abc import ABC
from dataclasses import dataclass
from typing import Any

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


class BaseService(ABC):
    """Base class for all Google API service wrappers.

    Provides common functionality and access to the underlying
    Google API resource for advanced usage.
    """

    def __init__(
        self,
        resource: Resource,
        retry_config: RetryConfig | None = None,
    ):
        """Initialize the service wrapper.

        Args:
            resource: The Google API resource from googleapiclient.discovery.build()
            retry_config: Configuration for retry behavior. Uses defaults if None.
        """
        self._resource = resource
        self._retry_config = retry_config or RetryConfig()

    @property
    def raw(self) -> Resource:
        """Access the underlying Google API resource.

        Use this for operations not yet wrapped by EasyGoogleAPI.

        Returns:
            The raw Google API resource object.
        """
        return self._resource

    def _should_retry(self, error: HttpError, attempt: int) -> bool:
        """Determine if the request should be retried.
        
        Args:
            error: The HttpError from the API.
            attempt: The current attempt number (0-indexed).
            
        Returns:
            True if the request should be retried, False otherwise.
        """
        if attempt >= self._retry_config.max_retries:
            return False
        
        status = error.resp.status
        
        # Always retry rate limits and server errors
        if status == 429 or status >= 500:
            return True
        
        # Don't retry client errors (4xx except 429)
        return False

    def _calculate_backoff(self, attempt: int, error: HttpError | None = None) -> float:
        """Calculate backoff delay with exponential backoff and jitter.
        
        Args:
            attempt: The current attempt number (0-indexed).
            error: The error that triggered the retry (for Retry-After header).
            
        Returns:
            Delay in seconds before next retry.
        """
        # Check for Retry-After header
        if error and error.resp.status == 429:
            retry_after = error.resp.get("retry-after")
            if retry_after:
                try:
                    return float(retry_after)
                except (ValueError, TypeError):
                    pass
        
        # Exponential backoff
        delay = self._retry_config.base_delay * (
            self._retry_config.exponential_base ** attempt
        )
        
        # Cap at max_delay
        delay = min(delay, self._retry_config.max_delay)
        
        # Add jitter
        if self._retry_config.jitter:
            delay = delay * (0.5 + random.random())
        
        return delay

    def _wrap_http_error(self, error: HttpError) -> APIError:
        """Convert HttpError to appropriate EasyGoogleAPI exception.
        
        Args:
            error: The HttpError from Google API client.
            
        Returns:
            An appropriate subclass of APIError.
        """
        status = error.resp.status
        reason = error.reason
        
        # Try to extract more details from error content
        request_id = None
        error_details = None
        
        try:
            import json
            error_content = json.loads(error.content.decode("utf-8"))
            error_details = error_content.get("error", {})
            request_id = error_details.get("requestId")
        except Exception:
            pass
        
        # Map status codes to specific exceptions
        if status == 400:
            return InvalidRequestError(
                reason,
                status_code=status,
                reason=error_details.get("code") if error_details else None,
                request_id=request_id,
                original_error=error,
            )
        elif status == 403:
            return PermissionDeniedError(
                reason,
                status_code=status,
                request_id=request_id,
                original_error=error,
            )
        elif status == 404:
            return NotFoundError(
                reason,
                status_code=status,
                request_id=request_id,
                original_error=error,
            )
        elif status == 409:
            return ConflictError(
                reason,
                status_code=status,
                request_id=request_id,
                original_error=error,
            )
        elif status == 429:
            # Could be rate limit or quota
            if error_details and "quota" in error_details.get("reason", "").lower():
                return QuotaExceededError(
                    reason,
                    status_code=status,
                    request_id=request_id,
                    original_error=error,
                )
            else:
                retry_after = error.resp.get("retry-after")
                try:
                    retry_after_int = int(retry_after) if retry_after else None
                except (ValueError, TypeError):
                    retry_after_int = None
                
                return RateLimitError(
                    reason,
                    retry_after=retry_after_int,
                    status_code=status,
                    request_id=request_id,
                    original_error=error,
                )
        elif status == 503:
            return BackendError(
                reason,
                status_code=status,
                request_id=request_id,
                original_error=error,
            )
        elif status >= 500:
            return ServerError(
                reason,
                status_code=status,
                request_id=request_id,
                original_error=error,
            )
        else:
            # Generic API error
            return APIError(
                f"API request failed: {reason}",
                status_code=status,
                request_id=request_id,
                original_error=error,
            )

    def _execute_request(self, request: Any) -> Any:
        """Execute an API request with automatic retry and error handling.

        Args:
            request: The API request to execute.

        Returns:
            The API response.

        Raises:
            APIError: If the request fails after all retries.
            MaxRetriesExceededError: If max retries are exceeded.
        """
        last_error = None
        
        for attempt in range(self._retry_config.max_retries + 1):
            try:
                logger.debug(
                    f"Executing API request (attempt {attempt + 1}/{self._retry_config.max_retries + 1})"
                )
                result = request.execute()
                
                if attempt > 0:
                    logger.info(f"Request succeeded after {attempt + 1} attempts")
                
                return result
                
            except HttpError as e:
                last_error = e
                
                # Convert to our exception type
                wrapped_error = self._wrap_http_error(e)
                
                # Check if we should retry
                if not self._should_retry(e, attempt):
                    logger.error(
                        f"Request failed with non-retryable error: {e.reason}",
                        extra={"status": e.resp.status, "attempt": attempt + 1},
                    )
                    raise wrapped_error
                
                # Calculate backoff
                delay = self._calculate_backoff(attempt, e)
                
                logger.warning(
                    f"Request failed with retryable error: {e.reason}. "
                    f"Retrying in {delay:.2f}s (attempt {attempt + 1}/{self._retry_config.max_retries + 1})",
                    extra={"status": e.resp.status, "delay": delay},
                )
                
                time.sleep(delay)
        
        # If we get here, we exceeded max retries
        logger.error(
            f"Request failed after {self._retry_config.max_retries + 1} attempts"
        )
        raise MaxRetriesExceededError(
            f"Request failed after {self._retry_config.max_retries + 1} attempts",
            attempts=self._retry_config.max_retries + 1,
            last_error=last_error,
        )
