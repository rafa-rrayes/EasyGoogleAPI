"""Middleware system for request lifecycle hooks."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable


@dataclass
class RequestContext:
    """Context passed to before-request hooks."""

    service_name: str
    method_name: str
    attempt: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ResponseContext:
    """Context passed to after-request hooks."""

    request: RequestContext
    duration_ms: float
    status_code: int | None = None
    error: Exception | None = None
    retried: bool = False


BeforeRequestHook = Callable[[RequestContext], None]
AfterRequestHook = Callable[[ResponseContext], None]


class MiddlewareChain:
    """Chain of before/after request hooks.

    Usage::

        middleware = MiddlewareChain()

        @middleware.before_request
        def log_request(ctx):
            print(f"[{ctx.correlation_id}] {ctx.service_name}.{ctx.method_name}")

        @middleware.after_request
        def log_response(ctx):
            print(f"[{ctx.request.correlation_id}] {ctx.duration_ms:.1f}ms")

        google = GoogleService(
            credentials_path="creds.json",
            services=["drive"],
            middleware=middleware,
        )
    """

    def __init__(self) -> None:
        self._before: list[BeforeRequestHook] = []
        self._after: list[AfterRequestHook] = []

    def before_request(self, hook: BeforeRequestHook) -> BeforeRequestHook:
        """Register a before-request hook. Can be used as a decorator."""
        self._before.append(hook)
        return hook

    def after_request(self, hook: AfterRequestHook) -> AfterRequestHook:
        """Register an after-request hook. Can be used as a decorator."""
        self._after.append(hook)
        return hook

    def fire_before(self, ctx: RequestContext) -> None:
        """Fire all before-request hooks."""
        for hook in self._before:
            try:
                hook(ctx)
            except Exception:
                pass  # Middleware errors must not break requests

    def fire_after(self, ctx: ResponseContext) -> None:
        """Fire all after-request hooks."""
        for hook in self._after:
            try:
                hook(ctx)
            except Exception:
                pass
