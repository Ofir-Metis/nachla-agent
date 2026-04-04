"""FastAPI middleware for authentication, logging, and rate limiting.

All middleware components are production-ready:
- Auth: Bearer token validation with RBAC
- Logging: Request/response logging with timing
- Rate limiting: Per-IP request throttling
- Error handling: Consistent Hebrew error responses
"""

from __future__ import annotations

import logging
import os
import time
from collections import defaultdict
from typing import Any

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from config.security import ENDPOINT_OPERATIONS, check_permission

logger = logging.getLogger(__name__)

# Paths that skip authentication
AUTH_EXEMPT_PATHS: set[str] = {
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
}


class AuthMiddleware(BaseHTTPMiddleware):
    """Bearer token authentication with RBAC role checking.

    Validates the Authorization header and attaches user info to request.state.
    Checks RBAC permissions based on endpoint-to-operation mapping.

    Token format expected: Bearer <token>
    Token validation uses API_AUTH_TOKENS env var (comma-separated token:role pairs).
    Example: API_AUTH_TOKENS=abc123:admin,def456:analyst,ghi789:viewer
    """

    def __init__(self, app: Any) -> None:
        """Initialize auth middleware and load token map from environment."""
        super().__init__(app)
        self._token_map: dict[str, str] = self._load_tokens()

    @staticmethod
    def _load_tokens() -> dict[str, str]:
        """Load token-to-role mapping from API_AUTH_TOKENS env var.

        Returns:
            Dict mapping token string to role string.
        """
        raw = os.getenv("API_AUTH_TOKENS", "")
        if not raw:
            return {}

        token_map: dict[str, str] = {}
        for entry in raw.split(","):
            entry = entry.strip()
            if ":" not in entry:
                continue
            token, role = entry.split(":", 1)
            token_map[token.strip()] = role.strip()
        return token_map

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process request through auth checks.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware/handler in chain.

        Returns:
            Response from downstream handler or 401/403 error.
        """
        # Skip auth for exempt paths
        if request.url.path in AUTH_EXEMPT_PATHS:
            return await call_next(request)

        # Skip auth if no tokens configured (development mode)
        if not self._token_map:
            request.state.user_role = "admin"
            request.state.authenticated = True
            return await call_next(request)

        # Extract Bearer token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "נדרש אימות. אנא ספקו טוקן גישה."},
            )

        token = auth_header[7:].strip()
        role = self._token_map.get(token)

        if role is None:
            return JSONResponse(
                status_code=401,
                content={"detail": "טוקן גישה לא תקין."},
            )

        # Attach user info to request state
        request.state.user_role = role
        request.state.authenticated = True

        # Check RBAC permission for the endpoint
        operation = self._resolve_operation(request.method, request.url.path)
        if operation and not check_permission(role, operation):
            return JSONResponse(
                status_code=403,
                content={"detail": "אין לך הרשאה לבצע פעולה זו."},
            )

        return await call_next(request)

    @staticmethod
    def _resolve_operation(method: str, path: str) -> str | None:
        """Resolve an HTTP method + path to an RBAC operation.

        Uses pattern matching to handle path parameters like {job_id}.

        Args:
            method: HTTP method (GET, POST, etc.).
            path: Request URL path.

        Returns:
            Operation string if found, None otherwise.
        """
        # Normalize path: strip trailing slash
        path = path.rstrip("/")

        # Try exact match first
        key = f"{method} {path}"
        if key in ENDPOINT_OPERATIONS:
            return ENDPOINT_OPERATIONS[key]

        # Try pattern matching for parameterized paths
        for pattern, op in ENDPOINT_OPERATIONS.items():
            pattern_method, pattern_path = pattern.split(" ", 1)
            if method != pattern_method:
                continue

            # Convert pattern to regex-like matching
            pattern_parts = pattern_path.strip("/").split("/")
            path_parts = path.strip("/").split("/")

            if len(pattern_parts) != len(path_parts):
                continue

            match = True
            for pp, rp in zip(pattern_parts, path_parts, strict=True):
                if pp.startswith("{") and pp.endswith("}"):
                    continue  # Wildcard segment
                if pp != rp:
                    match = False
                    break

            if match:
                return op

        return None


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests with timing information.

    Logs method, path, status code, and response time for every request.
    Sensitive headers (Authorization) are redacted in logs.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Log request and measure response time.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware/handler in chain.

        Returns:
            Response from downstream handler.
        """
        start_time = time.monotonic()

        # Log request
        logger.info(
            "Request: %s %s (client: %s)",
            request.method,
            request.url.path,
            request.client.host if request.client else "unknown",
        )

        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.monotonic() - start_time) * 1000
            logger.exception(
                "Request failed: %s %s (%.1fms)",
                request.method,
                request.url.path,
                elapsed_ms,
            )
            raise

        elapsed_ms = (time.monotonic() - start_time) * 1000

        logger.info(
            "Response: %s %s -> %d (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )

        # Add timing header
        response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.1f}"

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiter per client IP.

    Uses a sliding window counter. In production, replace with
    Redis-backed rate limiting for multi-instance deployments.

    Configuration via environment variables:
    - RATE_LIMIT_REQUESTS: max requests per window (default: 100)
    - RATE_LIMIT_WINDOW_SECONDS: window size in seconds (default: 60)
    """

    def __init__(self, app: Any) -> None:
        """Initialize rate limiter with configuration from environment."""
        super().__init__(app)
        self._max_requests = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
        self._window_seconds = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
        # IP -> list of request timestamps
        self._request_log: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Check rate limit before processing request.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware/handler in chain.

        Returns:
            Response from downstream handler or 429 error.
        """
        # Skip rate limiting for health checks
        if request.url.path == "/health":
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        cutoff = now - self._window_seconds

        # Prune old entries
        timestamps = self._request_log[client_ip]
        self._request_log[client_ip] = [t for t in timestamps if t > cutoff]

        # Check limit
        if len(self._request_log[client_ip]) >= self._max_requests:
            logger.warning("Rate limit exceeded for %s", client_ip)
            return JSONResponse(
                status_code=429,
                content={"detail": "חריגה ממגבלת בקשות. אנא נסו שוב מאוחר יותר."},
                headers={"Retry-After": str(self._window_seconds)},
            )

        # Record this request
        self._request_log[client_ip].append(now)

        return await call_next(request)
