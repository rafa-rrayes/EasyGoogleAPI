"""Tests for BaseService — retry, backoff, error mapping (most critical gap)."""

import json
import time
from unittest.mock import MagicMock, patch

import pytest

from easygoogleapi._base import BaseService, RetryConfig
from easygoogleapi._exceptions import (
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


# ---------------------------------------------------------------------------
# Helpers for building mock HttpError objects
# ---------------------------------------------------------------------------

def _make_http_error(
    status: int,
    reason: str = "Error",
    error_content: dict | None = None,
    headers: dict | None = None,
):
    """Build a googleapiclient.errors.HttpError-like object.

    This avoids importing the real HttpError class which requires
    httplib2.Response. We build a mock that behaves identically.
    """
    from googleapiclient.errors import HttpError

    resp = MagicMock()
    resp.status = status
    resp.get = lambda key, default=None: (headers or {}).get(key, default)

    if error_content is not None:
        content = json.dumps(error_content).encode("utf-8")
    else:
        content = b"{}"

    error = HttpError(resp=resp, content=content)
    error.reason = reason
    return error


class _ConcreteService(BaseService):
    """Concrete subclass of BaseService for testing."""
    pass


@pytest.fixture
def service():
    """Create a ConcreteService with a mocked resource and default retry config."""
    resource = MagicMock()
    return _ConcreteService(resource, retry_config=RetryConfig(max_retries=3, base_delay=0.01))


@pytest.fixture
def no_retry_service():
    """Create a ConcreteService with max_retries=0 (no retries)."""
    resource = MagicMock()
    return _ConcreteService(resource, retry_config=RetryConfig(max_retries=0))


# ===========================================================================
# _execute_request tests
# ===========================================================================


class TestExecuteRequestSuccess:
    """Tests for successful request execution."""

    def test_succeeds_first_attempt(self, service):
        """Test that a successful request returns the result immediately."""
        request = MagicMock()
        request.execute.return_value = {"id": "123", "name": "test"}

        result = service._execute_request(request)

        assert result == {"id": "123", "name": "test"}
        assert request.execute.call_count == 1

    def test_succeeds_with_none_result(self, service):
        """Test that None result is returned correctly."""
        request = MagicMock()
        request.execute.return_value = None

        result = service._execute_request(request)

        assert result is None


class TestExecuteRequestRetry:
    """Tests for retry behavior on transient errors."""

    @patch("time.sleep")
    def test_retries_on_429_and_succeeds(self, mock_sleep, service):
        """Test that 429 triggers retry and succeeds on second attempt."""
        error_429 = _make_http_error(429, "Rate limit exceeded")

        request = MagicMock()
        request.execute.side_effect = [error_429, {"id": "123"}]

        result = service._execute_request(request)

        assert result == {"id": "123"}
        assert request.execute.call_count == 2
        assert mock_sleep.call_count == 1

    @patch("time.sleep")
    def test_retries_on_500_and_succeeds(self, mock_sleep, service):
        """Test that 500 triggers retry and succeeds on second attempt."""
        error_500 = _make_http_error(500, "Internal Server Error")

        request = MagicMock()
        request.execute.side_effect = [error_500, {"id": "123"}]

        result = service._execute_request(request)

        assert result == {"id": "123"}
        assert request.execute.call_count == 2

    @patch("time.sleep")
    def test_retries_on_503_and_succeeds(self, mock_sleep, service):
        """Test that 503 triggers retry and succeeds."""
        error_503 = _make_http_error(503, "Service Unavailable")

        request = MagicMock()
        request.execute.side_effect = [error_503, {"result": "ok"}]

        result = service._execute_request(request)

        assert result == {"result": "ok"}
        assert request.execute.call_count == 2


class TestExecuteRequestNoRetry:
    """Tests for errors that should NOT be retried."""

    def test_400_raises_immediately(self, service):
        """Test that 400 raises InvalidRequestError without retry."""
        error_400 = _make_http_error(400, "Bad Request")

        request = MagicMock()
        request.execute.side_effect = error_400

        with pytest.raises(InvalidRequestError):
            service._execute_request(request)

        assert request.execute.call_count == 1

    def test_403_raises_immediately(self, service):
        """Test that 403 raises PermissionDeniedError without retry."""
        error_403 = _make_http_error(403, "Forbidden")

        request = MagicMock()
        request.execute.side_effect = error_403

        with pytest.raises(PermissionDeniedError):
            service._execute_request(request)

        assert request.execute.call_count == 1

    def test_404_raises_immediately(self, service):
        """Test that 404 raises NotFoundError without retry."""
        error_404 = _make_http_error(404, "Not Found")

        request = MagicMock()
        request.execute.side_effect = error_404

        with pytest.raises(NotFoundError):
            service._execute_request(request)

        assert request.execute.call_count == 1

    def test_409_raises_immediately(self, service):
        """Test that 409 raises ConflictError without retry."""
        error_409 = _make_http_error(409, "Conflict")

        request = MagicMock()
        request.execute.side_effect = error_409

        with pytest.raises(ConflictError):
            service._execute_request(request)

        assert request.execute.call_count == 1


class TestExecuteRequestMaxRetries:
    """Tests for max retry exhaustion."""

    @patch("time.sleep")
    def test_exceeds_max_retries_raises(self, mock_sleep):
        """Test that exceeding max retries raises the wrapped error on the last attempt."""
        resource = MagicMock()
        svc = _ConcreteService(
            resource, retry_config=RetryConfig(max_retries=2, base_delay=0.01)
        )

        error_500 = _make_http_error(500, "Internal Server Error")
        request = MagicMock()
        request.execute.side_effect = error_500  # Always fails

        from easygoogleapi._exceptions import ServerError
        with pytest.raises(ServerError):
            svc._execute_request(request)

        # 1 initial + 2 retries = 3 total attempts
        assert request.execute.call_count == 3

    @patch("time.sleep")
    def test_max_retries_preserves_error_info(self, mock_sleep):
        """Test that the final error has correct status info."""
        resource = MagicMock()
        svc = _ConcreteService(
            resource, retry_config=RetryConfig(max_retries=1, base_delay=0.01)
        )

        error_500 = _make_http_error(500, "Server Error")
        request = MagicMock()
        request.execute.side_effect = error_500

        from easygoogleapi._exceptions import ServerError
        with pytest.raises(ServerError) as exc_info:
            svc._execute_request(request)

        assert exc_info.value.status_code == 500


# ===========================================================================
# _calculate_backoff tests
# ===========================================================================


class TestCalculateBackoff:
    """Tests for backoff delay calculation."""

    def test_jitter_true_produces_varied_delays(self):
        """Test that jitter=True produces varied delays across calls."""
        resource = MagicMock()
        svc = _ConcreteService(
            resource, retry_config=RetryConfig(jitter=True, base_delay=1.0)
        )

        delays = [svc._calculate_backoff(1) for _ in range(20)]

        # With jitter, not all delays should be identical
        assert len(set(delays)) > 1, "Jitter should produce varied delays"

    def test_jitter_false_produces_deterministic_delays(self):
        """Test that jitter=False produces deterministic delays."""
        resource = MagicMock()
        svc = _ConcreteService(
            resource, retry_config=RetryConfig(jitter=False, base_delay=1.0, exponential_base=2.0)
        )

        delays = [svc._calculate_backoff(1) for _ in range(10)]

        # Without jitter, all delays for the same attempt should be identical
        assert len(set(delays)) == 1, "No jitter should produce deterministic delays"
        assert delays[0] == 2.0  # 1.0 * (2.0 ** 1) = 2.0

    def test_exponential_increase(self):
        """Test that delay increases exponentially with attempt number."""
        resource = MagicMock()
        svc = _ConcreteService(
            resource, retry_config=RetryConfig(jitter=False, base_delay=1.0, exponential_base=2.0)
        )

        d0 = svc._calculate_backoff(0)  # 1.0 * 2^0 = 1.0
        d1 = svc._calculate_backoff(1)  # 1.0 * 2^1 = 2.0
        d2 = svc._calculate_backoff(2)  # 1.0 * 2^2 = 4.0

        assert d0 == 1.0
        assert d1 == 2.0
        assert d2 == 4.0

    def test_respects_max_delay_cap(self):
        """Test that backoff delay is capped at max_delay."""
        resource = MagicMock()
        svc = _ConcreteService(
            resource, retry_config=RetryConfig(
                jitter=False, base_delay=1.0, exponential_base=2.0, max_delay=5.0
            )
        )

        # attempt 10: 1.0 * 2^10 = 1024.0, but should be capped at 5.0
        delay = svc._calculate_backoff(10)
        assert delay == 5.0

    def test_respects_retry_after_header(self):
        """Test that Retry-After header is respected for 429 errors."""
        resource = MagicMock()
        svc = _ConcreteService(resource)

        error_429 = _make_http_error(
            429, "Rate limit", headers={"retry-after": "30"}
        )

        delay = svc._calculate_backoff(0, error=error_429)
        assert delay == 30.0

    def test_retry_after_non_numeric_falls_back(self):
        """Test that non-numeric Retry-After falls back to exponential backoff."""
        resource = MagicMock()
        svc = _ConcreteService(
            resource, retry_config=RetryConfig(jitter=False, base_delay=1.0, exponential_base=2.0)
        )

        error_429 = _make_http_error(
            429, "Rate limit", headers={"retry-after": "not-a-number"}
        )

        delay = svc._calculate_backoff(0, error=error_429)
        assert delay == 1.0  # Falls back to normal exponential: 1.0 * 2^0

    def test_retry_after_not_used_for_non_429(self):
        """Test that Retry-After is not used for non-429 errors."""
        resource = MagicMock()
        svc = _ConcreteService(
            resource, retry_config=RetryConfig(jitter=False, base_delay=1.0, exponential_base=2.0)
        )

        error_500 = _make_http_error(
            500, "Server Error", headers={"retry-after": "99"}
        )

        delay = svc._calculate_backoff(0, error=error_500)
        assert delay == 1.0  # Normal exponential: 1.0 * 2^0


# ===========================================================================
# _wrap_http_error tests
# ===========================================================================


class TestWrapHttpError:
    """Tests for HTTP error to exception mapping."""

    @pytest.fixture
    def svc(self):
        return _ConcreteService(MagicMock())

    def test_maps_400_to_invalid_request_error(self, svc):
        """Test 400 maps to InvalidRequestError."""
        error = _make_http_error(400, "Bad Request")
        result = svc._wrap_http_error(error)
        assert isinstance(result, InvalidRequestError)
        assert result.status_code == 400

    def test_maps_403_to_permission_denied_error(self, svc):
        """Test 403 maps to PermissionDeniedError."""
        error = _make_http_error(403, "Forbidden")
        result = svc._wrap_http_error(error)
        assert isinstance(result, PermissionDeniedError)
        assert result.status_code == 403

    def test_maps_404_to_not_found_error(self, svc):
        """Test 404 maps to NotFoundError."""
        error = _make_http_error(404, "Not Found")
        result = svc._wrap_http_error(error)
        assert isinstance(result, NotFoundError)
        assert result.status_code == 404

    def test_maps_409_to_conflict_error(self, svc):
        """Test 409 maps to ConflictError."""
        error = _make_http_error(409, "Conflict")
        result = svc._wrap_http_error(error)
        assert isinstance(result, ConflictError)
        assert result.status_code == 409

    def test_maps_429_to_rate_limit_error(self, svc):
        """Test 429 maps to RateLimitError."""
        error = _make_http_error(429, "Too Many Requests")
        result = svc._wrap_http_error(error)
        assert isinstance(result, RateLimitError)
        assert result.status_code == 429

    def test_maps_429_with_quota_reason_to_quota_exceeded(self, svc):
        """Test 429 with quota reason maps to QuotaExceededError."""
        error = _make_http_error(
            429, "Quota exceeded",
            error_content={"error": {"reason": "quotaExceeded", "code": 429}},
        )
        result = svc._wrap_http_error(error)
        assert isinstance(result, QuotaExceededError)
        assert result.status_code == 429

    def test_maps_429_without_quota_to_rate_limit(self, svc):
        """Test 429 without quota reason maps to RateLimitError."""
        error = _make_http_error(
            429, "Rate limited",
            error_content={"error": {"reason": "rateLimitExceeded", "code": 429}},
        )
        result = svc._wrap_http_error(error)
        assert isinstance(result, RateLimitError)
        assert not isinstance(result, QuotaExceededError)

    def test_maps_429_retry_after_header(self, svc):
        """Test 429 RateLimitError includes retry_after from header."""
        error = _make_http_error(
            429, "Rate limited",
            headers={"retry-after": "60"},
        )
        result = svc._wrap_http_error(error)
        assert isinstance(result, RateLimitError)
        assert result.retry_after == 60

    def test_maps_503_to_backend_error(self, svc):
        """Test 503 maps to BackendError."""
        error = _make_http_error(503, "Service Unavailable")
        result = svc._wrap_http_error(error)
        assert isinstance(result, BackendError)
        assert result.status_code == 503

    def test_maps_502_to_server_error(self, svc):
        """Test 502 maps to ServerError (generic 5xx)."""
        error = _make_http_error(502, "Bad Gateway")
        result = svc._wrap_http_error(error)
        assert isinstance(result, ServerError)
        assert result.status_code == 502

    def test_maps_500_to_server_error(self, svc):
        """Test 500 maps to ServerError."""
        error = _make_http_error(500, "Internal Server Error")
        result = svc._wrap_http_error(error)
        assert isinstance(result, ServerError)
        assert result.status_code == 500

    def test_maps_unknown_status_to_api_error(self, svc):
        """Test unknown status code maps to generic APIError."""
        error = _make_http_error(418, "I'm a teapot")
        result = svc._wrap_http_error(error)
        assert isinstance(result, APIError)
        assert result.status_code == 418

    def test_handles_unparseable_error_content(self, svc):
        """Test that unparseable error content does not raise (error_details=None)."""
        from googleapiclient.errors import HttpError

        resp = MagicMock()
        resp.status = 500
        resp.get = lambda key, default=None: None

        error = HttpError(resp=resp, content=b"not json at all {{{")
        error.reason = "Internal Server Error"

        result = svc._wrap_http_error(error)
        assert isinstance(result, ServerError)
        assert result.status_code == 500

    def test_preserves_original_error(self, svc):
        """Test that original_error is set on the wrapped exception."""
        error = _make_http_error(404, "Not Found")
        result = svc._wrap_http_error(error)
        assert result.original_error is error

    def test_extracts_request_id(self, svc):
        """Test that requestId from error content is extracted."""
        error = _make_http_error(
            400, "Bad Request",
            error_content={"error": {"requestId": "req-12345", "code": 400}},
        )
        result = svc._wrap_http_error(error)
        assert result.request_id == "req-12345"


# ===========================================================================
# _should_retry tests
# ===========================================================================


class TestShouldRetry:
    """Tests for retry eligibility determination."""

    @pytest.fixture
    def svc(self):
        resource = MagicMock()
        return _ConcreteService(resource, retry_config=RetryConfig(max_retries=3))

    def test_retries_on_429(self, svc):
        """Test that 429 is retryable."""
        error = _make_http_error(429, "Too Many Requests")
        assert svc._should_retry(error, attempt=0) is True

    def test_retries_on_500(self, svc):
        """Test that 500 is retryable."""
        error = _make_http_error(500, "Internal Server Error")
        assert svc._should_retry(error, attempt=0) is True

    def test_retries_on_503(self, svc):
        """Test that 503 is retryable."""
        error = _make_http_error(503, "Service Unavailable")
        assert svc._should_retry(error, attempt=0) is True

    def test_no_retry_on_400(self, svc):
        """Test that 400 is not retryable."""
        error = _make_http_error(400, "Bad Request")
        assert svc._should_retry(error, attempt=0) is False

    def test_no_retry_on_403(self, svc):
        """Test that 403 is not retryable."""
        error = _make_http_error(403, "Forbidden")
        assert svc._should_retry(error, attempt=0) is False

    def test_no_retry_on_404(self, svc):
        """Test that 404 is not retryable."""
        error = _make_http_error(404, "Not Found")
        assert svc._should_retry(error, attempt=0) is False

    def test_no_retry_when_max_attempts_reached(self, svc):
        """Test that retry is refused when max attempts reached."""
        error = _make_http_error(500, "Internal Server Error")
        assert svc._should_retry(error, attempt=3) is False  # max_retries=3


# ===========================================================================
# RetryConfig tests
# ===========================================================================


class TestRetryConfig:
    """Tests for RetryConfig dataclass."""

    def test_defaults(self):
        """Test default values."""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True

    def test_custom_values(self):
        """Test custom values."""
        config = RetryConfig(
            max_retries=5, base_delay=0.5, max_delay=30.0,
            exponential_base=3.0, jitter=False,
        )
        assert config.max_retries == 5
        assert config.base_delay == 0.5
        assert config.max_delay == 30.0
        assert config.exponential_base == 3.0
        assert config.jitter is False


# ===========================================================================
# Middleware integration in _execute_request
# ===========================================================================


class TestExecuteRequestMiddleware:
    """Tests for middleware integration within _execute_request."""

    @patch("time.sleep")
    def test_before_and_after_hooks_fire(self, mock_sleep):
        """Test that middleware hooks fire on successful request."""
        from easygoogleapi._middleware import MiddlewareChain

        middleware = MiddlewareChain()
        before_calls = []
        after_calls = []

        @middleware.before_request
        def on_before(ctx):
            before_calls.append(ctx)

        @middleware.after_request
        def on_after(ctx):
            after_calls.append(ctx)

        resource = MagicMock()
        svc = _ConcreteService(resource, middleware=middleware)

        request = MagicMock()
        request.execute.return_value = {"ok": True}

        svc._execute_request(request, service_name="Drive", method_name="list_files")

        assert len(before_calls) == 1
        assert len(after_calls) == 1
        assert before_calls[0].service_name == "Drive"
        assert before_calls[0].method_name == "list_files"
        assert after_calls[0].status_code == 200

    @patch("time.sleep")
    def test_correlation_id_is_uuid_format(self, mock_sleep):
        """Test that correlation_id assigned by _execute_request is UUID format."""
        import uuid
        from easygoogleapi._middleware import MiddlewareChain

        middleware = MiddlewareChain()
        captured_ids = []

        @middleware.before_request
        def on_before(ctx):
            captured_ids.append(ctx.correlation_id)

        resource = MagicMock()
        svc = _ConcreteService(resource, middleware=middleware)

        request = MagicMock()
        request.execute.return_value = {}

        svc._execute_request(request)

        assert len(captured_ids) == 1
        # Validate it parses as a UUID
        parsed = uuid.UUID(captured_ids[0])
        assert str(parsed) == captured_ids[0]
