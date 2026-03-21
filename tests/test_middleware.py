"""Tests for MiddlewareChain, RequestContext, ResponseContext."""

import uuid

from easygoogleapi._middleware import (
    MiddlewareChain,
    RequestContext,
    ResponseContext,
)


class TestRequestContext:
    """Tests for RequestContext dataclass."""

    def test_default_fields(self):
        """Test that RequestContext has sensible defaults."""
        ctx = RequestContext(
            service_name="DriveService",
            method_name="list_files",
            attempt=0,
        )
        assert ctx.service_name == "DriveService"
        assert ctx.method_name == "list_files"
        assert ctx.attempt == 0
        assert ctx.timestamp is not None
        assert isinstance(ctx.correlation_id, str)
        assert len(ctx.correlation_id) > 0
        assert ctx.extra == {}

    def test_correlation_id_is_uuid_format(self):
        """Test that auto-generated correlation_id is valid UUID."""
        ctx = RequestContext(
            service_name="Test", method_name="test", attempt=0,
        )
        # Should not raise
        parsed = uuid.UUID(ctx.correlation_id)
        assert str(parsed) == ctx.correlation_id

    def test_extra_dict(self):
        """Test that extra dict can hold arbitrary data."""
        ctx = RequestContext(
            service_name="Test", method_name="test", attempt=0,
            extra={"query": "test", "page_size": 100},
        )
        assert ctx.extra["query"] == "test"
        assert ctx.extra["page_size"] == 100


class TestResponseContext:
    """Tests for ResponseContext dataclass."""

    def test_success_response(self):
        """Test ResponseContext for a successful response."""
        req = RequestContext(service_name="Drive", method_name="get_file", attempt=0)
        resp = ResponseContext(
            request=req, duration_ms=45.2, status_code=200,
        )
        assert resp.request is req
        assert resp.duration_ms == 45.2
        assert resp.status_code == 200
        assert resp.error is None
        assert resp.retried is False

    def test_error_response(self):
        """Test ResponseContext for an error response."""
        req = RequestContext(service_name="Drive", method_name="get_file", attempt=1)
        err = Exception("test error")
        resp = ResponseContext(
            request=req, duration_ms=100.0, status_code=500,
            error=err, retried=True,
        )
        assert resp.error is err
        assert resp.retried is True


class TestMiddlewareChain:
    """Tests for MiddlewareChain."""

    def test_before_hook_fires(self):
        """Test that before_request hooks fire correctly."""
        chain = MiddlewareChain()
        captured = []

        @chain.before_request
        def on_before(ctx):
            captured.append(ctx)

        ctx = RequestContext(service_name="Test", method_name="test", attempt=0)
        chain.fire_before(ctx)

        assert len(captured) == 1
        assert captured[0] is ctx

    def test_after_hook_fires(self):
        """Test that after_request hooks fire correctly."""
        chain = MiddlewareChain()
        captured = []

        @chain.after_request
        def on_after(ctx):
            captured.append(ctx)

        req = RequestContext(service_name="Test", method_name="test", attempt=0)
        resp = ResponseContext(request=req, duration_ms=10.0, status_code=200)
        chain.fire_after(resp)

        assert len(captured) == 1
        assert captured[0] is resp

    def test_multiple_hooks_fire_in_order(self):
        """Test that multiple hooks fire in registration order."""
        chain = MiddlewareChain()
        order = []

        @chain.before_request
        def first(ctx):
            order.append("first")

        @chain.before_request
        def second(ctx):
            order.append("second")

        @chain.before_request
        def third(ctx):
            order.append("third")

        ctx = RequestContext(service_name="Test", method_name="test", attempt=0)
        chain.fire_before(ctx)

        assert order == ["first", "second", "third"]

    def test_multiple_after_hooks_fire_in_order(self):
        """Test that multiple after hooks fire in registration order."""
        chain = MiddlewareChain()
        order = []

        @chain.after_request
        def first(ctx):
            order.append("first")

        @chain.after_request
        def second(ctx):
            order.append("second")

        req = RequestContext(service_name="Test", method_name="test", attempt=0)
        resp = ResponseContext(request=req, duration_ms=10.0)
        chain.fire_after(resp)

        assert order == ["first", "second"]

    def test_hook_errors_dont_break_requests(self):
        """Test that errors in hooks do not propagate."""
        chain = MiddlewareChain()
        captured = []

        @chain.before_request
        def broken_hook(ctx):
            raise RuntimeError("Hook exploded!")

        @chain.before_request
        def working_hook(ctx):
            captured.append("ok")

        ctx = RequestContext(service_name="Test", method_name="test", attempt=0)
        # Should not raise
        chain.fire_before(ctx)

        # The second hook should still have fired
        assert captured == ["ok"]

    def test_after_hook_errors_dont_break(self):
        """Test that errors in after hooks do not propagate."""
        chain = MiddlewareChain()
        captured = []

        @chain.after_request
        def broken_hook(ctx):
            raise ValueError("After hook failed!")

        @chain.after_request
        def working_hook(ctx):
            captured.append("ok")

        req = RequestContext(service_name="Test", method_name="test", attempt=0)
        resp = ResponseContext(request=req, duration_ms=10.0)

        # Should not raise
        chain.fire_after(resp)

        assert captured == ["ok"]

    def test_before_hook_returns_original_function(self):
        """Test that before_request decorator returns the original function."""
        chain = MiddlewareChain()

        @chain.before_request
        def my_hook(ctx):
            pass

        # The decorator should return the function unchanged
        assert my_hook is not None
        assert callable(my_hook)

    def test_after_hook_returns_original_function(self):
        """Test that after_request decorator returns the original function."""
        chain = MiddlewareChain()

        @chain.after_request
        def my_hook(ctx):
            pass

        assert my_hook is not None
        assert callable(my_hook)

    def test_no_hooks_registered(self):
        """Test that firing with no hooks registered does nothing."""
        chain = MiddlewareChain()

        ctx = RequestContext(service_name="Test", method_name="test", attempt=0)
        req = RequestContext(service_name="Test", method_name="test", attempt=0)
        resp = ResponseContext(request=req, duration_ms=10.0)

        # Should not raise
        chain.fire_before(ctx)
        chain.fire_after(resp)

    def test_hook_receives_correct_data(self):
        """Test that hooks receive the correct context data."""
        chain = MiddlewareChain()
        before_data = []
        after_data = []

        @chain.before_request
        def on_before(ctx):
            before_data.append({
                "service": ctx.service_name,
                "method": ctx.method_name,
                "attempt": ctx.attempt,
            })

        @chain.after_request
        def on_after(ctx):
            after_data.append({
                "status": ctx.status_code,
                "duration": ctx.duration_ms,
                "retried": ctx.retried,
            })

        req = RequestContext(
            service_name="CalendarService",
            method_name="create_event",
            attempt=2,
        )
        chain.fire_before(req)

        resp = ResponseContext(
            request=req, duration_ms=150.5,
            status_code=200, retried=True,
        )
        chain.fire_after(resp)

        assert before_data == [{
            "service": "CalendarService",
            "method": "create_event",
            "attempt": 2,
        }]
        assert after_data == [{
            "status": 200,
            "duration": 150.5,
            "retried": True,
        }]

    def test_programmatic_registration(self):
        """Test registering hooks programmatically (not as decorator)."""
        chain = MiddlewareChain()
        calls = []

        def hook(ctx):
            calls.append("called")

        chain.before_request(hook)

        ctx = RequestContext(service_name="Test", method_name="test", attempt=0)
        chain.fire_before(ctx)

        assert calls == ["called"]
