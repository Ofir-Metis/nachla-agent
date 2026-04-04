"""Basic authentication for the Chainlit prototype.

Production will use proper OAuth/RBAC (Phase 5).
For the prototype, uses simple token-based auth loaded from environment.
"""

from __future__ import annotations

import functools
import os
from typing import Any

import chainlit as cl


# Valid tokens loaded from environment variable AUTH_TOKENS (comma-separated)
# Format: "token1:user1:role1,token2:user2:role2"
def _load_tokens() -> dict[str, dict[str, str]]:
    """Load valid tokens from AUTH_TOKENS environment variable.

    Expected format: "token1:username1:role1,token2:username2:role2"
    If AUTH_TOKENS is not set, authentication is disabled (prototype mode).

    Returns:
        Dict mapping token to user info dict with 'username' and 'role' keys.
    """
    tokens_str = os.environ.get("AUTH_TOKENS", "")
    if not tokens_str:
        return {}

    tokens: dict[str, dict[str, str]] = {}
    for entry in tokens_str.split(","):
        parts = entry.strip().split(":")
        if len(parts) >= 2:
            token = parts[0].strip()
            username = parts[1].strip()
            role = parts[2].strip() if len(parts) >= 3 else "user"
            tokens[token] = {"username": username, "role": role}

    return tokens


VALID_TOKENS: dict[str, dict[str, str]] = _load_tokens()


async def authenticate(token: str) -> dict[str, str] | None:
    """Validate token and return user info, or None if invalid.

    Args:
        token: Authentication token string.

    Returns:
        Dict with 'username' and 'role' if valid, None if invalid.
        If no tokens are configured (prototype mode), returns a default user.
    """
    # Prototype mode: no tokens configured, allow all access
    if not VALID_TOKENS:
        return {"username": "prototype_user", "role": "admin"}

    return VALID_TOKENS.get(token)


def require_auth(func: Any) -> Any:
    """Decorator to require authentication on Chainlit handlers.

    Checks the session for an authenticated user. If not found,
    sends a Hebrew error message and returns without executing the handler.

    Args:
        func: The async handler function to wrap.

    Returns:
        Wrapped function that checks auth before executing.
    """

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        user = cl.user_session.get("authenticated_user")
        if user is None:
            await cl.Message(content='<div dir="rtl">אין הרשאה. אנא התחברו למערכת.</div>').send()
            return None
        return await func(*args, **kwargs)

    return wrapper


@cl.password_auth_callback
async def auth_callback(username: str, password: str) -> cl.User | None:
    """Chainlit password authentication callback.

    Uses the token as the password field for simplicity in the prototype.

    Args:
        username: Username entered by the user.
        password: Password/token entered by the user.

    Returns:
        cl.User if authenticated, None if not.
    """
    user_info = await authenticate(password)
    if user_info is not None:
        return cl.User(
            identifier=user_info.get("username", username),
            metadata={"role": user_info.get("role", "user")},
        )

    # Prototype mode: if no tokens configured, allow login with any credentials
    if not VALID_TOKENS:
        return cl.User(
            identifier=username,
            metadata={"role": "admin"},
        )

    return None
